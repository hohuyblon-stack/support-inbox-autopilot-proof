import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from market_quality import evaluate_market_quality


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
            "criteria": criteria,
        }

    def test_critical_failure_blocks_a_high_numeric_score(self):
        result = evaluate_market_quality(
            self.spec(
                [
                    self.criterion("strong_noncritical", 90, critical=False),
                    self.criterion("missing_auth", 10, status="fail", critical=True),
                ]
            ),
            root=self.root,
            today=date(2026, 7, 22),
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

    def test_stale_market_sources_make_the_criterion_unverified(self):
        result = evaluate_market_quality(
            self.spec([self.criterion("freshness", 100)]),
            root=self.root,
            today=date(2026, 11, 1),
        )

        self.assertEqual(result["verdict"], "NOT_MARKET_READY")
        self.assertEqual(result["criteria"][0]["effective_status"], "unverified")
        self.assertTrue(result["market_sources_stale"])

    def test_all_critical_passes_and_threshold_produce_market_ready(self):
        result = evaluate_market_quality(
            self.spec(
                [
                    self.criterion("core", 85),
                    self.criterion("polish", 15, status="partial", critical=False),
                ],
                threshold=85,
            ),
            root=self.root,
            today=date(2026, 7, 22),
        )

        self.assertEqual(result["score"], 92.5)
        self.assertEqual(result["critical_failures"], [])
        self.assertEqual(result["verdict"], "MARKET_READY")

    def test_weights_must_total_one_hundred(self):
        with self.assertRaisesRegex(ValueError, "weights must total 100"):
            evaluate_market_quality(
                self.spec([self.criterion("bad_total", 99)]),
                root=self.root,
                today=date(2026, 7, 22),
            )


if __name__ == "__main__":
    unittest.main()
