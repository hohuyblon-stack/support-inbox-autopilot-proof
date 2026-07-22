# 150-second integrated demo script

Use only synthetic input. Start the migrated API and Next.js frontend with the
README quick start before recording.

## 0:00–0:20 — State the boundary

Show the masthead and amber boundary.

> This is a real local Next.js, FastAPI, and relational workflow using synthetic
> data and a recorded provider. It cannot send a message or change an order. I am
> demonstrating engineering behavior, not a client result or live-platform claim.

## 0:20–0:45 — Create persisted state

Use the default WISMO case and choose `Grounded output`. Select **Create synthetic
ticket**.

Point out:

- strict typed form values reach FastAPI validation;
- the API inserts a ticket with unique external identity; and
- the queue refreshes from the relational store.

## 0:45–1:15 — Run the real decision path

Select **Evaluate**.

> The API closes its read session before external-style work. Order and policy
> context start concurrently under one timeout. The deterministic engine then
> checks intent, context, approved citations and confidence before one short
> transaction stores the evaluation and citations.

Show the route, human-readable reason, confidence, measured local latency,
citations, review state, blocked external action, and automatic-send count of
zero.

## 1:15–1:35 — Record human review

Select **Record approval**.

> Approval is persisted as readiness for a separately authorized human action.
> There is no send button, endpoint, platform credential, or shopper adapter in
> this repository.

## 1:35–1:55 — Show a failure

Create a second ticket with `Timeout`, `Low confidence`, or `Unapproved citation`
and evaluate it.

Show that it becomes a human escalation, produces no draft/send path, and leaves
the failure reason visible.

## 1:55–2:20 — Show verification

Show the relevant commands rather than scrolling through all source:

```bash
uv run --python 3.13 pytest -q apps/api/tests
cd apps/web && npm run verify && npm run test:e2e
```

Then show the committed async benchmark and SQL query-plan artifact. Explain that
both use declared synthetic local workloads and are not production claims.

## 2:20–2:30 — Close with the production gap

> The next real-client step is not autonomous sending. It is a bounded readiness
> sprint using approved policies, lawful sanitized cases, a named reviewer,
> platform contracts, authentication, privacy design, monitoring, and explicit
> go/no-go rules.

Do not say “production-ready,” “enterprise-grade,” “deployed,” “accurate,” or
quote a time/cost/business improvement not supported by separately observed
evidence.
