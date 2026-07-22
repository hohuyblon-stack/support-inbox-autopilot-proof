# Ticket-list query investigation

The ticket list uses keyset pagination ordered by `created_at DESC, id DESC`.
The `id` tie-breaker makes ordering stable when multiple tickets share a
timestamp. The first index draft covered only `(status, created_at)`, leaving
SQLite to perform a temporary sort for the final ordering term.

## Reproduce

```bash
uv run python apps/api/sql/investigate_ticket_query.py \
  --rows 30000 \
  --runs 300 \
  --verify
```

The script builds isolated in-memory databases from the same deterministic
30,000-row workload. Eight rows share each timestamp to model burst ingestion.
It runs the application query with a status filter, cursor boundary and 50-row
limit, then verifies both index variants return the same SHA-256 result digest.

The checked-in evidence is
[`apps/api/sql/ticket-list-query-plan.json`](../apps/api/sql/ticket-list-query-plan.json).

| Index | Plan finding | Median | p95 |
|---|---|---:|---:|
| `(status, created_at)` | `USE TEMP B-TREE FOR ORDER BY` | 6.1206 ms | 6.2484 ms |
| `(status, created_at, id)` | index search; no temp sort | 0.3186 ms | 0.3344 ms |

The migration and ORM model use the three-column index. The local workload
showed a large timing difference, but it is deliberately not generalized into
a production percentage claim. PostgreSQL may choose a different plan based on
statistics, row distribution and cache state; production validation should use
`EXPLAIN (ANALYZE, BUFFERS)` against representative non-sensitive data.

Normalization is intentionally simple: tickets, evaluations and citations are
separate relations; citations use a unique `(evaluation_id, source_id)` pair.
One evaluation per ticket is enforced because the ticket input is immutable and
retrying the POST must not duplicate external work or durable records.
