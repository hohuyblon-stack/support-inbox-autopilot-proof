import tempfile
import unittest
from datetime import date
from pathlib import Path

from scripts.quality_harness import (
    TECHNICAL_COMMANDS,
    _evaluation_date_for_run,
    evaluate_market_from_checks,
    exit_code_for_result,
)


class QualityHarnessCompositionTests(unittest.TestCase):
    def test_technical_failure_takes_precedence_over_market_block(self):
        result = {"technical_gate": "FAIL", "overall_verdict": "NOT_MARKET_READY"}

        self.assertEqual(exit_code_for_result(result, allow_not_ready=False), 1)
        whitespace_check = next(
            check for check in TECHNICAL_COMMANDS if check["id"] == "whitespace_gate"
        )
        command = " ".join(whitespace_check["command"])
        self.assertIn("4b825dc642cb6eb9a060e54bf8d69288fbee4904", command)
        self.assertIn("git diff --check HEAD", command)
        browser_check = next(
            check
            for check in TECHNICAL_COMMANDS
            if check["id"] == "browser_api_database_journey"
        )
        self.assertEqual(browser_check.get("env"), {"CI": "1"})

    def test_current_technical_results_are_supplied_to_market_controls(self):
        root = Path(tempfile.mkdtemp())
        (root / "evidence.txt").write_text("evidence\n")
        spec = {
            "schema_version": "2.0",
            "benchmark_scope": "Narrow workflow.",
            "market_checked_at": "2026-07-22",
            "max_source_age_days": 90,
            "threshold": 85,
            "system_under_test_paths": ["evidence.txt"],
            "criteria": [
                {
                    "id": "operator_flow",
                    "label": "Operator flow",
                    "weight": 100,
                    "critical": True,
                    "status": "fail",
                    "market_expectation": "Observed workflow.",
                    "evidence": ["evidence.txt"],
                    "sources": ["https://docs.gorgias.com/en-US/example-1"],
                    "gap": "None after verification.",
                    "controls": [
                        {
                            "id": "browser_journey",
                            "kind": "technical_check",
                            "check_ids": ["browser_api_database_journey"],
                        }
                    ],
                }
            ],
        }

        result = evaluate_market_from_checks(
            spec,
            root=root,
            checks=[{"id": "browser_api_database_journey", "status": "PASS"}],
            today=date(2026, 7, 22),
        )

        self.assertEqual(result["verdict"], "NOT_MARKET_READY")
        self.assertEqual(
            result["evidence_state"],
            "STRUCTURALLY_COMPLETE_PENDING_INDEPENDENT_PROVENANCE_REVIEW",
        )

        snapshot = root / "harness.json"
        snapshot.write_text('{"as_of": "2026-07-22"}')
        self.assertEqual(
            _evaluation_date_for_run(
                snapshot,
                verify=True,
                current_date=date(2026, 8, 1),
            ),
            date(2026, 7, 22),
        )


if __name__ == "__main__":
    unittest.main()
