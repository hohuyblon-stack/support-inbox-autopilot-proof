# Debugging case study: a static pass table had no executable decision path

## Observed issue

At the start of the 2026-07-22 hardening pass, `index.html` displayed 15 rows in
which every observed route matched its expected route. The repository contained
no routing module, fixture runner, automated test, or CI workflow. A reviewer
could inspect the narrative, but could not reproduce why a row passed or prove
that a future safety-policy change preserved the boundary.

## Root cause

Expected and observed values were authored together in static HTML. That made
the table presentation evidence, not executable behavior. There was also no
separate provider contract, grounding check, confidence threshold, or regression
case for provider failure, prompt injection, or human rejection.

## Fix

The hardening pass added:

1. `readiness.py` for deterministic routing and structured provider-output gates;
2. `evaluation/scenarios.json` for 20 reviewable synthetic inputs;
3. `evaluate.py` for reproducible expected-versus-observed results;
4. behavior tests covering safe and failure paths; and
5. CI that regenerates and diffs `evaluation/results.json`.

The static page remains useful for a short walkthrough, but it now links to the
machine-readable result instead of carrying the entire proof claim by itself.

## Regression evidence

The CLI test deliberately changes a fixture's expected route and asserts that
the evaluator exits non-zero. The behavior suite also proves that unapproved
citations, low confidence, provider timeouts, missing order context, policy
conflict, high-risk intent, prompt-injection wording, and human rejection do not
unlock an automatic send.

## Remaining risk

The regression suite proves only the committed deterministic policy and recorded
provider contract. Live retrieval, model behavior, platform permissions, and
buyer-specific policies remain unimplemented and must be evaluated separately.
