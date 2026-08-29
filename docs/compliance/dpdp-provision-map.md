# DPDP Act 2023 — provision → rule index

The build-step-2 compliance framework turns each criterion below into a
code-checkable rule in [`src/compliance/rules/`](../../src/compliance/rules/),
with a stable rule ID and an evaluation that yields a status + 0–1 score against
an extraction run (`compliance.models.ExtractionRun` + sampled
`ExtractedRecord`s).

Every compliance-relevant code path cites its provision in a comment, e.g.
`# DPDP Act 2023, s.8(5) — reasonable security safeguards`.

> **Section references are placeholders.** Each is marked `TODO: verify against
> Act text` in the code and must be confirmed against the DPDP Act 2023 and the
> Review-1 background report before the review.

## Rules

| Rule ID | Criterion | Provision (to confirm) | Check mechanism | Status |
|---------|-----------|------------------------|-----------------|--------|
| `DM-01` | Data minimisation | s.6(1) — data limited to what is necessary for the specified purpose | Extracted field categories ⊆ purpose-allowed set; score = 1 − excess/total | **implemented** (slice 1) |
| `LB-01` | Lawful basis | s.4 — lawful purpose with consent (s.6) or legitimate use (s.7) | Basis declared, recognised, and carries a reference | **implemented** (slice 1) |
| `SL-01` | Storage limitation | s.8(7) — erase once purpose served / consent withdrawn | `retention_days` present and ≤ policy max; deletion mechanism declared | **implemented** (slice 1) |
| `SS-01` | Security safeguards | s.8(5) — reasonable security safeguards against breach | Fraction of required safeguards (TLS, at-rest encryption, access control, pseudonymisation) satisfied | **implemented** (slice 1) |
| `PL-01` | Purpose limitation | s.5(2) / s.6 — processing confined to the purpose consented to | planned | pending |
| `NT-01` | Transparency / notice | s.5 — notice to the Data Principal | planned | pending |
| `AC-01` | Accountability | s.8(1)–(3) — Data Fiduciary obligations; audit trail | planned | pending |

## Policy

The "what is necessary for the purpose" and retention limits live as a
declarative table in [`src/compliance/policy.py`](../../src/compliance/policy.py)
(`PURPOSE_POLICY`), keyed by processing purpose. Slice 1 models a single
purpose, `care_coordination`. Tuning the compliance envelope is a policy edit,
not a rule-code change.

## Output artifact

`compliance.checkers.run_all(run, records)` returns a `ComplianceReport`
(`compliance.report`) with an overall `compliance_score`, a `pass_rate`, and a
per-rule breakdown. `ComplianceReport.to_json_file()` writes it to
`docs/benchmark_results/<run_id>.json` (gitignored).

This artifact — not prose — is the comparison point against baseline techniques
(e.g. AutoScraper, EMNLP 2024): the same rules score any technique's run.

## Demo

```
python scripts/score_extraction_run.py
```

Scores a compliant run against a "grab everything, declare nothing" run and
prints both reports. Current contrast: **1.000** vs **0.188**.
