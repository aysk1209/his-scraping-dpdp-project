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
| `DM-01` | Data minimisation — data limited to what is necessary for the purpose | Extracted field categories ⊆ purpose-allowed set; score = 1 − excess/total | **implemented** |
| `LB-01` | Lawful basis — processing rests on consent or a recognised legitimate use | Basis declared, recognised, and carries a reference | **implemented** |
| `SL-01` | Storage limitation — retain only as long as the purpose requires, then erase | `retention_days` present and ≤ policy max; deletion mechanism declared | **implemented** |
| `SS-01` | Security safeguards — reasonable safeguards against personal data breach | Fraction of required technical safeguards (TLS, at-rest encryption, access control, pseudonymisation) satisfied | **implemented** |
| `PL-01` | Purpose limitation — processing confined to the declared purpose | Purpose specified and recognised in policy; declared onward uses assessed for compatibility against the other recognised purposes' envelopes | **implemented** |
| `NT-01` | Transparency / notice — notice to the Data Principal | A privacy notice is recorded and covers the stated purpose | **implemented** |
| `AC-01` | Accountability — Data Fiduciary can demonstrate compliance | Fraction of governance controls (audit log, named accountable party, record of processing) in place | **implemented** |

All seven principles are now covered. The rule set is `compliance.rules.ALL_RULES`.

## Policy

The "what is necessary for the purpose" and retention limits live as a
declarative table in [`src/compliance/policy.py`](../../src/compliance/policy.py)
(`PURPOSE_POLICY`), keyed by processing purpose. Tuning the compliance envelope is
a policy edit, not a rule-code change.

Two purposes are modelled, `care_coordination` and `billing_settlement`, and
deliberately **neither one's scope contains the other's**: care coordination may
see clinical data but not financial or contact data; billing may see financial and
contact data but not clinical data, and may retain it for a year rather than 90
days against its audit obligation. Purposes are therefore not ranked from strict
to lax, and "out of scope" carries its proper meaning — *not necessary for this
purpose* rather than *more sensitive in general*. Three rules vary with the
purpose in consequence: `DM-01` (allowed categories), `SL-01` (retention ceiling)
and `SS-01` (whether pseudonymisation is a required safeguard — it is not, for
billing, since an invoice that cannot be attributed cannot be settled).

Claims adjudication is deliberately *not* modelled: real adjudication needs coded
diagnosis data, so folding it into `billing_settlement` would quietly re-admit the
clinical category and collapse the distinction above. It belongs as its own
purpose with its own envelope.

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
python scripts/run_benchmark.py               # headline: 3 techniques compared
python scripts/run_synthetic_extraction.py    # 1 technique, 3 configurations
python scripts/score_extraction_run.py        # hand-built records, rules in isolation
```

`run_benchmark.py` output (compliance-aware / minimising / baseline):
**1.000 / 0.500 / 0.131**.
