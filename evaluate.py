#!/usr/bin/env python3
"""Run the committed synthetic routing fixtures without network access."""

import argparse
from collections import Counter
import json
from pathlib import Path
from typing import Any, Dict

from readiness import evaluate_ticket


ROOT = Path(__file__).resolve().parent


class RecordedProvider:
    """Deterministic provider boundary backed only by committed fixture data."""

    def __init__(self, configuration: Dict[str, Any]):
        self.configuration = configuration

    def generate(self, ticket: Dict[str, Any]) -> Dict[str, Any]:
        if self.configuration.get("status") == "timeout":
            raise TimeoutError("recorded provider timeout")
        return self.configuration.get("result")


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Evaluate synthetic WISMO/returns routing fixtures offline."
    )
    parser.add_argument(
        "--fixtures",
        type=Path,
        default=ROOT / "evaluation" / "scenarios.json",
    )
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def build_report(fixtures):
    cases = []
    route_counts = Counter()
    automatic_sends = 0

    for scenario in fixtures:
        decision = evaluate_ticket(
            scenario.get("ticket"), RecordedProvider(scenario.get("provider", {}))
        )
        expected_route = scenario.get("expected_route")
        matched = decision["route"] == expected_route
        route_counts[decision["route"]] += 1
        automatic_sends += int(decision["automatic_send_allowed"])
        cases.append(
            {
                "id": scenario.get("id"),
                "ticket_id": decision.get("ticket_id"),
                "expected_route": expected_route,
                "observed_route": decision["route"],
                "reason": decision["reason"],
                "matched": matched,
                "automatic_send_allowed": decision["automatic_send_allowed"],
            }
        )

    passed = sum(item["matched"] for item in cases)
    return {
        "schema_version": "1.0",
        "environment": "offline_deterministic_fixture_run",
        "fixture_count": len(cases),
        "passed": passed,
        "all_routes_matched": passed == len(cases),
        "automatic_sends": automatic_sends,
        "route_counts": dict(sorted(route_counts.items())),
        "provider_boundary": "recorded_fixture_only_no_network",
        "claim_limit": "Synthetic routing evidence only; not live accuracy or client impact.",
        "cases": cases,
    }


def main():
    arguments = parse_arguments()
    fixtures = json.loads(arguments.fixtures.read_text(encoding="utf-8"))
    if not isinstance(fixtures, list):
        raise ValueError("fixtures must be a JSON list")
    report = build_report(fixtures)
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if arguments.output:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if report["all_routes_matched"] and report["automatic_sends"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
