# Evaluation model

## Required offline run

```bash
python3 evaluate.py --output evaluation/results.json
python3 -m unittest discover -s tests -v
```

The committed evaluation contains 20 synthetic cases:

- ordinary WISMO and policy questions;
- delivered-not-received, damage, chargeback, wholesale, and return exceptions;
- return-label, address-change, and cancellation admin actions;
- missing order context and policy conflict;
- low-confidence, malformed, ungrounded, and timed-out provider behavior;
- prompt-injection wording; and
- explicit human rejection in the behavior tests.

## Metrics

### Route agreement

`passed / fixture_count`, where a pass means the deterministic observed route is
exactly the fixture's authored expected route. This is a regression contract,
not an estimate of intent-classification accuracy on unseen tickets.

### Automatic sends

The count of decisions with `automatic_send_allowed=true`. The required result
is zero because this proof does not contain a shopper-send adapter.

### Environment

- Python standard library only.
- Recorded provider outputs or a recorded timeout.
- No network request, paid model, live Gorgias/Shopify account, or API key.
- Fictional tickets and policy IDs.

## Current committed result

`evaluation/results.json` records 20 matching authored routes and zero automatic
sends for the committed fixture version. CI regenerates the file and diffs it
byte-for-byte so stale evidence fails the workflow.

## What is not measured

No claim is made about live intent accuracy, macro-F1, retrieval recall, draft
acceptance, edit rate, unsafe false-negative rate, latency, model cost, support
time, backlog, SLA, conversion, revenue, staffing, or customer satisfaction.
Those require representative approved data, a live provider contract, and a
named client reviewer.
