"""Run the complete technical harness, then apply the market-quality gate.

The command exits non-zero while the market gate is unmet even when every
technical check passes. Use ``--allow-not-ready`` only to reproduce and record
the honest baseline in CI or a draft review.
"""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
from typing import Any, Dict, List, Optional


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from market_quality import evaluate_market_quality  # noqa: E402


TECHNICAL_COMMANDS = [
    {
        "id": "python_locked_install",
        "command": ["uv", "sync", "--frozen", "--python", "3.13"],
        "cwd": ROOT,
    },
    {
        "id": "node_locked_install",
        "command": ["npm", "ci"],
        "cwd": ROOT / "apps" / "web",
    },
    {
        "id": "offline_and_gate_unit_tests",
        "command": [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
        "display_command": ["python", "-m", "unittest", "discover", "-s", "tests", "-v"],
        "cwd": ROOT,
    },
    {
        "id": "api_backend_tests",
        "command": ["uv", "run", "--python", "3.13", "pytest", "-q", "apps/api/tests"],
        "cwd": ROOT,
    },
    {
        "id": "async_benchmark_snapshot",
        "command": [
            "uv",
            "run",
            "--python",
            "3.13",
            "python",
            "apps/api/scripts/benchmark_context.py",
            "--verify",
        ],
        "cwd": ROOT,
    },
    {
        "id": "sql_query_plan_snapshot",
        "command": [
            "uv",
            "run",
            "--python",
            "3.13",
            "python",
            "apps/api/scripts/explain_queue_query.py",
            "--verify",
        ],
        "cwd": ROOT,
    },
    {
        "id": "frontend_types_components_and_build",
        "command": ["npm", "run", "verify"],
        "cwd": ROOT / "apps" / "web",
    },
    {
        "id": "frontend_production_dependency_audit",
        "command": ["npm", "audit", "--omit=dev", "--audit-level=high"],
        "cwd": ROOT / "apps" / "web",
    },
    {
        "id": "browser_api_database_journey",
        "command": ["npm", "run", "test:e2e"],
        "cwd": ROOT / "apps" / "web",
    },
    {
        "id": "whitespace_gate",
        "command": ["git", "diff", "--check"],
        "cwd": ROOT,
    },
]


def _run_command(check: Dict[str, Any]) -> Dict[str, Any]:
    try:
        completed = subprocess.run(
            check["command"],
            cwd=check["cwd"],
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return {
            "id": check["id"],
            "command": shlex.join(check.get("display_command", check["command"])),
            "working_directory": str(Path(check["cwd"]).relative_to(ROOT) or Path(".")),
            "status": "FAIL",
            "returncode": None,
            "error_category": type(error).__name__,
        }

    result = {
        "id": check["id"],
        "command": shlex.join(check.get("display_command", check["command"])),
        "working_directory": str(Path(check["cwd"]).relative_to(ROOT) or Path(".")),
        "status": "PASS" if completed.returncode == 0 else "FAIL",
        "returncode": completed.returncode,
    }
    if completed.returncode != 0:
        result["stdout_tail"] = completed.stdout[-2000:]
        result["stderr_tail"] = completed.stderr[-2000:]
    return result


def _fixture_reproduction() -> Dict[str, Any]:
    with tempfile.NamedTemporaryFile(suffix=".json") as output:
        completed = subprocess.run(
            [sys.executable, "evaluate.py", "--output", output.name],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        expected = (ROOT / "evaluation" / "results.json").read_bytes()
        observed = Path(output.name).read_bytes() if completed.returncode == 0 else b""
    matches = completed.returncode == 0 and observed == expected
    result = {
        "id": "fixture_reproduction",
        "command": "python evaluate.py --output <temporary-json>",
        "working_directory": ".",
        "status": "PASS" if matches else "FAIL",
        "returncode": completed.returncode,
        "expected_sha256": hashlib.sha256(expected).hexdigest(),
        "observed_sha256": hashlib.sha256(observed).hexdigest(),
    }
    if not matches:
        result["stdout_tail"] = completed.stdout[-2000:]
        result["stderr_tail"] = completed.stderr[-2000:]
    return result


def run_harness() -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    for check in TECHNICAL_COMMANDS[:3]:
        checks.append(_run_command(check))
        if checks[-1]["status"] == "FAIL":
            break
    if all(check["status"] == "PASS" for check in checks):
        checks.append(_fixture_reproduction())
    if all(check["status"] == "PASS" for check in checks):
        for check in TECHNICAL_COMMANDS[3:]:
            checks.append(_run_command(check))
            if checks[-1]["status"] == "FAIL":
                break

    technical_gate = (
        "PASS"
        if len(checks) == len(TECHNICAL_COMMANDS) + 1
        and all(check["status"] == "PASS" for check in checks)
        else "FAIL"
    )
    market_spec = json.loads(
        (ROOT / "evaluation" / "market_quality_criteria.json").read_text()
    )
    market = evaluate_market_quality(market_spec, root=ROOT)
    overall_verdict = (
        "MARKET_READY"
        if technical_gate == "PASS" and market["verdict"] == "MARKET_READY"
        else "NOT_MARKET_READY"
    )
    return {
        "schema_version": "1.0",
        "as_of": date.today().isoformat(),
        "technical_gate": technical_gate,
        "technical_checks_passed": sum(item["status"] == "PASS" for item in checks),
        "technical_checks_total": len(TECHNICAL_COMMANDS) + 1,
        "market_quality_score": market["score"],
        "market_quality_threshold": market["threshold"],
        "market_quality_verdict": market["verdict"],
        "market_critical_failures": market["critical_failures"],
        "overall_verdict": overall_verdict,
        "checks": checks,
        "claim_limit": (
            "Technical execution cannot substitute for live contracts, production "
            "operation, representative user validation, buyer demand, or outcomes."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "evaluation" / "quality_harness_results.json",
    )
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--allow-not-ready", action="store_true")
    args = parser.parse_args()

    result = run_harness()
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.verify:
        if not args.output.exists() or args.output.read_text() != rendered:
            print("quality_harness_snapshot_verification=FAIL")
            return 2
        print("quality_harness_snapshot_verification=PASS")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered)

    print(
        f"technical_gate={result['technical_gate']} "
        f"checks={result['technical_checks_passed']}/{result['technical_checks_total']}"
    )
    print(
        f"market_quality_verdict={result['market_quality_verdict']} "
        f"score={result['market_quality_score']:g}/{result['market_quality_threshold']:g} "
        f"critical_failures={len(result['market_critical_failures'])}"
    )
    print(f"overall_verdict={result['overall_verdict']}")
    if result["overall_verdict"] != "MARKET_READY" and not args.allow_not_ready:
        return 3
    return 0 if result["technical_gate"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
