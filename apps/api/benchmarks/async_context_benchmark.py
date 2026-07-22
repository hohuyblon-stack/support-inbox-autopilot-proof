"""Compare sequential and concurrent reads for the real context boundary.

The deterministic adapter sleeps to model I/O without making a network call.
This measures scheduling overhead and elapsed latency, not production capacity.
"""

import argparse
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
from statistics import median
import sys
from time import perf_counter
from typing import Awaitable, Callable

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
DEFAULT_ARTIFACT = ROOT / "apps" / "api" / "benchmarks" / "results.json"

from apps.api.app.providers import (  # noqa: E402
    DeterministicContextProvider,
    collect_context,
)


async def collect_context_sequential(
    provider: DeterministicContextProvider,
    *,
    timeout_seconds: float,
) -> list[dict[str, object]]:
    """Reference implementation used only as the measured baseline."""

    async with asyncio.timeout(timeout_seconds):
        order = await provider.fetch_order("ORDER-BENCH-001", "in_transit", "success")
        policy = await provider.fetch_policy(
            ["policy-shipping-v1", "order-bench-001"],
            "success",
        )
    return [order, policy]


def percentile(samples: list[float], percent: float) -> float:
    if not samples:
        raise ValueError("at least one sample is required")
    ordered = sorted(samples)
    rank = (len(ordered) - 1) * percent / 100
    lower = int(rank)
    upper = min(lower + 1, len(ordered) - 1)
    weight = rank - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


async def timed(operation: Callable[[], Awaitable[object]]) -> float:
    started = perf_counter()
    await operation()
    return (perf_counter() - started) * 1000


def summarize(samples: list[float]) -> dict[str, float]:
    return {
        "min_ms": round(min(samples), 3),
        "median_ms": round(median(samples), 3),
        "p95_ms": round(percentile(samples, 95), 3),
        "max_ms": round(max(samples), 3),
    }


async def run_benchmark(*, iterations: int, delay_ms: float) -> dict[str, object]:
    if iterations < 5:
        raise ValueError("iterations must be at least 5")
    if not 0 < delay_ms <= 1_000:
        raise ValueError("delay_ms must be greater than 0 and at most 1000")

    provider = DeterministicContextProvider(delay_seconds=delay_ms / 1_000)
    timeout_seconds = max(1, delay_ms / 100)

    async def sequential() -> object:
        return await collect_context_sequential(
            provider,
            timeout_seconds=timeout_seconds,
        )

    async def concurrent() -> object:
        return await collect_context(
            provider,
            order_id="ORDER-BENCH-001",
            tracking_status="in_transit",
            approved_source_ids=["policy-shipping-v1", "order-bench-001"],
            mode="success",
            timeout_seconds=timeout_seconds,
        )

    # Warm both paths before collecting samples. Alternate order to reduce
    # one-sided scheduler and thermal bias.
    await sequential()
    await concurrent()
    sequential_samples: list[float] = []
    concurrent_samples: list[float] = []
    for iteration in range(iterations):
        if iteration % 2 == 0:
            sequential_samples.append(await timed(sequential))
            concurrent_samples.append(await timed(concurrent))
        else:
            concurrent_samples.append(await timed(concurrent))
            sequential_samples.append(await timed(sequential))

    sequential_summary = summarize(sequential_samples)
    concurrent_summary = summarize(concurrent_samples)
    speedup = sequential_summary["median_ms"] / concurrent_summary["median_ms"]
    return {
        "schema_version": 1,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
        "workload": {
            "adapter": "DeterministicContextProvider",
            "context_reads_per_evaluation": 2,
            "delay_per_read_ms": delay_ms,
            "iterations_per_path": iterations,
            "network_calls": 0,
        },
        "baseline_sequential": sequential_summary,
        "application_concurrent": concurrent_summary,
        "median_speedup": round(speedup, 3),
        "interpretation": (
            "Synthetic deterministic I/O benchmark; demonstrates overlap of two "
            "independent waits, not production throughput or provider latency."
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
        workload = result.get("workload", {})
        baseline = result.get("baseline_sequential", {})
        concurrent = result.get("application_concurrent", {})
        if workload.get("network_calls") != 0:
            errors.append(f"{label}: benchmark must remain offline")
        if concurrent.get("median_ms", float("inf")) >= baseline.get(
            "median_ms", 0
        ):
            errors.append(f"{label}: concurrent median must beat sequential median")
        for path_name, summary in (("baseline", baseline), ("concurrent", concurrent)):
            values = [
                summary.get("min_ms", -1),
                summary.get("median_ms", -1),
                summary.get("p95_ms", -1),
                summary.get("max_ms", -1),
            ]
            if not (0 < values[0] <= values[1] <= values[2] <= values[3]):
                errors.append(f"{label}: invalid {path_name} timing summary")
        if "not production" not in str(result.get("interpretation", "")):
            errors.append(f"{label}: missing production-claim boundary")
    if observed.get("workload") != committed.get("workload"):
        errors.append("observed workload differs from committed workload")
    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=60)
    parser.add_argument("--delay-ms", type=float, default=10)
    output_mode = parser.add_mutually_exclusive_group()
    output_mode.add_argument("--output", type=Path)
    output_mode.add_argument("--verify", action="store_true")
    parser.add_argument("--artifact", type=Path, default=DEFAULT_ARTIFACT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = asyncio.run(
        run_benchmark(iterations=args.iterations, delay_ms=args.delay_ms)
    )
    if args.verify:
        committed = json.loads(args.artifact.read_text(encoding="utf-8"))
        errors = verification_errors(result, committed)
        if errors:
            for error in errors:
                print(f"FAIL: {error}", file=sys.stderr)
            return 1
        print("async_benchmark_verification=PASS")
        return 0
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
