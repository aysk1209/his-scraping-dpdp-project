# DPDP Act 2023 — principle → rule index

The build-step-2 compliance framework turns each DPDP Act 2023 principle below
into a code-checkable rule in
[`src/compliance/rules/`](../../src/compliance/rules/), with a stable rule ID and
an evaluation that yields a status + 0–1 score against an extraction run
(`compliance.models.ExtractionRun` + sampled `ExtractedRecord`s).

Rules cite the DPDP Act 2023 **principle** by name (in `provision` and in a code
comment at the point of the check). Exact section numbers are a report-time
reference task — deliberately not pinned in code, so the rules stay readable and
don't rot against a mis-transcribed clause.

## Rules

| Rule ID | DPDP principle | Check mechanism | Status |
|---------|----------------|-----------------|--------|
| `DM-01` | Data minimisation — data limited to what is necessary for the purpose | Extracted field categories ⊆ purpose-allowed set; score = 1 − excess/total | **implemented** (slice 1) |
| `LB-01` | Lawful basis — processing rests on consent or a recognised legitimate use | Basis declared, recognised, and carries a reference | **implemented** (slice 1) |
| `SL-01` | Storage limitation — retain only as long as the purpose requires, then erase | `retention_days` present and ≤ policy max; deletion mechanism declared | **implemented** (slice 1) |
| `SS-01` | Security safeguards — reasonable safeguards against personal data breach | Fraction of required safeguards (TLS, at-rest encryption, access control, pseudonymisation) satisfied | **implemented** (slice 1) |
| `PL-01` | Purpose limitation — processing confined to the declared purpose | planned | pending |
| `NT-01` | Transparency / notice — notice to the Data Principal | planned | pending |
| `AC-01` | Accountability — Data Fiduciary obligations; audit trail | planned | pending |

## Policy

The "what is necessary for the purpose" and retention limits live as a
declarative table in [`src/compliance/policy.py`](../../src/compliance/policy.py)
(`PURPOSE_POLICY`), keyed by processing purpose. Slice 1 models a single
purpose, `care_coordination`. Tuning the compliance envelope is a policy edit,
not a rule-code change.

## Output artifact

`compliance.checkers.run_all(run, records)` returns a `ComplianceReport`
(`compliance.report`) with an overall `compliance_score`, a `pass_rate`, and a
per-rule breakdown. It renders as a console table, JSON (`to_json_file`), or
Markdown (`to_markdown_file`); file artifacts land in
`docs/benchmark_results/<run_id>.{json,md}` (gitignored).

This artifact — not prose — is the comparison point against baseline techniques
(e.g. AutoScraper, EMNLP 2024): the same rules score any technique's run.

## Demos

```
python scripts/score_extraction_run.py       # hand-built records, rules in isolation
python scripts/run_synthetic_extraction.py    # records from the synthetic generator
```

Each scores three runs — compliant, partial, careless. Current spread
(synthetic demo): **1.00 / ~0.63 / ~0.23**.
