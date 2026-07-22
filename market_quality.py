"""Evidence-gated market-quality assessment for the declared product slice.

This module does not infer market readiness from a green test suite. It combines
weighted criteria with non-negotiable critical gates, checks that referenced
evidence exists, and expires market-source research after a bounded interval.
"""

from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
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


def _official_sources(sources: Iterable[str]) -> bool:
    sources = list(sources)
    return bool(sources) and all(
        urlparse(source).scheme == "https"
        and urlparse(source).hostname in APPROVED_MARKET_HOSTS
        for source in sources
    )


def evaluate_market_quality(
    spec: Dict[str, Any],
    *,
    root: Path,
    today: Optional[date] = None,
) -> Dict[str, Any]:
    """Evaluate one evidence registry without allowing points to hide blockers."""

    today = today or date.today()
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
        effective_status = declared_status
        if missing_evidence or market_sources_stale or not sources_official:
            effective_status = "unverified"

        points = float(item["weight"]) * STATUS_FACTORS[effective_status]
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
    verdict = (
        "MARKET_READY"
        if score >= threshold and not critical_failures
        else "NOT_MARKET_READY"
    )

    return {
        "schema_version": spec["schema_version"],
        "as_of": today.isoformat(),
        "benchmark_scope": spec["benchmark_scope"],
        "market_checked_at": checked_at.isoformat(),
        "market_source_age_days": source_age_days,
        "max_source_age_days": max_source_age_days,
        "market_sources_stale": market_sources_stale,
        "threshold": threshold,
        "score": score,
        "critical_failures": critical_failures,
        "verdict": verdict,
        "claim_limit": (
            "A MARKET_READY verdict applies only to the declared benchmark scope; "
            "it never proves customer demand, production safety, or business impact "
            "unless those are explicit passing criteria."
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

    result = evaluate_market_quality(_load(args.spec), root=root)
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
        f"score={result['score']:g}/{result['threshold']:g} "
        f"critical_failures={len(result['critical_failures'])}"
    )
    if result["verdict"] != "MARKET_READY" and not args.allow_not_ready:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
