# Architecture

## Purpose and trust boundary

The workbench is one real local vertical slice: an operator creates a synthetic
case, the API validates and persists it, two independent context reads run under
a shared timeout, deterministic safety rules gate a recorded provider result,
and the decision plus citations are stored for human review.

It deliberately has no shopper-send, refund, cancellation, order-edit, Gorgias,
Shopify, carrier, or model-provider adapter. `automatic_send_allowed` is false in
the domain result, API response, database constraint, component tests, and E2E
flow. This is defense in depth around an absent capability, not a disabled
production integration.

```text
Browser
  Next.js 16 / React 19 / strict TypeScript
  intake -> queue -> evaluation -> review states
                  |
                  v
FastAPI / Pydantic / OpenAPI
  validation -> error taxonomy -> bounded pagination -> metrics
        |                            |
        v                            v
SQLAlchemy async                deterministic safety engine
  tickets                           recorded provider output
  evaluations                       source/confidence/failure gates
  citations                              ^
        |                                |
        +---------- async context -------+
                    order + policy reads
                    gather + timeout
```

## Browser boundary

`apps/web/components/TicketWorkbench.tsx` is a client component because the
workflow owns mutable form, queue, error, evaluation, and review state. The page
shell and metadata remain server-renderable and the production build prerenders
the route.

The typed client in `apps/web/lib/api.ts` is the only HTTP boundary. It maps
non-success responses to safe categories, never handles a credential, and
exposes no send method. Loading, empty, error, ticket, evaluation, approval, and
rejection states are tested. The mobile layout stacks the same workflow rather
than hiding decision evidence.

## API and domain boundary

`apps/api/app/main.py` owns HTTP contracts and persistence orchestration.
Pydantic models bound string lengths, enum-like fields, source counts, pagination
and review input. FastAPI publishes the resulting OpenAPI schema.

`readiness.py` remains the deterministic domain gate. It handles malformed
context, high-risk/admin intents, policy conflict, source allowlisting,
confidence, provider failures, injection tripwire, and human review without
depending on FastAPI or SQLAlchemy. `apps/api/app/service.py` adapts persisted
ticket state and recorded context to that engine.

HTTP errors are bounded and explicit:

- `422` for request validation;
- `409 external_id_conflict` for a repeated external identity;
- `400 invalid_cursor` for an unknown pagination cursor;
- `404` for missing ticket/evaluation state; and
- `503 database_unavailable` for readiness failure.

## Relational model and transaction boundary

The Alembic migration creates three relations:

- `tickets`: bounded input, provider-fixture mode, workflow status, and creation
  time; `external_id` is unique;
- `evaluations`: route/reason/draft/confidence, review and external-action state,
  measured local latency, and a check constraint that forbids automatic send;
- `evaluation_citations`: normalized source IDs with a unique
  `(evaluation_id, source_id)` constraint.

`ix_tickets_status_created_at_id` supports the bounded queue query and its stable
ID tie-breaker. The committed
query investigation records the actual local plan and workload; it is not a
production throughput claim.

The API does not hold a database transaction while waiting for context adapters.
It reads and snapshots the ticket, closes that session, runs bounded async work,
then opens a short write transaction to persist the evaluation and ticket state.
A real distributed design would also need a durable job claim, lease/outbox,
idempotent provider contract, and crash recovery between remote effect and local
commit.

SQLite provides a zero-service local/test path. The Compose path uses PostgreSQL
with the same SQLAlchemy model and Alembic migration. Docker was unavailable on
the local execution machine, but the draft-PR `docker-postgres-smoke` job built
the images, ran the migration, reached both health endpoints, and exercised one
create/evaluate/metrics path against the disposable PostgreSQL service.

## Async boundary

`collect_context` starts the order and policy adapters together with
`asyncio.gather` inside `asyncio.timeout`. The rendezvous test fails if one call
waits for the other to finish, so it proves concurrent start without relying on
fragile wall-clock timing. Timeout/failure maps to human escalation.

The benchmark compares sequential and concurrent execution of those exact local
adapters over a declared workload and environment. The adapter delay is recorded
fixture behavior. The result demonstrates scheduling and measurement mechanics;
it must not be generalized to a live provider, network, queue, or production
latency.

## Observability

The API exposes health separately from database readiness. `/api/v1/metrics`
returns aggregate ticket/evaluation/route counts and the automatic-send count;
it includes no message, order ID, source ID, or user data. Evaluation records
include their safe reason, citations, review state, action state, and measured
local duration.

Production still requires structured logs, traces, authenticated metrics,
alerts, redaction policy, retention, service ownership, and incident runbooks.

## Deployment path

- Locked `uv.lock` and `package-lock.json` files make dependency resolution
  reviewable.
- CI runs deterministic Python, API, migration, SQL/performance, TypeScript,
  component, production-build, dependency-audit, and cross-stack browser checks.
- Dockerfiles separate build/runtime stages and use non-root runtime users.
- Compose wires the web container, API, migration, PostgreSQL health, and local
  ports without provisioning infrastructure.

There is no claim of AWS operation. A production cloud step would require image
digest pinning, registry and secret management, TLS/ingress, private database
networking, backups, migrations as a controlled job, health/readiness policy,
logs/metrics/alerts, cost notes, rollback, and explicit deployment authorization.

## Key tradeoffs

- **One repository, one journey.** The existing safety engine is reused rather
  than duplicated in a fashionable microservice layout.
- **Recorded provider, real boundaries.** The app proves API/data/async/UI
  behavior without pretending a live model or platform contract exists.
- **SQLite plus PostgreSQL path.** SQLite keeps local review zero-service; the
  disposable CI stack verifies PostgreSQL migration and a narrow smoke journey.
  Neither path proves production data distribution, recovery or capacity.
- **No background queue yet.** The bounded concurrent work completes in the API
  request so failure is easy to inspect. A queue would be required before slow or
  durable production work, but adding one solely for keywords would obscure the
  current proof.
- **No authentication in a local proof.** The service binds to loopback in manual
  commands and must not be exposed publicly. Production auth is a blocking gap,
  not deferred polish.
