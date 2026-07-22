# External market-evidence records

This directory is intentionally empty of passing observations. A technical test,
author-written note, attractive render, or edited status field is not independent
market evidence.

Each `external_observation` control in
`../market_quality_criteria.json` names its own JSON record. A record is eligible
only when it contains:

```json
{
  "schema_version": "1.0",
  "criterion_id": "buyer_user_and_market_validation",
  "control_id": "representative_operator_pilot",
  "observed_at": "YYYY-MM-DD",
  "observer_relationship": "representative_operator",
  "observer_role": "support_operator",
  "observer_reference": "privacy-safe-reference",
  "consent_recorded": true,
  "sample_size": 3,
  "sample_references": ["case-001", "case-002", "case-003"],
  "system_under_test_sha256": "digest emitted by the current harness",
  "acceptance_checks": [
    {"id": "criterion-specific-required-check", "result": "pass"}
  ],
  "privacy_review": {
    "status": "pass",
    "reviewer_relationship": "independent_reviewer",
    "reviewer_reference": "privacy-review-01",
    "sanitized_for_public_repository": true,
    "raw_evidence_stored_outside_repository": true
  ],
  "artifacts": [
    {
      "path": "evaluation/market_evidence/artifacts/aggregate.json",
      "sha256": "...",
      "sample_references": ["case-001", "case-002", "case-003"]
    }
  ]
}
```

Allowed observer relationships are `buyer`, `representative_operator`,
`independent_reviewer`, `security_reviewer`, and `operations_owner`. `author` is
rejected. Records and artifacts must stay inside the repository, meet the
control's minimum sample, contain only passing acceptance checks, remain within
the declared age limit, cover every criterion-specific required acceptance ID,
bind every privacy-safe sample reference to an artifact, match the current
system-under-test digest, and match every artifact SHA-256 digest.

The release harness fingerprints the production evidence contract, including
scope, sources, control kinds, check IDs, record paths, required acceptance IDs,
sample floors, weights, critical flags, and threshold. Drift fails against the
verifier at this commit before scoring. Because verifier and policy share a
repository, protected external review—not this fingerprint—is the control
against an owner deliberately editing both.

Do not place customer messages, names, emails, phone numbers, order details,
credentials, raw screenshots, or other personal/private data here. Raw evidence
stays outside this public repository. Only approved UTF-8 JSON/CSV/Markdown/text
receipts or aggregates up to 1 MB may be committed. The evaluator runs bounded
email/phone/high-confidence-secret checks, but that is not a complete privacy or
data-loss-prevention system.

The evaluator validates structure, freshness, required checks, sample/artifact
binding, source-tree binding, privacy-review metadata, and integrity. It cannot
authenticate whether a claimed observer, reviewer, or observation is real.
Repository-local automation therefore never emits `MARKET_READY`: even
structurally complete records remain pending independent human provenance review
and an externally governed release decision.
