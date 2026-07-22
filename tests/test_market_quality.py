import hashlib
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from market_quality import (
    _load_observed_checks,
    _system_under_test_digest,
    _verification_evaluation_date,
    evaluate_market_quality,
    validate_live_freshness,
    validate_market_policy,
)


class MarketQualityGateTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        (self.root / "evidence.txt").write_text("observed evidence\n")

    def criterion(self, identifier, weight, status="pass", critical=True):
        return {
            "id": identifier,
            "label": identifier.replace("_", " "),
            "weight": weight,
            "critical": critical,
            "status": status,
            "market_expectation": "Observed category expectation.",
            "evidence": ["evidence.txt"],
            "sources": ["https://docs.gorgias.com/en-US/example-1"],
            "gap": "None" if status == "pass" else "Still missing.",
        }

    def spec(self, criteria, threshold=85):
        return {
            "schema_version": "1.0",
            "benchmark_scope": "Narrow declared workflow.",
            "market_checked_at": "2026-07-22",
            "max_source_age_days": 90,
            "threshold": threshold,
            "system_under_test_paths": ["evidence.txt"],
            "criteria": criteria,
        }

    def write_valid_external_record(self, **overrides):
        evidence_sha256 = hashlib.sha256(
            (self.root / "evidence.txt").read_bytes()
        ).hexdigest()
        sample_references = ["case-001", "case-002", "case-003"]
        record = {
            "schema_version": "1.0",
            "criterion_id": "operator_pilot",
            "control_id": "representative_operator_observation",
            "observed_at": "2026-07-22",
            "observer_relationship": "representative_operator",
            "observer_role": "support_operator",
            "observer_reference": "pilot-operator-01",
            "consent_recorded": True,
            "sample_size": 3,
            "sample_references": sample_references,
            "system_under_test_sha256": _system_under_test_digest(
                self.root, ["evidence.txt"]
            ),
            "acceptance_checks": [{"id": "task_completed", "result": "pass"}],
            "privacy_review": {
                "status": "pass",
                "reviewer_relationship": "independent_reviewer",
                "reviewer_reference": "privacy-review-01",
                "sanitized_for_public_repository": True,
                "raw_evidence_stored_outside_repository": True,
            },
            "artifacts": [
                {
                    "path": "evidence.txt",
                    "sha256": evidence_sha256,
                    "sample_references": sample_references,
                }
            ],
        }
        record.update(overrides)
        (self.root / "pilot.json").write_text(json.dumps(record))

    def external_criterion(self):
        criterion = self.criterion("operator_pilot", 100)
        criterion["controls"] = [
            {
                "id": "representative_operator_observation",
                "kind": "external_observation",
                "record": "pilot.json",
                "minimum_sample_size": 3,
                "max_observation_age_days": 90,
                "required_acceptance_check_ids": ["task_completed"],
            }
        ]
        return criterion

    def test_critical_failure_blocks_a_high_numeric_score(self):
        strong = self.criterion("strong_noncritical", 90, critical=False)
        strong["controls"] = [
            {"id": "strong_check", "kind": "technical_check", "check_ids": ["strong"]}
        ]
        missing_auth = self.criterion("missing_auth", 10, status="pass", critical=True)
        missing_auth["controls"] = [
            {
                "id": "auth_review",
                "kind": "external_observation",
                "record": "missing-auth-review.json",
                "minimum_sample_size": 1,
                "max_observation_age_days": 90,
                "required_acceptance_check_ids": ["access_denied"],
            }
        ]
        result = evaluate_market_quality(
            self.spec([strong, missing_auth]),
            root=self.root,
            today=date(2026, 7, 22),
            observed_checks=[{"id": "strong", "status": "PASS"}],
        )

        self.assertEqual(result["score"], 90)
        self.assertEqual(result["verdict"], "NOT_MARKET_READY")
        self.assertEqual(result["critical_failures"], ["missing_auth"])

    def test_missing_evidence_downgrades_an_authored_pass(self):
        criterion = self.criterion("operator_flow", 100)
        criterion["evidence"] = ["missing-file.txt"]

        result = evaluate_market_quality(
            self.spec([criterion]), root=self.root, today=date(2026, 7, 22)
        )

        self.assertEqual(result["score"], 0)
        self.assertEqual(result["criteria"][0]["effective_status"], "unverified")
        self.assertIn("missing-file.txt", result["criteria"][0]["missing_evidence"])

    def test_authored_pass_without_verified_controls_is_unverified(self):
        result = evaluate_market_quality(
            self.spec([self.criterion("operator_flow", 100)]),
            root=self.root,
            today=date(2026, 7, 22),
        )

        self.assertEqual(result["score"], 0)
        self.assertEqual(result["criteria"][0]["effective_status"], "unverified")
        self.assertEqual(result["verdict"], "NOT_MARKET_READY")

    def test_technical_control_status_is_derived_from_current_check_results(self):
        criterion = self.criterion("operator_flow", 100, status="fail")
        criterion["controls"] = [
            {
                "id": "browser_journey",
                "kind": "technical_check",
                "check_ids": ["browser_api_database_journey"],
            }
        ]

        result = evaluate_market_quality(
            self.spec([criterion]),
            root=self.root,
            today=date(2026, 7, 22),
            observed_checks=[
                {"id": "browser_api_database_journey", "status": "PASS"}
            ],
        )

        self.assertEqual(result["score"], 100)
        self.assertEqual(result["criteria"][0]["effective_status"], "pass")
        self.assertEqual(result["verdict"], "NOT_MARKET_READY")
        self.assertEqual(
            result["evidence_state"],
            "STRUCTURALLY_COMPLETE_PENDING_INDEPENDENT_PROVENANCE_REVIEW",
        )

    def test_self_attested_external_observation_cannot_pass(self):
        self.write_valid_external_record(
            observer_relationship="author", observer_role="developer"
        )

        result = evaluate_market_quality(
            self.spec([self.external_criterion()]),
            root=self.root,
            today=date(2026, 7, 22),
        )

        control = result["criteria"][0]["controls"][0]
        self.assertFalse(control["verified"])
        self.assertIn("observer_not_independent", control["failures"])
        self.assertEqual(result["verdict"], "NOT_MARKET_READY")

    def test_structurally_valid_external_observation_still_needs_provenance_review(self):
        self.write_valid_external_record()
        criterion = self.external_criterion()
        criterion["status"] = "fail"

        result = evaluate_market_quality(
            self.spec([criterion]),
            root=self.root,
            today=date(2026, 7, 22),
        )

        self.assertTrue(result["criteria"][0]["controls"][0]["verified"])
        self.assertEqual(result["criteria"][0]["effective_status"], "pass")
        self.assertEqual(result["verdict"], "NOT_MARKET_READY")
        self.assertEqual(
            result["evidence_state"],
            "STRUCTURALLY_COMPLETE_PENDING_INDEPENDENT_PROVENANCE_REVIEW",
        )

    def test_tampered_external_observation_artifact_is_rejected(self):
        self.write_valid_external_record()
        (self.root / "evidence.txt").write_text("tampered after observation\n")

        result = evaluate_market_quality(
            self.spec([self.external_criterion()]),
            root=self.root,
            today=date(2026, 7, 22),
        )

        control = result["criteria"][0]["controls"][0]
        self.assertFalse(control["verified"])
        self.assertIn("observation_artifact_digest_mismatch", control["failures"])

    def test_stale_external_observation_is_rejected(self):
        self.write_valid_external_record(observed_at="2026-01-01")

        with self.assertRaisesRegex(
            ValueError, "live external-observation freshness check failed"
        ):
            validate_live_freshness(
                self.spec([self.external_criterion()]),
                root=self.root,
                today=date(2026, 7, 22),
            )

        result = evaluate_market_quality(
            self.spec([self.external_criterion()]),
            root=self.root,
            today=date(2026, 7, 22),
        )

        control = result["criteria"][0]["controls"][0]
        self.assertFalse(control["verified"])
        self.assertIn("observation_stale", control["failures"])

    def test_external_observation_below_minimum_sample_is_rejected(self):
        self.write_valid_external_record(sample_size=2)

        result = evaluate_market_quality(
            self.spec([self.external_criterion()]),
            root=self.root,
            today=date(2026, 7, 22),
        )

        control = result["criteria"][0]["controls"][0]
        self.assertFalse(control["verified"])
        self.assertIn("sample_size_below_minimum", control["failures"])

    def test_external_observation_with_invalid_sample_value_fails_closed(self):
        for invalid_value in ("many", 3.9, True):
            with self.subTest(invalid_value=invalid_value):
                self.write_valid_external_record(sample_size=invalid_value)
                result = evaluate_market_quality(
                    self.spec([self.external_criterion()]),
                    root=self.root,
                    today=date(2026, 7, 22),
                )

                control = result["criteria"][0]["controls"][0]
                self.assertFalse(control["verified"])
                self.assertIn("sample_size_invalid", control["failures"])

    def test_external_observation_with_failed_acceptance_is_rejected(self):
        self.write_valid_external_record(
            acceptance_checks=[{"id": "task_completed", "result": "fail"}]
        )

        result = evaluate_market_quality(
            self.spec([self.external_criterion()]),
            root=self.root,
            today=date(2026, 7, 22),
        )

        control = result["criteria"][0]["controls"][0]
        self.assertFalse(control["verified"])
        self.assertIn("acceptance_checks_not_passed", control["failures"])

    def test_external_observation_must_cover_required_acceptance_checks(self):
        self.write_valid_external_record(
            acceptance_checks=[{"id": "unrelated_check", "result": "pass"}]
        )

        result = evaluate_market_quality(
            self.spec([self.external_criterion()]),
            root=self.root,
            today=date(2026, 7, 22),
        )

        control = result["criteria"][0]["controls"][0]
        self.assertFalse(control["verified"])
        self.assertIn("required_acceptance_checks_missing", control["failures"])

    def test_external_observation_samples_must_be_bound_to_artifacts(self):
        self.write_valid_external_record(sample_references=["case-001"])

        result = evaluate_market_quality(
            self.spec([self.external_criterion()]),
            root=self.root,
            today=date(2026, 7, 22),
        )

        control = result["criteria"][0]["controls"][0]
        self.assertFalse(control["verified"])
        self.assertIn("sample_references_invalid", control["failures"])

    def test_external_observation_requires_privacy_review(self):
        invalid_reviews = [
            {},
            {
                "status": "pass",
                "reviewer_relationship": "independent_reviewer",
                "reviewer_reference": {"id": "privacy-review-01"},
                "sanitized_for_public_repository": True,
                "raw_evidence_stored_outside_repository": True,
            },
        ]
        for invalid_review in invalid_reviews:
            with self.subTest(invalid_review=invalid_review):
                self.write_valid_external_record(privacy_review=invalid_review)
                result = evaluate_market_quality(
                    self.spec([self.external_criterion()]),
                    root=self.root,
                    today=date(2026, 7, 22),
                )

                control = result["criteria"][0]["controls"][0]
                self.assertFalse(control["verified"])
                self.assertIn(
                    "privacy_review_missing_or_failed", control["failures"]
                )

    def test_external_observation_public_artifact_rejects_email(self):
        (self.root / "evidence.txt").write_text("customer@example.com\n")
        self.write_valid_external_record()

        result = evaluate_market_quality(
            self.spec([self.external_criterion()]),
            root=self.root,
            today=date(2026, 7, 22),
        )

        control = result["criteria"][0]["controls"][0]
        self.assertFalse(control["verified"])
        self.assertIn("observation_artifact_privacy_risk", control["failures"])

    def test_external_observation_record_rejects_private_or_unknown_fields(self):
        self.write_valid_external_record(raw_message="customer@example.com")

        result = evaluate_market_quality(
            self.spec([self.external_criterion()]),
            root=self.root,
            today=date(2026, 7, 22),
        )

        control = result["criteria"][0]["controls"][0]
        self.assertFalse(control["verified"])
        self.assertIn("observation_record_privacy_risk", control["failures"])
        self.assertIn("observation_record_unknown_fields", control["failures"])

    def test_external_observation_without_recorded_consent_is_rejected(self):
        self.write_valid_external_record(consent_recorded=False)

        result = evaluate_market_quality(
            self.spec([self.external_criterion()]),
            root=self.root,
            today=date(2026, 7, 22),
        )

        control = result["criteria"][0]["controls"][0]
        self.assertFalse(control["verified"])
        self.assertIn("observation_consent_missing", control["failures"])

    def test_external_observation_without_observer_reference_is_rejected(self):
        invalid_identities = [
            {"observer_reference": ""},
            {"observer_reference": {"id": "operator-01"}},
            {"observer_role": {"name": "support_operator"}},
        ]
        for invalid_identity in invalid_identities:
            with self.subTest(invalid_identity=invalid_identity):
                self.write_valid_external_record(**invalid_identity)
                result = evaluate_market_quality(
                    self.spec([self.external_criterion()]),
                    root=self.root,
                    today=date(2026, 7, 22),
                )

                control = result["criteria"][0]["controls"][0]
                self.assertFalse(control["verified"])
                self.assertIn("observer_identity_incomplete", control["failures"])

    def test_external_observation_for_another_criterion_is_rejected(self):
        self.write_valid_external_record(criterion_id="different_criterion")

        result = evaluate_market_quality(
            self.spec([self.external_criterion()]),
            root=self.root,
            today=date(2026, 7, 22),
        )

        control = result["criteria"][0]["controls"][0]
        self.assertFalse(control["verified"])
        self.assertIn("criterion_id_mismatch", control["failures"])

    def test_external_observation_for_another_control_is_rejected(self):
        self.write_valid_external_record(control_id="different_control")

        result = evaluate_market_quality(
            self.spec([self.external_criterion()]),
            root=self.root,
            today=date(2026, 7, 22),
        )

        control = result["criteria"][0]["controls"][0]
        self.assertFalse(control["verified"])
        self.assertIn("control_id_mismatch", control["failures"])

    def test_external_observation_with_unknown_schema_is_rejected(self):
        self.write_valid_external_record(schema_version="999")

        result = evaluate_market_quality(
            self.spec([self.external_criterion()]),
            root=self.root,
            today=date(2026, 7, 22),
        )

        control = result["criteria"][0]["controls"][0]
        self.assertFalse(control["verified"])
        self.assertIn("observation_schema_unsupported", control["failures"])

    def test_external_observation_without_artifacts_is_rejected(self):
        self.write_valid_external_record(artifacts=[])

        result = evaluate_market_quality(
            self.spec([self.external_criterion()]),
            root=self.root,
            today=date(2026, 7, 22),
        )

        control = result["criteria"][0]["controls"][0]
        self.assertFalse(control["verified"])
        self.assertIn("observation_artifacts_missing", control["failures"])

    def test_external_observation_cannot_reference_artifact_outside_repository(self):
        outside = self.root.parent / f"{self.root.name}-outside.txt"
        outside.write_text("outside repository\n")
        outside_sha256 = hashlib.sha256(outside.read_bytes()).hexdigest()
        self.write_valid_external_record(
            artifacts=[
                {"path": f"../{outside.name}", "sha256": outside_sha256}
            ]
        )

        result = evaluate_market_quality(
            self.spec([self.external_criterion()]),
            root=self.root,
            today=date(2026, 7, 22),
        )

        control = result["criteria"][0]["controls"][0]
        self.assertFalse(control["verified"])
        self.assertIn("observation_artifact_outside_repository", control["failures"])

    def test_external_observation_record_must_be_inside_repository(self):
        self.write_valid_external_record()
        outside = self.root.parent / f"{self.root.name}-pilot.json"
        outside.write_text((self.root / "pilot.json").read_text())
        criterion = self.external_criterion()
        criterion["controls"][0]["record"] = f"../{outside.name}"

        result = evaluate_market_quality(
            self.spec([criterion]),
            root=self.root,
            today=date(2026, 7, 22),
        )

        control = result["criteria"][0]["controls"][0]
        self.assertFalse(control["verified"])
        self.assertIn("observation_record_outside_repository", control["failures"])

    def test_stale_market_sources_make_the_criterion_unverified(self):
        result = evaluate_market_quality(
            self.spec([self.criterion("freshness", 100)]),
            root=self.root,
            today=date(2026, 11, 1),
        )

        self.assertEqual(result["verdict"], "NOT_MARKET_READY")
        self.assertEqual(result["criteria"][0]["effective_status"], "unverified")
        self.assertTrue(result["market_sources_stale"])

    def test_all_critical_passes_remain_pending_independent_provenance_review(self):
        core = self.criterion("core", 85)
        core["controls"] = [
            {"id": "core_check", "kind": "technical_check", "check_ids": ["core"]}
        ]
        polish = self.criterion("polish", 15, status="fail", critical=False)
        polish["controls"] = [
            {"id": "polish_one", "kind": "technical_check", "check_ids": ["one"]},
            {"id": "polish_two", "kind": "technical_check", "check_ids": ["two"]},
        ]
        result = evaluate_market_quality(
            self.spec([core, polish], threshold=85),
            root=self.root,
            today=date(2026, 7, 22),
            observed_checks=[
                {"id": "core", "status": "PASS"},
                {"id": "one", "status": "PASS"},
            ],
        )

        self.assertEqual(result["score"], 92.5)
        self.assertEqual(result["critical_failures"], [])
        self.assertEqual(result["verdict"], "NOT_MARKET_READY")
        self.assertEqual(
            result["evidence_state"],
            "STRUCTURALLY_COMPLETE_PENDING_INDEPENDENT_PROVENANCE_REVIEW",
        )

    def test_weights_must_total_one_hundred(self):
        with self.assertRaisesRegex(ValueError, "weights must total 100"):
            evaluate_market_quality(
                self.spec([self.criterion("bad_total", 99)]),
                root=self.root,
                today=date(2026, 7, 22),
            )

    def test_observed_checks_can_be_loaded_from_a_harness_snapshot(self):
        snapshot = self.root / "quality.json"
        snapshot.write_text(
            json.dumps(
                {
                    "technical_gate": "PASS",
                    "checks": [{"id": "browser", "status": "PASS"}],
                }
            )
        )

        self.assertEqual(
            _load_observed_checks(snapshot),
            [{"id": "browser", "status": "PASS"}],
        )

    def test_standalone_report_rejects_a_forged_partial_harness_snapshot(self):
        snapshot = self.root / "quality.json"
        snapshot.write_text(
            json.dumps(
                {
                    "technical_gate": "PASS",
                    "technical_checks_passed": 1,
                    "technical_checks_total": 1,
                    "checks": [{"id": "browser", "status": "PASS"}],
                }
            )
        )

        with self.assertRaisesRegex(ValueError, "full technical harness"):
            _load_observed_checks(snapshot, require_full_harness=True)

    def test_locked_market_policy_rejects_removed_critical_control(self):
        root = Path(__file__).resolve().parents[1]
        spec = json.loads(
            (root / "evaluation" / "market_quality_criteria.json").read_text()
        )
        buyer_validation = next(
            item
            for item in spec["criteria"]
            if item["id"] == "buyer_user_and_market_validation"
        )
        buyer_validation["controls"].pop()

        with self.assertRaisesRegex(ValueError, "market policy contract mismatch"):
            validate_market_policy(spec, required=True)

    def test_locked_market_policy_rejects_changed_scope_or_sources(self):
        root = Path(__file__).resolve().parents[1]
        spec = json.loads(
            (root / "evaluation" / "market_quality_criteria.json").read_text()
        )
        spec["benchmark_scope"] = "A weaker and unrelated benchmark."

        with self.assertRaisesRegex(ValueError, "market policy contract mismatch"):
            validate_market_policy(spec, required=True)

    def test_snapshot_verification_reuses_committed_as_of_date(self):
        snapshot = self.root / "market-result.json"
        snapshot.write_text(json.dumps({"as_of": "2026-07-22"}))

        self.assertEqual(
            _verification_evaluation_date(snapshot), date(2026, 7, 22)
        )


if __name__ == "__main__":
    unittest.main()
