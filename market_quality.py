"""Evidence-gated market-quality assessment for the declared product slice.

This module does not infer market readiness from a green test suite. It combines
weighted criteria with non-negotiable critical gates, checks that referenced
evidence exists, and expires market-source research after a bounded interval.
"""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Dict, Iterable, Optional
from urllib.parse import urlparse


STATUS_FACTORS = {
    "pass": 1.0,
    "partial": 0.5,
    "fail": 0.0,
    "unverified": 0.0,
}

APPROVED_MARKET_HOSTS = {
    "docs.gorgias.com",
    "www.intercom.com",
    "support.zendesk.com",
    "www.w3.org",
}

INDEPENDENT_OBSERVER_RELATIONSHIPS = {
    "buyer",
    "representative_operator",
    "independent_reviewer",
    "security_reviewer",
    "operations_owner",
}

PRODUCTION_MARKET_POLICY_ID = "support-readiness-market-v2"
PRODUCTION_MARKET_POLICY_SHA256 = (
    "3b94c34c4644eacccd9ecceaff8e0da5b7980af44f6ca2a77abed85ce7daa85c"
)

PUBLIC_EVIDENCE_SUFFIXES = {".csv", ".json", ".md", ".txt"}
PRODUCTION_TECHNICAL_CHECK_IDS = {
    "python_locked_install",
    "node_locked_install",
    "offline_and_gate_unit_tests",
    "fixture_reproduction",
    "api_backend_tests",
    "async_benchmark_snapshot",
    "sql_query_plan_snapshot",
    "frontend_types_components_and_build",
    "frontend_production_dependency_audit",
    "browser_api_database_journey",
    "whitespace_gate",
}
PRIVACY_RISK_PATTERNS = (
    re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),
    re.compile(r"(?<!\d)(?:\+?\d[\s().-]*){9,15}(?!\d)"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    re.compile(r"\b(?:gh[pousr]_|github_pat_)[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
    re.compile(r"\bsk_live_[0-9A-Za-z]{16,}\b"),
)


def _market_policy_projection(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Return the complete benchmark contract except generated observations."""

    return {
        "schema_version": spec.get("schema_version"),
        "policy_id": spec.get("policy_id"),
        "benchmark_scope": spec.get("benchmark_scope"),
        "market_checked_at": spec.get("market_checked_at"),
        "market_review_receipt": spec.get("market_review_receipt"),
        "threshold": spec.get("threshold"),
        "max_source_age_days": spec.get("max_source_age_days"),
        "system_under_test_paths": spec.get("system_under_test_paths"),
        "criteria": spec.get("criteria"),
    }


def _market_policy_digest(spec: Dict[str, Any]) -> str:
    rendered = json.dumps(
        _market_policy_projection(spec),
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(rendered).hexdigest()


def _canonical_json_digest(value: Any) -> str:
    rendered = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(rendered).hexdigest()


def _validate_market_review_receipt(spec: Dict[str, Any]) -> None:
    receipt = spec.get("market_review_receipt", {})
    urls = sorted(
        {
            source
            for criterion in spec.get("criteria", [])
            for source in criterion.get("sources", [])
        }
    )
    claims = [
        {
            "id": criterion.get("id"),
            "market_expectation": criterion.get("market_expectation"),
            "sources": criterion.get("sources", []),
        }
        for criterion in spec.get("criteria", [])
    ]
    valid = (
        isinstance(receipt, dict)
        and receipt.get("schema_version") == "1.0"
        and receipt.get("reviewed_at") == spec.get("market_checked_at")
        and receipt.get("reviewer_relationship") == "author_research_review"
        and receipt.get("source_count") == len(urls)
        and receipt.get("source_urls_sha256") == _canonical_json_digest(urls)
        and receipt.get("criterion_claims_sha256")
        == _canonical_json_digest(claims)
        and isinstance(receipt.get("retrieval_summary"), str)
        and bool(receipt["retrieval_summary"].strip())
    )
    if not valid:
        raise ValueError("market review receipt does not match benchmark sources")


def validate_market_policy(
    spec: Dict[str, Any], *, required: bool = False
) -> Optional[str]:
    """Reject a weakened production policy before any score is calculated."""

    policy_id = spec.get("policy_id")
    if policy_id is None:
        if required:
            raise ValueError("market policy contract mismatch: locked policy required")
        return None
    if policy_id != PRODUCTION_MARKET_POLICY_ID:
        raise ValueError("market policy contract mismatch: unsupported policy id")

    _validate_market_review_receipt(spec)
    digest = _market_policy_digest(spec)
    if digest != PRODUCTION_MARKET_POLICY_SHA256:
        raise ValueError("market policy contract mismatch: scoring controls changed")
    return digest


def _official_sources(sources: Iterable[str]) -> bool:
    sources = list(sources)
    return bool(sources) and all(
        urlparse(source).scheme == "https"
        and urlparse(source).hostname in APPROVED_MARKET_HOSTS
        for source in sources
    )


def _system_under_test_digest(root: Path, declared_paths: Iterable[str]) -> str:
    """Bind observation records to the exact reviewable product tree."""

    root = root.resolve()
    files: set[Path] = set()
    for declared in declared_paths:
        relative = Path(declared)
        candidate = (root / relative).resolve()
        try:
            candidate.relative_to(root)
        except ValueError as error:
            raise ValueError("system-under-test path outside repository") from error
        if relative.is_absolute() or not candidate.exists():
            raise ValueError(f"system-under-test path missing or invalid: {declared}")
        if candidate.is_dir():
            for child in candidate.rglob("*"):
                if child.is_file() and not (
                    any(
                        part in {"__pycache__", ".next", "node_modules", "test-results"}
                        for part in child.parts
                    )
                    or child.suffix in {".pyc", ".pyo"}
                    or child.name == "tsconfig.tsbuildinfo"
                ):
                    resolved = child.resolve()
                    try:
                        resolved.relative_to(root)
                    except ValueError as error:
                        raise ValueError(
                            "system-under-test file outside repository"
                        ) from error
                    files.add(resolved)
        elif candidate.is_file():
            files.add(candidate)

    if not files:
        raise ValueError("at least one system-under-test file is required")

    digest = hashlib.sha256()
    for path in sorted(files, key=lambda item: item.relative_to(root).as_posix()):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def _contains_privacy_risk(text: str) -> bool:
    return any(pattern.search(text) for pattern in PRIVACY_RISK_PATTERNS)


def _verification_evaluation_date(output: Path) -> date:
    """Use the committed snapshot date for deterministic byte verification."""

    snapshot = json.loads(output.read_text())
    try:
        return date.fromisoformat(snapshot["as_of"])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("market snapshot has no valid as_of date") from error


def validate_live_freshness(
    spec: Dict[str, Any], *, root: Path, today: date
) -> None:
    """Fail verification when research or an existing observation has expired.

    Snapshot reproduction may pin ``as_of`` for byte stability, so freshness
    must be checked independently against the actual verification date.
    Missing observation records remain ordinary unmet controls; malformed,
    future-dated, or stale records fail the live input check.
    """

    try:
        checked_at = date.fromisoformat(spec["market_checked_at"])
        max_source_age_days = int(spec["max_source_age_days"])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("live market-source freshness check failed") from error
    source_age_days = (today - checked_at).days
    if (
        max_source_age_days < 1
        or source_age_days < 0
        or source_age_days > max_source_age_days
    ):
        raise ValueError("live market-source freshness check failed")

    resolved_root = root.resolve()
    for criterion in spec.get("criteria", []):
        for control in criterion.get("controls", []):
            if control.get("kind") != "external_observation":
                continue
            control_id = control.get("id", "unknown")
            raw_max_age_days = control.get("max_observation_age_days")
            if type(raw_max_age_days) is not int or raw_max_age_days < 1:
                raise ValueError(
                    f"external control {control_id!r} requires a positive "
                    "max_observation_age_days"
                )
            max_age_days = raw_max_age_days

            relative_record = Path(control.get("record", ""))
            record_path = (root / relative_record).resolve()
            try:
                record_path.relative_to(resolved_root)
                inside_root = not relative_record.is_absolute()
            except ValueError:
                inside_root = False
            if not inside_root or not record_path.is_file():
                continue

            try:
                record = json.loads(record_path.read_text())
                observed_at = date.fromisoformat(record["observed_at"])
            except (
                OSError,
                json.JSONDecodeError,
                KeyError,
                TypeError,
                ValueError,
            ) as error:
                raise ValueError(
                    f"live external-observation freshness check failed: {control_id}"
                ) from error
            age_days = (today - observed_at).days
            if age_days < 0 or age_days > max_age_days:
                raise ValueError(
                    f"live external-observation freshness check failed: {control_id}"
                )


def _load_observed_checks(
    path: Path,
    *,
    require_full_harness: bool = False,
    expected_policy_sha256: Optional[str] = None,
    expected_system_under_test_sha256: Optional[str] = None,
) -> list[Dict[str, Any]]:
    snapshot = json.loads(path.read_text())
    if not isinstance(snapshot, dict):
        raise ValueError("quality harness snapshot must be an object")
    if snapshot.get("technical_gate") != "PASS":
        return []
    checks = snapshot.get("checks", [])
    if not isinstance(checks, list):
        raise ValueError("quality harness snapshot checks must be a list")
    if require_full_harness:
        check_ids = [
            item.get("id") for item in checks if isinstance(item, dict)
        ]
        full_harness_valid = (
            len(check_ids) == len(checks) == len(PRODUCTION_TECHNICAL_CHECK_IDS)
            and all(isinstance(identifier, str) for identifier in check_ids)
            and len(set(check_ids)) == len(check_ids)
            and set(check_ids) == PRODUCTION_TECHNICAL_CHECK_IDS
            and all(item.get("status") == "PASS" for item in checks)
            and snapshot.get("technical_checks_passed")
            == len(PRODUCTION_TECHNICAL_CHECK_IDS)
            and snapshot.get("technical_checks_total")
            == len(PRODUCTION_TECHNICAL_CHECK_IDS)
        )
        if expected_policy_sha256 is not None:
            full_harness_valid = full_harness_valid and (
                snapshot.get("market_policy_sha256") == expected_policy_sha256
            )
        if expected_system_under_test_sha256 is not None:
            full_harness_valid = full_harness_valid and (
                snapshot.get("system_under_test_sha256")
                == expected_system_under_test_sha256
            )
        if not full_harness_valid:
            raise ValueError("full technical harness snapshot validation failed")
    return checks


def _evaluate_controls(
    controls: Iterable[Dict[str, Any]],
    *,
    criterion_id: str,
    observed_checks: Iterable[Dict[str, Any]],
    root: Path,
    today: date,
    system_under_test_sha256: str,
) -> list[Dict[str, Any]]:
    passed_check_ids = {
        item["id"] for item in observed_checks if item.get("status") == "PASS"
    }
    evaluated = []
    for control in controls:
        kind = control.get("kind")
        if kind == "technical_check":
            check_ids = control.get("check_ids", [])
            if not check_ids:
                raise ValueError(
                    f"technical control {control.get('id')!r} requires check_ids"
                )
            missing_check_ids = [
                check_id for check_id in check_ids if check_id not in passed_check_ids
            ]
            evaluated.append(
                {
                    **control,
                    "verified": not missing_check_ids,
                    "missing_check_ids": missing_check_ids,
                    "failures": (
                        ["required_technical_checks_not_observed"]
                        if missing_check_ids
                        else []
                    ),
                }
            )
            continue
        if kind == "external_observation":
            failures = []
            raw_max_observation_age_days = control.get(
                "max_observation_age_days"
            )
            if (
                type(raw_max_observation_age_days) is not int
                or raw_max_observation_age_days < 1
            ):
                raise ValueError(
                    f"external control {control.get('id')!r} requires a positive "
                    "max_observation_age_days"
                )
            max_observation_age_days = raw_max_observation_age_days
            raw_minimum_sample_size = control.get("minimum_sample_size")
            if (
                type(raw_minimum_sample_size) is not int
                or raw_minimum_sample_size < 1
            ):
                raise ValueError(
                    f"external control {control.get('id')!r} requires a positive "
                    "minimum_sample_size"
                )
            minimum_sample_size = raw_minimum_sample_size
            required_acceptance_ids = control.get(
                "required_acceptance_check_ids", []
            )
            if not required_acceptance_ids:
                raise ValueError(
                    f"external control {control.get('id')!r} requires "
                    "required_acceptance_check_ids"
                )
            record_relative_path = Path(control.get("record", ""))
            record_path = (root / record_relative_path).resolve()
            record: Dict[str, Any] = {}
            try:
                record_path.relative_to(root.resolve())
                record_inside_root = not record_relative_path.is_absolute()
            except ValueError:
                record_inside_root = False
            if not record_inside_root:
                failures.append("observation_record_outside_repository")
            elif not control.get("record") or not record_path.is_file():
                failures.append("observation_record_missing")
            else:
                try:
                    loaded_record = json.loads(record_path.read_text())
                    if not isinstance(loaded_record, dict):
                        failures.append("observation_record_invalid")
                    else:
                        record = loaded_record
                except (OSError, json.JSONDecodeError):
                    failures.append("observation_record_invalid")

            if record:
                allowed_record_fields = {
                    "schema_version",
                    "criterion_id",
                    "control_id",
                    "observed_at",
                    "observer_relationship",
                    "observer_role",
                    "observer_reference",
                    "consent_recorded",
                    "sample_size",
                    "sample_references",
                    "system_under_test_sha256",
                    "acceptance_checks",
                    "privacy_review",
                    "artifacts",
                }
                if set(record) - allowed_record_fields:
                    failures.append("observation_record_unknown_fields")
                if _contains_privacy_risk(
                    json.dumps(record, ensure_ascii=False, sort_keys=True)
                ):
                    failures.append("observation_record_privacy_risk")
                if record.get("schema_version") != "1.0":
                    failures.append("observation_schema_unsupported")
                if record.get("criterion_id") != criterion_id:
                    failures.append("criterion_id_mismatch")
                if record.get("control_id") != control.get("id"):
                    failures.append("control_id_mismatch")
                observer_relationship = record.get("observer_relationship")
                if (
                    not isinstance(observer_relationship, str)
                    or observer_relationship
                    not in INDEPENDENT_OBSERVER_RELATIONSHIPS
                ):
                    failures.append("observer_not_independent")
                observer_role = record.get("observer_role")
                observer_reference = record.get("observer_reference")
                if not (
                    isinstance(observer_role, str)
                    and observer_role.strip()
                    and isinstance(observer_reference, str)
                    and observer_reference.strip()
                ):
                    failures.append("observer_identity_incomplete")
                elif _contains_privacy_risk(observer_reference):
                    failures.append("observer_reference_privacy_risk")
                if record.get("consent_recorded") is not True:
                    failures.append("observation_consent_missing")
                if (
                    record.get("system_under_test_sha256")
                    != system_under_test_sha256
                ):
                    failures.append("system_under_test_digest_mismatch")
                try:
                    observed_at = date.fromisoformat(record["observed_at"])
                    observation_age_days = (today - observed_at).days
                    if observation_age_days < 0:
                        failures.append("observation_date_in_future")
                    elif observation_age_days > max_observation_age_days:
                        failures.append("observation_stale")
                except (KeyError, TypeError, ValueError):
                    failures.append("observation_date_invalid")
                sample_size: Optional[int] = None
                raw_sample_size = record.get("sample_size")
                if type(raw_sample_size) is int and raw_sample_size > 0:
                    sample_size = raw_sample_size
                    if sample_size < minimum_sample_size:
                        failures.append("sample_size_below_minimum")
                else:
                    failures.append("sample_size_invalid")

                sample_references = record.get("sample_references", [])
                valid_sample_references = (
                    isinstance(sample_references, list)
                    and sample_size is not None
                    and len(sample_references) == sample_size
                    and all(
                        isinstance(reference, str) and reference.strip()
                        for reference in sample_references
                    )
                    and len(set(sample_references)) == len(sample_references)
                )
                if not valid_sample_references:
                    failures.append("sample_references_invalid")

                acceptance_checks = record.get("acceptance_checks", [])
                acceptance_ids = []
                if isinstance(acceptance_checks, list):
                    acceptance_ids = [
                        check.get("id")
                        for check in acceptance_checks
                        if isinstance(check, dict)
                    ]
                if (
                    not acceptance_checks
                    or len(acceptance_ids) != len(acceptance_checks)
                    or not all(
                        isinstance(identifier, str) and identifier.strip()
                        for identifier in acceptance_ids
                    )
                    or len(set(acceptance_ids)) != len(acceptance_ids)
                    or any(
                        check.get("result") != "pass"
                        for check in acceptance_checks
                        if isinstance(check, dict)
                    )
                    or any(
                        set(check) - {"id", "result"}
                        for check in acceptance_checks
                        if isinstance(check, dict)
                    )
                ):
                    failures.append("acceptance_checks_not_passed")
                if not set(required_acceptance_ids).issubset(acceptance_ids):
                    failures.append("required_acceptance_checks_missing")

                privacy_review = record.get("privacy_review", {})
                if not (
                    isinstance(privacy_review, dict)
                    and not set(privacy_review)
                    - {
                        "status",
                        "reviewer_relationship",
                        "reviewer_reference",
                        "sanitized_for_public_repository",
                        "raw_evidence_stored_outside_repository",
                    }
                    and privacy_review.get("status") == "pass"
                    and isinstance(
                        privacy_review.get("reviewer_relationship"), str
                    )
                    and privacy_review.get("reviewer_relationship") in {
                        "independent_reviewer",
                        "security_reviewer",
                        "operations_owner",
                    }
                    and isinstance(
                        privacy_review.get("reviewer_reference"), str
                    )
                    and privacy_review["reviewer_reference"].strip()
                    and privacy_review.get("sanitized_for_public_repository") is True
                    and privacy_review.get("raw_evidence_stored_outside_repository")
                    is True
                ):
                    failures.append("privacy_review_missing_or_failed")

                artifacts = record.get("artifacts", [])
                if not isinstance(artifacts, list) or not artifacts:
                    failures.append("observation_artifacts_missing")
                    artifacts = []
                covered_sample_references: set[str] = set()
                for artifact in artifacts:
                    if not isinstance(artifact, dict):
                        failures.append("observation_artifact_invalid")
                        continue
                    if set(artifact) - {"path", "sha256", "sample_references"}:
                        failures.append("observation_artifact_invalid")
                        continue
                    relative_path = Path(artifact.get("path", ""))
                    artifact_path = (root / relative_path).resolve()
                    try:
                        artifact_path.relative_to(root.resolve())
                    except ValueError:
                        failures.append("observation_artifact_outside_repository")
                        continue
                    if relative_path.is_absolute():
                        failures.append("observation_artifact_outside_repository")
                        continue
                    if not artifact_path.is_file():
                        failures.append("observation_artifact_missing")
                        continue
                    if artifact_path.suffix.lower() not in PUBLIC_EVIDENCE_SUFFIXES:
                        failures.append("observation_artifact_type_not_allowed")
                        continue
                    artifact_bytes = artifact_path.read_bytes()
                    if len(artifact_bytes) > 1_000_000:
                        failures.append("observation_artifact_too_large")
                        continue
                    try:
                        artifact_text = artifact_bytes.decode("utf-8")
                    except UnicodeDecodeError:
                        failures.append("observation_artifact_not_utf8")
                        continue
                    if _contains_privacy_risk(artifact_text):
                        failures.append("observation_artifact_privacy_risk")
                    observed_digest = hashlib.sha256(artifact_bytes).hexdigest()
                    if observed_digest != artifact.get("sha256"):
                        failures.append("observation_artifact_digest_mismatch")
                    artifact_sample_references = artifact.get(
                        "sample_references", []
                    )
                    if not (
                        isinstance(artifact_sample_references, list)
                        and all(
                            isinstance(reference, str) and reference.strip()
                            for reference in artifact_sample_references
                        )
                    ):
                        failures.append("artifact_sample_references_invalid")
                    else:
                        covered_sample_references.update(artifact_sample_references)

                if valid_sample_references and (
                    covered_sample_references != set(sample_references)
                ):
                    failures.append("sample_artifact_binding_incomplete")

            evaluated.append(
                {
                    **control,
                    "verified": not failures,
                    "failures": sorted(set(failures)),
                }
            )
            continue
        else:
            raise ValueError(
                f"unsupported market control kind {kind!r} for {control.get('id')!r}"
            )
    return evaluated


def evaluate_market_quality(
    spec: Dict[str, Any],
    *,
    root: Path,
    today: Optional[date] = None,
    observed_checks: Optional[Iterable[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Evaluate one evidence registry without allowing points to hide blockers."""

    policy_sha256 = validate_market_policy(spec)
    today = today or date.today()
    system_under_test_sha256 = _system_under_test_digest(
        root, spec.get("system_under_test_paths", [])
    )
    criteria = spec.get("criteria", [])
    if not criteria:
        raise ValueError("at least one market criterion is required")

    total_weight = sum(float(item["weight"]) for item in criteria)
    if abs(total_weight - 100.0) > 0.0001:
        raise ValueError(f"criterion weights must total 100, observed {total_weight:g}")

    identifiers = [item["id"] for item in criteria]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("criterion ids must be unique")

    checked_at = date.fromisoformat(spec["market_checked_at"])
    source_age_days = (today - checked_at).days
    if source_age_days < 0:
        raise ValueError("market_checked_at cannot be in the future")
    max_source_age_days = int(spec.get("max_source_age_days", 90))
    market_sources_stale = source_age_days > max_source_age_days

    observed_checks = list(observed_checks or [])
    evaluated = []
    score = 0.0
    for item in criteria:
        declared_status = item["status"]
        if declared_status not in STATUS_FACTORS:
            raise ValueError(
                f"unsupported status {declared_status!r} for criterion {item['id']}"
            )

        missing_evidence = [
            relative_path
            for relative_path in item.get("evidence", [])
            if not (root / relative_path).exists()
        ]
        sources = item.get("sources", [])
        sources_official = _official_sources(sources)
        controls = item.get("controls", [])
        evaluated_controls = _evaluate_controls(
            controls,
            criterion_id=item["id"],
            observed_checks=observed_checks,
            root=root,
            today=today,
            system_under_test_sha256=system_under_test_sha256,
        ) if controls else []
        verified_control_count = sum(
            control["verified"] for control in evaluated_controls
        )
        effective_status = "unverified"
        if (
            missing_evidence
            or market_sources_stale
            or not sources_official
            or not controls
        ):
            effective_status = "unverified"
        elif verified_control_count == len(evaluated_controls):
            effective_status = "pass"
        elif verified_control_count:
            effective_status = "partial"
        else:
            effective_status = "fail"

        control_factor = (
            verified_control_count / len(evaluated_controls)
            if effective_status != "unverified" and evaluated_controls
            else 0.0
        )
        points = float(item["weight"]) * control_factor
        score += points
        evaluated.append(
            {
                "id": item["id"],
                "label": item["label"],
                "weight": item["weight"],
                "critical": bool(item["critical"]),
                "declared_status": declared_status,
                "effective_status": effective_status,
                "scored_points": round(points, 2),
                "market_expectation": item["market_expectation"],
                "evidence": item.get("evidence", []),
                "missing_evidence": missing_evidence,
                "sources": sources,
                "sources_official": sources_official,
                "controls": evaluated_controls,
                "verified_controls": verified_control_count,
                "total_controls": len(evaluated_controls),
                "gap": item["gap"],
            }
        )

    score = round(score, 2)
    critical_failures = [
        item["id"]
        for item in evaluated
        if item["critical"] and item["effective_status"] != "pass"
    ]
    threshold = float(spec["threshold"])
    evidence_state = (
        "STRUCTURALLY_COMPLETE_PENDING_INDEPENDENT_PROVENANCE_REVIEW"
        if score >= threshold and not critical_failures
        else "INCOMPLETE"
    )
    verdict = "NOT_MARKET_READY"

    return {
        "schema_version": spec["schema_version"],
        "policy_id": spec.get("policy_id"),
        "policy_sha256": policy_sha256,
        "system_under_test_sha256": system_under_test_sha256,
        "as_of": today.isoformat(),
        "benchmark_scope": spec["benchmark_scope"],
        "market_checked_at": checked_at.isoformat(),
        "market_source_age_days": source_age_days,
        "max_source_age_days": max_source_age_days,
        "market_sources_stale": market_sources_stale,
        "threshold": threshold,
        "score": score,
        "critical_failures": critical_failures,
        "evidence_state": evidence_state,
        "verdict": verdict,
        "claim_limit": (
            "Repository-local automation never emits MARKET_READY. Even structurally "
            "complete evidence remains pending independent human provenance review "
            "and an externally governed release decision."
        ),
        "criteria": evaluated,
    }


def _load(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text())


def main() -> int:
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--spec",
        type=Path,
        default=root / "evaluation" / "market_quality_criteria.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=root / "evaluation" / "market_quality_results.json",
    )
    parser.add_argument(
        "--observed-checks-file",
        type=Path,
        help=(
            "Use checks from a completed technical-harness snapshot for report "
            "reproduction. The real release gate remains quality_harness.py."
        ),
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Compare the generated result with the committed output without writing.",
    )
    parser.add_argument(
        "--allow-not-ready",
        action="store_true",
        help="Return zero for an honestly reproduced NOT_MARKET_READY baseline.",
    )
    args = parser.parse_args()

    try:
        spec = _load(args.spec)
        policy_sha256 = validate_market_policy(spec, required=True)
        system_under_test_sha256 = _system_under_test_digest(
            root, spec.get("system_under_test_paths", [])
        )
        validate_live_freshness(spec, root=root, today=date.today())
        if not args.observed_checks_file:
            raise ValueError("full technical harness snapshot is required")
        observed_checks = _load_observed_checks(
            args.observed_checks_file,
            require_full_harness=True,
            expected_policy_sha256=policy_sha256,
            expected_system_under_test_sha256=system_under_test_sha256,
        )
        evaluation_today = (
            _verification_evaluation_date(args.output)
            if args.verify
            else date.today()
        )
        result = evaluate_market_quality(
            spec,
            root=root,
            today=evaluation_today,
            observed_checks=observed_checks,
        )
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(f"market_quality_input=FAIL error={error}")
        return 2

    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.verify:
        if not args.output.exists() or args.output.read_text() != rendered:
            print("market_quality_snapshot_verification=FAIL")
            return 2
        print("market_quality_snapshot_verification=PASS")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered)

    print(
        f"market_quality_verdict={result['verdict']} "
        f"readiness_rubric_score={result['score']:g}/100 "
        f"threshold={result['threshold']:g} "
        f"critical_failures={len(result['critical_failures'])}"
    )
    if result["verdict"] != "MARKET_READY" and not args.allow_not_ready:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
