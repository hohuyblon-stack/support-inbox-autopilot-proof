# Backend engineering evidence

This document maps the local FastAPI implementation to inspectable evidence.
All records and provider responses are synthetic. The API has no adapter that
can send a customer message or mutate a support platform.

## Request path

1. `POST /api/v1/tickets` validates and stores an immutable synthetic ticket.
2. `POST /api/v1/tickets/{id}/evaluate` copies the scalar ticket fields into a
   frozen snapshot, closes the database session, and only then awaits the two
   independent context adapters.
3. The deterministic policy engine validates intent, citations, confidence and
   prompt-injection markers.
4. A new short database transaction stores exactly one evaluation per ticket.
   A unique constraint and retry lookup make sequential and concurrent request
   retries idempotent.
5. `POST /api/v1/evaluations/{id}/review` records a human decision. Even an
   approved draft remains `automatic_send_allowed=false`; it is only marked
   ready for a separately authorized human send.

The session boundary in step 2 matters: a slow provider does not retain a
database connection or open transaction. Tests cover sequential and concurrent
evaluate retries, duplicate context sources, timeouts, unexpected provider
errors, filtered cursors, metrics and the no-automatic-send invariant.

## API and persistence boundaries

- Pydantic request models bound string lengths, allowed intents, provider modes,
  and source-list cardinality.
- The `/api/v1` prefix leaves room for an explicit compatibility boundary.
- Cursor pagination is bounded to 100 rows and rejects a cursor from a different
  status filter.
- SQLAlchemy uses an async driver for both SQLite and PostgreSQL.
- Alembic owns the schema. `AUTO_CREATE_SCHEMA=true` exists for isolated tests
  and the zero-setup SQLite demo; Compose disables it and runs migrations first.
- Check and unique constraints keep invalid route, review, send and duplicate
  evaluation states out of durable storage.
- `/healthz` proves the process responds; `/readyz` separately checks database
  connectivity.

## External and AI boundary

`DeterministicContextProvider` is offline. It models two independent context
reads so concurrency, timeout, grounding and fallback behavior are executable
without keys or network access. Unexpected ordinary provider exceptions are
collapsed into the safe `provider_failure` category; provider details are not
returned to the client. Task cancellation is not swallowed.

This proves the boundary and controls, not a live Gorgias or model integration.
A production adapter still needs authentication, request tracing, bounded
retries for retry-safe reads, rate-limit handling, structured logs and secret
management. Review records are last-write-wins in this local proof; a production
system also needs reviewer identity, append-only decision history and optimistic
concurrency control.

## Verification entry points

```bash
uv sync --dev
uv run pytest -q apps/api/tests
uv run python -m apps.api.app.migrations
uv run python apps/api/scripts/benchmark_context.py --verify
uv run python apps/api/scripts/explain_queue_query.py --verify
```

Use a temporary `DATABASE_URL` for the migration command if the default local
SQLite state should not be changed.
