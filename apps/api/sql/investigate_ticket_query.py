"""Reproduce the ticket-list index investigation with deterministic SQLite data."""

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import platform
import sqlite3
from statistics import median
import sys
from time import perf_counter


QUERY = """
SELECT id, external_id, status, created_at
FROM tickets
WHERE status = ?
  AND (created_at < ? OR (created_at = ? AND id < ?))
ORDER BY created_at DESC, id DESC
LIMIT ?
""".strip()

BASELINE_INDEX = "CREATE INDEX ix_tickets_status_created_at ON tickets(status, created_at)"
OPTIMIZED_INDEX = (
    "CREATE INDEX ix_tickets_status_created_at_id "
    "ON tickets(status, created_at, id)"
)
ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ARTIFACT = ROOT / "apps" / "api" / "sql" / "ticket-list-query-plan.json"


def percentile(samples: list[float], percent: float) -> float:
    ordered = sorted(samples)
    rank = (len(ordered) - 1) * percent / 100
    lower = int(rank)
    upper = min(lower + 1, len(ordered) - 1)
    weight = rank - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def seed_rows(row_count: int) -> list[tuple[str, str, str, str]]:
    base = datetime(2026, 7, 1, tzinfo=timezone.utc)
    rows = []
    for number in range(row_count):
        ticket_id = f"ticket-{number:029d}"
        status = "pending" if number % 3 else "evaluated"
        # Eight tickets share a timestamp to model burst ingestion and make the
        # id tie-breaker part of the real ordering work.
        created_at = (base + timedelta(seconds=number // 8)).isoformat()
        rows.append((ticket_id, f"EXT-{number:08d}", status, created_at))
    return rows


def create_database(index_sql: str, rows: list[tuple[str, str, str, str]]) -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.execute(
        """
        CREATE TABLE tickets (
            id TEXT PRIMARY KEY,
            external_id TEXT NOT NULL UNIQUE,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    connection.executemany(
        "INSERT INTO tickets(id, external_id, status, created_at) VALUES (?, ?, ?, ?)",
        rows,
    )
    connection.execute(index_sql)
    connection.execute("ANALYZE")
    return connection


def investigate_path(
    *,
    index_sql: str,
    rows: list[tuple[str, str, str, str]],
    runs: int,
) -> dict[str, object]:
    connection = create_database(index_sql, rows)
    status_filter = "pending"
    matching_rows = [row for row in rows if row[2] == status_filter]
    cursor_row = matching_rows[len(matching_rows) * 3 // 4]
    parameters = (
        status_filter,
        cursor_row[3],
        cursor_row[3],
        cursor_row[0],
        50,
    )
    plan = [
        row[3]
        for row in connection.execute(
            f"EXPLAIN QUERY PLAN {QUERY}",
            parameters,
        )
    ]
    expected = connection.execute(QUERY, parameters).fetchall()
    samples = []
    for _ in range(runs):
        started = perf_counter()
        observed = connection.execute(QUERY, parameters).fetchall()
        samples.append((perf_counter() - started) * 1_000)
        if observed != expected:
            raise RuntimeError("query result changed between benchmark runs")
    connection.close()
    digest = hashlib.sha256(
        json.dumps(expected, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {
        "query_plan": plan,
        "uses_temp_sort": any("TEMP B-TREE" in step for step in plan),
        "cursor_status": cursor_row[2],
        "result_count": len(expected),
        "result_sha256": digest,
        "latency": {
            "median_ms": round(median(samples), 4),
            "p95_ms": round(percentile(samples, 95), 4),
        },
    }


def run_investigation(*, row_count: int, runs: int) -> dict[str, object]:
    if row_count < 100:
        raise ValueError("row_count must be at least 100")
    if runs < 5:
        raise ValueError("runs must be at least 5")
    rows = seed_rows(row_count)
    baseline = investigate_path(
        index_sql=BASELINE_INDEX,
        rows=rows,
        runs=runs,
    )
    optimized = investigate_path(
        index_sql=OPTIMIZED_INDEX,
        rows=rows,
        runs=runs,
    )
    if baseline["result_sha256"] != optimized["result_sha256"]:
        raise RuntimeError("optimized index changed query results")
    return {
        "schema_version": 1,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "environment": {
            "python": platform.python_version(),
            "sqlite": sqlite3.sqlite_version,
            "platform": platform.platform(),
        },
        "workload": {
            "rows": row_count,
            "runs_per_path": runs,
            "page_size": 50,
            "status_filter": "pending",
            "cursor_status": baseline["cursor_status"],
            "burst_rows_per_timestamp": 8,
        },
        "query": " ".join(QUERY.split()),
        "baseline": {
            "index": "(status, created_at)",
            **baseline,
        },
        "optimized": {
            "index": "(status, created_at, id)",
            **optimized,
        },
        "interpretation": (
            "The id tie-breaker removes SQLite's temporary sort for the "
            "keyset-pagination order. Timings are local synthetic evidence, not "
            "a production latency claim."
        ),
    }


def verification_errors(
    observed: dict[str, object],
    committed: dict[str, object],
) -> list[str]:
    errors = []
    for label, result in (("observed", observed), ("committed", committed)):
        if result.get("schema_version") != 1:
            errors.append(f"{label}: unsupported schema_version")
            continue
        baseline = result.get("baseline", {})
        optimized = result.get("optimized", {})
        if baseline.get("uses_temp_sort") is not True:
            errors.append(f"{label}: baseline no longer records the temp sort")
        if optimized.get("uses_temp_sort") is not False:
            errors.append(f"{label}: optimized path still uses a temp sort")
        if baseline.get("result_sha256") != optimized.get("result_sha256"):
            errors.append(f"{label}: index variants return different rows")
        if baseline.get("index") != "(status, created_at)":
            errors.append(f"{label}: unexpected baseline index")
        if optimized.get("index") != "(status, created_at, id)":
            errors.append(f"{label}: unexpected optimized index")
        if "not a production" not in str(result.get("interpretation", "")):
            errors.append(f"{label}: missing production-claim boundary")
    if observed.get("workload") != committed.get("workload"):
        errors.append("observed workload differs from committed workload")
    if observed.get("query") != committed.get("query"):
        errors.append("observed query differs from committed query")
    observed_digest = observed.get("optimized", {}).get("result_sha256")
    committed_digest = committed.get("optimized", {}).get("result_sha256")
    if observed_digest != committed_digest:
        errors.append("deterministic result digest differs from committed evidence")
    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=int, default=30_000)
    parser.add_argument("--runs", type=int, default=300)
    output_mode = parser.add_mutually_exclusive_group()
    output_mode.add_argument("--output", type=Path)
    output_mode.add_argument("--verify", action="store_true")
    parser.add_argument("--artifact", type=Path, default=DEFAULT_ARTIFACT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = run_investigation(row_count=args.rows, runs=args.runs)
    if args.verify:
        committed = json.loads(args.artifact.read_text(encoding="utf-8"))
        errors = verification_errors(result, committed)
        if errors:
            for error in errors:
                print(f"FAIL: {error}", file=sys.stderr)
            return 1
        print("sql_query_plan_verification=PASS")
        return 0
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
