# Limitations

- All tickets, orders, policies, names, drafts, and provider results are
  synthetic or recorded fixtures.
- The provider boundary makes no live model request and therefore does not prove
  latency, cost, retry behavior, model quality, or availability.
- The engine does not retrieve documents; approved source IDs are fixture inputs.
- The explicit intent lists and phrase-based injection tripwire are reviewable
  controls, not comprehensive natural-language classification or adversarial
  defense.
- There is no Gorgias, Shopify, carrier, order, refund, cancellation, email, or
  shopper-message adapter.
- There is no authentication, authorization, PII store, durable queue, rate
  limiting, audit database, monitoring, alerting, rollback, or incident response.
- A human approval record does not send anything; an independently authorized
  external adapter would still need least-privilege permissions and auditability.
- The 20/20 fixture agreement is an authored regression result. It must not be
  presented as live accuracy, macro-F1, production safety, or a client outcome.
- The static page's 15 rows are a curated narrative subset; the executable suite
  is the source for current control-path evidence.
