# Market-readiness evidence gate

## Current verdict

**`NOT_MARKET_READY` — internal readiness rubric 42.5/100, release threshold
85, with eight failed or partial critical gates.**

The local technical harness passes 11/11 checks. That proves the declared local
software path executes; it does not override the market verdict. The number is
an internal evidence rubric, not an independently calibrated market score. Its
categories come from current official product documentation; its weights and
threshold are authored release policy. No number can compensate for a critical
failure.

Repository-local automation is intentionally unable to emit `MARKET_READY`.
Even if the rubric reaches 85 and every critical control is structurally
complete, the machine state is only
`STRUCTURALLY_COMPLETE_PENDING_INDEPENDENT_PROVENANCE_REVIEW`. A final market
pass requires a real independent reviewer to authenticate the people,
observations and underlying raw evidence through an externally governed review
path that is not present in this repository.

The current default command therefore exits non-zero by design.

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

The exact URLs, review receipt, date, weights, evidence paths, controls and gaps live in
[`evaluation/market_quality_criteria.json`](../evaluation/market_quality_criteria.json).
Vendor feature documentation is used only to define a current category baseline;
vendor performance or automation claims are not treated as independent proof.
The locked author-research receipt records 18 official URLs: 17 returned HTTP
200 to a bounded live retrieval on 2026-07-22, while the W3C page blocked curl
but opened successfully in the browser. This proves a dated research action,
not buyer validation or objective calibration of the weights.

The authored `status` field is retained only as a comparison note and never
determines the effective result. Technical controls consume checks observed in
the current local-harness process. Feature criteria also contain implementation
test IDs that are currently absent; an external note cannot substitute for code
that is not in this product tree. External controls require a dated record from
a buyer, representative operator, operations owner, security reviewer, or
independent reviewer. The evaluator checks strict record fields, consent,
role/reference, criterion-specific acceptance IDs, minimum sample, privacy-safe
sample-to-artifact binding, a digest of the exact system under test, UTF-8
aggregate artifacts, bounded PII/secret patterns, and SHA-256 integrity. Raw
customer evidence must remain outside the public repository.
The privacy-safe record contract is documented in
[`evaluation/market_evidence/README.md`](../evaluation/market_evidence/README.md).

The production registry is fingerprint-checked before scoring. The digest covers
the benchmark scope, dated research receipt, exact sources/expectations/evidence,
threshold, source-age limit, weights/critical flags, implementation checks,
external-record paths, required acceptance IDs, sample floors and observation
age. Drift raises `market policy contract mismatch` before a result exists.

This is a review aid, not cryptographic governance: the policy and verifier live
in the same repository, so an owner could deliberately edit both. A legitimate
revision needs a new reviewed policy version/fingerprint, and a true release
needs protected external approval. The local fingerprint alone never creates a
market pass.

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

Reproduce the local technical and evidence-rubric baseline:

```bash
uv run --python 3.13 python scripts/quality_harness.py --allow-not-ready
```

Expected current summary:

```text
technical_gate=PASS checks=11/11
market_quality_verdict=NOT_MARKET_READY readiness_rubric_score=42.5/100 threshold=85 critical_failures=8
overall_verdict=NOT_MARKET_READY
```

Run the fail-closed local release-candidate gate without an exception flag:

```bash
uv run --python 3.13 python scripts/quality_harness.py
```

It currently exits 3 by design. `--allow-not-ready` means only “the
evidence-derived failing baseline was reproduced”; it never means market
readiness.

The technical gate includes clean locked installs, original/unit/API tests,
fixture reproduction, async and SQL evidence verification, strict frontend
types/component/build, production dependency audit, browser-to-API-to-database
E2E on fresh harness-owned servers, and committed-tree/current-diff whitespace
checks. The committed result is
[`evaluation/quality_harness_results.json`](../evaluation/quality_harness_results.json).
This command is local and does not run Docker/PostgreSQL. The GitHub aggregate is
the broader release-candidate gate: four technical jobs, including the disposable
PostgreSQL smoke, must pass before the intentionally blocked market-release job
runs. That job cannot turn green from repository-local evidence alone; it also
requires a protected external provenance approval/release path that is not yet
implemented. The standalone `market_quality.py` accepts only the locked production
policy plus an exact 11-check harness receipt; it reproduces a report and can
never issue a final market pass.

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
5. refresh and independently review the market registry, pass every
   implementation and observation control, then authenticate provenance through
   a protected external approval path.

Real customer sending, order mutation, account access, paid infrastructure, and
production deployment require separate explicit authorization. A technical
green build, attractive UI, draft PR, buyer reply, or funded milestone is not a
market-quality pass by itself.
