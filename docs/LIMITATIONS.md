# Limitations

## Data and commercial truth

- Every ticket, order, policy, source, draft, and provider result is synthetic or
  recorded. No client, customer, shopper, employer, or production data is used.
- The repository proves executable engineering behavior, not buyer demand,
  deployment, accuracy, deflection, cost savings, SLA impact, revenue, or another
  business result.
- The UI and API use Gorgias/Shopify only to explain the absent production
  boundary. The project is not affiliated with or endorsed by either company.

## Provider and decision quality

- There is no live model or retrieval request. The provider adapter is a
  deterministic local fixture and does not prove model latency, cost, quality,
  safety, retry behavior, or availability.
- Approved source IDs are supplied with synthetic context; their content is not
  retrieved or cryptographically verified.
- Explicit intent lists and phrase-based injection checks are narrow reviewable
  controls, not comprehensive classification or adversarial defense.
- The 20/20 fixture agreement measures authored regression behavior only. It is
  not accuracy, macro-F1, recall, production safety, or a client outcome.

## Application security

- The local API has no user authentication, authorization, tenancy, CSRF design,
  secret manager, abuse protection, audit identity, or privacy/retention policy.
  It must not be exposed to an untrusted network.
- CORS is restricted to one configured origin, but CORS is not authentication.
- There is no shopper-send, refund, cancellation, order-edit, Gorgias, Shopify,
  carrier, email, or customer-system adapter. Human approval does not cause an
  external action.
- The relational constraint and tests forbid automatic-send state, but a future
  external adapter would require its own least-privilege authorization, idempotency,
  audit, rollback, and human-approval enforcement.

## Data and distributed reliability

- SQLite is the observed local/test path. A disposable draft-PR CI job also
  builds the Compose stack, migrates PostgreSQL and exercises one narrow API/web
  smoke path. Neither is evidence of production data distribution, multi-region
  availability, encryption, backup/restore, retention, deletion, residency or
  subject-request handling.
- Docker was unavailable on the local execution machine. Container runtime
  evidence comes from the bounded CI job, not from a local or deployed environment.
- The API runs bounded context reads inside one request. There is no durable queue,
  job claim, outbox, lease, dead-letter state, distributed idempotency, worker
  autoscaling, backpressure across processes, or crash recovery after a remote
  effect.
- Aggregate metrics are local counts. There are no structured production logs,
  traces, protected metrics, dashboards, alerts, capacity model, SLO, on-call
  owner, reconciliation job, or incident runbook.

## Performance

- The async benchmark measures a deterministic local delay fixture. It proves the
  concurrency path is measurable and bounded; it cannot be generalized to a live
  provider, network, database, user latency, throughput, or infrastructure cost.
- The SQL query investigation uses a declared synthetic local workload and query
  plan. It does not prove PostgreSQL plans, production data distribution, cache
  behavior, concurrency, or capacity.
- No percentage from either artifact may be used as a customer or production
  improvement claim.

## Deployment and cloud

- CI is reviewable and remote draft-PR checks can verify the locked build. CI is
  not a deployed environment.
- There is no AWS account, infrastructure as code for a named environment,
  registry, TLS ingress, WAF, private networking, managed database, secrets,
  backups, logs, metrics, alerts, cost evidence, deployment record, or rollback
  exercise.
- Container base tags require digest pinning and regular rebuild/advisory review
  before a production supply-chain claim.

## Visual and accessibility scope

- The exact production build was reviewed at one desktop and one mobile width,
  with decision, loading, empty, and API-error states. Component/E2E tests cover critical
  semantics and mobile overflow.
- This is not a complete screen-reader, browser matrix, localization, zoom,
  high-contrast, cognitive-load, or assistive-technology audit.

## Market-quality status

- The full technical harness passes, but the dated market gate is 53/85 and
  `NOT_MARKET_READY` because eight critical criteria remain failed or partial.
- Passing authored fixtures, CI, visual review, Docker/PostgreSQL smoke, or a
  portfolio score cannot override missing identity/security, live contracts,
  governed feedback/outcomes/operations, or representative user/buyer evidence.
- `--allow-not-ready` exists only to verify this honest baseline in a draft; it
  does not waive the release gate.
