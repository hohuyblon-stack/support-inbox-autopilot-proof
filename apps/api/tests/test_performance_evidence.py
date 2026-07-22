import json
from pathlib import Path

import pytest

from apps.api.benchmarks.async_context_benchmark import (
    percentile,
    run_benchmark,
    verification_errors as benchmark_verification_errors,
)
from apps.api.sql.investigate_ticket_query import (
    run_investigation,
    verification_errors as query_verification_errors,
)


ROOT = Path(__file__).resolve().parents[3]


def test_percentile_interpolates_observed_samples():
    assert percentile([1.0, 2.0, 3.0, 4.0, 5.0], 95) == pytest.approx(4.8)


@pytest.mark.asyncio
async def test_async_benchmark_exercises_application_concurrency_path():
    result = await run_benchmark(iterations=5, delay_ms=2)

    assert result["workload"]["network_calls"] == 0
    assert (
        result["application_concurrent"]["median_ms"]
        < result["baseline_sequential"]["median_ms"]
    )


def test_optimized_ticket_index_removes_temp_sort_without_changing_results():
    result = run_investigation(row_count=1_000, runs=5)

    assert result["workload"]["cursor_status"] == result["workload"]["status_filter"]
    assert result["baseline"]["uses_temp_sort"] is True
    assert result["optimized"]["uses_temp_sort"] is False
    assert (
        result["baseline"]["result_sha256"]
        == result["optimized"]["result_sha256"]
    )


def test_checked_in_results_keep_truth_boundaries_and_plan_invariants():
    benchmark = json.loads(
        (ROOT / "apps/api/benchmarks/results.json").read_text(encoding="utf-8")
    )
    investigation = json.loads(
        (ROOT / "apps/api/sql/ticket-list-query-plan.json").read_text(
            encoding="utf-8"
        )
    )

    assert benchmark["workload"]["network_calls"] == 0
    assert "not production" in benchmark["interpretation"]
    assert (
        benchmark["application_concurrent"]["median_ms"]
        < benchmark["baseline_sequential"]["median_ms"]
    )
    assert investigation["baseline"]["uses_temp_sort"] is True
    assert investigation["optimized"]["uses_temp_sort"] is False
    assert (
        investigation["baseline"]["result_sha256"]
        == investigation["optimized"]["result_sha256"]
    )
    assert "not a production" in investigation["interpretation"]
    assert benchmark_verification_errors(benchmark, benchmark) == []
    assert query_verification_errors(investigation, investigation) == []
