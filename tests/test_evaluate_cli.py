import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "evaluate.py"
FIXTURES = ROOT / "evaluation" / "scenarios.json"


class EvaluationCliTests(unittest.TestCase):
    def test_cli_writes_traceable_offline_summary(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_path = Path(temporary_directory) / "results.json"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(CLI),
                    "--fixtures",
                    str(FIXTURES),
                    "--output",
                    str(output_path),
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            report = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(report["fixture_count"], 20)
        self.assertEqual(report["passed"], 20)
        self.assertTrue(report["all_routes_matched"])
        self.assertEqual(report["automatic_sends"], 0)
        self.assertEqual(report["environment"], "offline_deterministic_fixture_run")
        self.assertEqual(sum(report["route_counts"].values()), 20)
        self.assertEqual(len(report["cases"]), 20)

    def test_cli_fails_when_an_expected_route_does_not_match(self):
        scenario = json.loads(FIXTURES.read_text(encoding="utf-8"))[0]
        scenario["expected_route"] = "escalate"

        with tempfile.TemporaryDirectory() as temporary_directory:
            fixture_path = Path(temporary_directory) / "mismatch.json"
            fixture_path.write_text(json.dumps([scenario]), encoding="utf-8")
            completed = subprocess.run(
                [sys.executable, str(CLI), "--fixtures", str(fixture_path)],
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(completed.returncode, 1)
        report = json.loads(completed.stdout)
        self.assertFalse(report["all_routes_matched"])
        self.assertEqual(report["passed"], 0)


if __name__ == "__main__":
    unittest.main()
