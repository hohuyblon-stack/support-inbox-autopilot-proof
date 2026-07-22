# Async context benchmark

The application needs order and policy context before it can prepare a grounded
draft. Those reads are independent, so `collect_context` starts both under one
timeout with `asyncio.gather`.

## Reproduce

```bash
uv run python apps/api/benchmarks/async_context_benchmark.py \
  --iterations 60 \
  --delay-ms 10 \
  --verify
```

The checked-in run is
[`apps/api/benchmarks/results.json`](../apps/api/benchmarks/results.json). It was
recorded on Python 3.13.12 on an Apple Silicon Mac with 60 samples per path and
two deterministic 10 ms waits per sample. No network calls were made.

| Path | Median | p95 |
|---|---:|---:|
| Sequential reference | 24.183 ms | 24.286 ms |
| Application concurrent path | 12.274 ms | 12.359 ms |

The observed median ratio was 1.97x. This is evidence that the two waits overlap
and that the chosen concurrency path does useful work. It is not a production
throughput, external-provider latency, capacity or cost claim. Real results will
depend on network latency, connection pools, provider rate limits and database
capacity.

The test suite separately proves both adapter coroutines start before either is
released, and exercises the benchmark on a small workload.
