# Market-quality gate

## Current verdict

**`NOT_MARKET_READY` — 53/85 with eight failed or partial critical gates.**

The technical harness passes 11/11 checks. That proves the declared local
software path executes; it does not override the market verdict. The default
market gate exits non-zero until both conditions are true:

1. the weighted score is at least 85; and
2. every critical criterion is `pass` with present evidence and market sources
   checked within the last 90 days.

No number can compensate for a critical failure.

## Benchmark scope

The comparison is intentionally narrow: an operator creates a support case,
evaluates grounded evidence, records a human decision, and has no automatic-send
capability. The workbench is not benchmarked as a replacement for Gorgias,
Intercom, Zendesk, or an autonomous customer agent.

Current official product documentation establishes the category expectations
used in the registry:

- Gorgias describes trusted knowledge, configurable handover, response/source
  reasoning, direct feedback, pre-live test conversations, analytics, and
  governed connected actions.
- Intercom documents managed knowledge sources, source inspection, confidence/
  uncertainty handling, human handoff, and failure fallback.
- Zendesk documents trusted knowledge, authenticated/escalation workflows,
  explicit conversation outcomes, live channels, and performance monitoring.
- WCAG 2.2 provides the pointer-target baseline used in the narrow accessibility
  criterion.

The exact URLs, date, weights, evidence paths, statuses and gaps live in
[`evaluation/market_quality_criteria.json`](../evaluation/market_quality_criteria.json).
Vendor feature documentation is used only to define a current category baseline;
vendor performance or automation claims are not treated as independent proof.

## Current critical gaps

| Critical gate | Status | Why it blocks market readiness |
|---|---|---|
| Trusted-source grounding | PARTIAL | Citations and allowlists execute, but knowledge content/audience permissions are recorded fixtures. |
| Reasoning, source review, and feedback | PARTIAL | Reason/citations/review exist; reviewer identity, append-only feedback, source rating, and knowledge correction do not. |
| Authentication, roles, and tenant isolation | FAIL | There is no authenticated or role-scoped untrusted-network surface. |
| Live channel/platform/provider contracts | FAIL | There is no live support, commerce, carrier, model, retrieval, or authorized-action adapter. |
| Outcome analytics and quality monitoring | PARTIAL | Local counts and authored routes are not real conversation outcomes, trends, satisfaction, or calibrated quality. |
| Audit, governance, and privacy | PARTIAL | Synthetic data is safe, but production identity, retention, deletion, encryption, consent, and immutable audit are absent. |
| Operability, observability, and recovery | PARTIAL | Disposable CI passes; production logs, alerts, SLOs, backup/restore, rollback, and incident operation are absent. |
| Buyer, user, and market validation | FAIL | No representative operator run, buyer proof, live outcome, funded work, or collected cash exists. |

## Run the harness

Reproduce the complete technical and market baseline:

```bash
uv run --python 3.13 python scripts/quality_harness.py --allow-not-ready
```

Expected current summary:

```text
technical_gate=PASS checks=11/11
market_quality_verdict=NOT_MARKET_READY score=53/85 critical_failures=8
overall_verdict=NOT_MARKET_READY
```

Run the real release gate without an exception flag:

```bash
uv run --python 3.13 python scripts/quality_harness.py
```

It currently exits non-zero by design. `--allow-not-ready` means only “the
declared failing baseline was reproduced”; it never means market readiness.

The technical gate includes clean locked installs, original/unit/API tests,
fixture reproduction, async and SQL evidence verification, strict frontend
types/component/build, production dependency audit, browser-to-API-to-database
E2E, and whitespace checks. The committed result is
[`evaluation/quality_harness_results.json`](../evaluation/quality_harness_results.json).

## Path to a legitimate pass

Do not turn every missing feature into speculative scope. First validate the
operator and buyer workflow. A credible sequence is:

1. test the narrow workflow with representative support operators and record
   tasks, failures, decisions, and rejected assumptions;
2. define lawful data, identity, role, privacy, retention, and channel boundaries
   for one real pilot;
3. add one read-only knowledge/platform contract and immutable reviewer audit,
   then rerun representative cases before any external action capability;
4. add outcome definitions, source/answer feedback, monitoring, backup/restore,
   rollback, and incident ownership; and
5. refresh the market registry and pass every critical gate with observed
   evidence.

Real customer sending, order mutation, account access, paid infrastructure, and
production deployment require separate explicit authorization. A technical
green build, attractive UI, draft PR, buyer reply, or funded milestone is not a
market-quality pass by itself.
