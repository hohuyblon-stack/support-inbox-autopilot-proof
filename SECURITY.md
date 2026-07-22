# Security policy

## Supported scope

This repository is an independent local engineering sample, not a hosted
service. It contains a real Next.js/FastAPI/relational workflow but no live
Gorgias, Shopify, carrier, model, email, refund, cancellation, order-edit, or
shopper-send integration.

The current API has no authentication, authorization, tenancy, or production
privacy controls. Bind it to loopback for local review. Do not expose it to an
untrusted network or enter real customer, ticket, order, policy, credential, or
private business data.

Useful reports include:

- validation or pagination bypass;
- database constraint, citation, or review-state bypass;
- a path that permits `automatic_send_allowed=true`;
- CORS, browser, API, container, or dependency weaknesses;
- accidental network/provider activity that contradicts the fixture boundary;
- credential, synthetic-boundary, or private-data exposure; and
- migration, replay, concurrency, or transaction behavior that could corrupt
  local evidence.

## Reporting

Use the repository's private GitHub security-advisory flow. Do not paste a live
secret, customer record, private URL, exploit payload tied to a real system, or
other sensitive reproduction into a public issue.

Include the affected commit/version, a minimal synthetic reproduction, expected
and observed behavior, and the impacted boundary. If a credential is exposed,
revoke it at the provider first, preserve incident evidence privately, and then
follow an agreed history-remediation plan. Deleting the visible line alone is not
revocation.

## Local configuration

- Python and Node dependency graphs are locked; CI installs from those locks.
- The frontend production build and npm advisory audit are verification gates.
- The API accepts one configured CORS origin with credentials disabled. CORS is
  not authentication.
- SQLite state, virtual environments, Node modules, build output, Playwright
  traces, and local environment files are ignored.
- Docker runtime users are non-root. Container tags and transitive dependencies
  still require ongoing digest/advisory review.
- No `.env` file is loaded or committed by application code. Configuration comes
  from explicit process/container environment variables.

## Production blockers

Before adapting this proof to real support work, add and review:

- authenticated users and role authorization;
- least-privilege platform/provider access and secret rotation;
- request/source verification, data minimization, encryption and retention;
- a durable queue/outbox, idempotent external contract, replay ownership and
  crash recovery;
- private networking, TLS/ingress, rate limits and abuse protection;
- controlled migrations, backups, restore tests and rollback;
- redacted logs, protected metrics, traces, alerts, SLOs and incident ownership;
- provider-specific timeout, cost, rate-limit and evaluation policy; and
- explicit human authorization for every customer-facing or order-changing
  action.

Passing the local test suite or draft-PR CI does not make the application safe to
deploy publicly.
