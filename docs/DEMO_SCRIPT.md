# 120-second demo script

## 0:00–0:20 — Problem and boundary

Open the README. Explain that routine WISMO can be draft-assisted, but returns,
order changes, and risky complaints need explicit control. Point out the
synthetic-data and non-affiliation boundary.

## 0:20–0:40 — Architecture

Open the Mermaid flow in `docs/ARCHITECTURE.md`. Trace one ticket through input
validation, deterministic routing, the recorded provider boundary, grounding,
and human review. State that there is no shopper-send adapter.

## 0:40–1:05 — Happy path

Run:

```bash
python3 evaluate.py
```

Show `routine-wismo`: the provider result cites only approved order/carrier
sources, clears the declared confidence threshold, and becomes a review-only
draft with `automatic_send_allowed=false`.

## 1:05–1:30 — Failure path

Show `provider-timeout`, `prompt-injection`, or `return-exception`. Explain why
the provider is bypassed or why output fails closed to human escalation.

## 1:30–1:50 — Verification

Run:

```bash
python3 -m unittest discover -s tests -v
```

Point to behavior tests for grounding, low confidence, provider failure, prompt
injection, and human rejection, plus public-page link and truth-boundary checks.

## 1:50–2:00 — Limitation and relevant next step

State that this is synthetic routing evidence, not live model quality. The next
paid slice would use approved representative tickets, platform test mode, a named
reviewer, and a written no-go rule for unsafe false negatives.
