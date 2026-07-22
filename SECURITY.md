# Security policy

## Scope

This repository is an offline independent sample. It contains no live Gorgias,
Shopify, model-provider, order, refund, or shopper-message integration.

Do not use real tickets, customer data, credentials, platform exports, or private
policy documents in issues, fixtures, pull requests, screenshots, or demos.

## Reporting

Use the repository's private GitHub security-advisory flow for a suspected
vulnerability or accidentally published secret. Do not paste sensitive evidence
into a public issue.

If a secret is ever committed, revoke it at the provider first, preserve the
incident evidence privately, and then remove it from the repository and history
using an agreed response plan. Deleting the visible line alone is insufficient.

## Production boundary

Before adapting the proof to a real support environment, add authenticated
request verification, least-privilege platform access, encrypted secret storage,
data-retention rules, PII redaction, provider timeouts and budgets, durable audit
events, monitoring, incident ownership, and explicit authorization for every
customer-facing or order-changing action.
