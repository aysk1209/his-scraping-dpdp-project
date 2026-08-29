# Compliance approach — reviewer walkthrough

A one-page account of how the project treats DPDP Act 2023 compliance as a
measurable property of an extraction technique. Companion to
[`dpdp-provision-map.md`](dpdp-provision-map.md).

## The claim

Existing HIS scraping work is evaluated on speed, robustness, and coverage.
This project adds a fourth axis — **data-protection compliance** — and makes it
a number, produced by the same harness for any technique, so techniques can be
compared on it.

## How a run is represented

A compliance rule cannot inspect "a scrape" in the abstract, so an extraction is
expressed as data ([`compliance/models.py`](../../src/compliance/models.py)):

- **`ExtractionRun`** — the manifest a technique declares: processing `purpose`,
  `lawful_basis` (+ reference), `retention_days`, `deletion_mechanism`, and a
  `SecurityPosture` (TLS, at-rest encryption, access control, pseudonymisation).
- **`ExtractedRecord`** — a sample of what came out, tagged only by
  `FieldCategory` (`direct_identifier`, `quasi_identifier`, `clinical`,
  `financial`, `administrative`, `contact`). No values, so benchmark inputs
  carry no personal data.

## The policy

[`compliance/policy.py`](../../src/compliance/policy.py) holds `PURPOSE_POLICY`:
per processing purpose, the field categories that are *necessary for that
purpose*, the maximum retention, and whether identifiers must be pseudonymised.
This is the auditable "what is allowed" — tuning the compliance envelope is a
policy edit, not a rule-code change. One purpose is modelled so far:
`care_coordination`.

## The rules

Four rules ([`compliance/rules/`](../../src/compliance/rules/)), each a distinct
check mechanism, each citing a DPDP Act 2023 **principle** (exact section
citations are left for the report's references, not pinned in code):

| Rule | DPDP principle | Mechanism |
|------|----------------|-----------|
| `DM-01` | data minimisation | extracted categories ⊆ policy-allowed; score = 1 − excess/total |
| `LB-01` | lawful basis for processing | basis declared, recognised, carries a reference |
| `SL-01` | storage limitation | `retention_days` present and ≤ policy max; deletion mechanism declared |
| `SS-01` | security safeguards | fraction of required safeguards satisfied |

Each returns a status (`pass` / `fail` / `not_applicable`), a 0–1 score, and
plain-language findings.

## The output

`compliance.checkers.run_all(run, records)` →
[`ComplianceReport`](../../src/compliance/report.py): an overall
`compliance_score` (mean of applicable rule scores), a `pass_rate`, and the
per-rule breakdown. It renders three ways — console table (`render_table`),
JSON (`to_json_file`), and Markdown (`to_markdown_file`, for pasting into slides
or the report). Artifacts land in `docs/benchmark_results/<run_id>.{json,md}`.
This artifact is the comparison unit — the same rules will score a baseline
technique (e.g. AutoScraper, EMNLP 2024).

## End to end, on synthetic data

Live HIS access is not usable, so the pipeline runs against self-generated data:

```
data_synthetic.catalogue        field inventory: name -> HIS layer -> DPDP category
data_synthetic.generators       Faker-seeded plain-dict records per catalogue field
extraction.adapters.MockHISDataSource
                                fetch(layer, fields=[...]) -> records projected to
                                the requested fields  (stand-in for Tier 2 scraping)
compliance.checkers.run_all     score the run -> ComplianceReport
```

Two demos, each scoring three runs — compliant, partial, careless:

- `python scripts/score_extraction_run.py` — hand-built records, isolates the rules.
- `python scripts/run_synthetic_extraction.py` — records come from the generator
  via the adapter; a compliant field selection, a tight selection with a sloppy
  manifest, and a "request everything, declare nothing" selection.

Current spread (synthetic demo): compliant **1.00**, partial **~0.63**,
careless **~0.23**. The spread is the thesis, demonstrated.

## Assumptions in play (accepted as the working set)

- The five-layer HIS model ([`interop/layers.py`](../../src/interop/layers.py)) —
  a working reconstruction; the team has accepted it for now and will reconfigure
  if real HIS access shows a different structure.
- The `care_coordination` purpose and its allowed-category set.
- Staff names categorised as `administrative`, not `direct_identifier`.
- Rules cite DPDP principles by name; exact section numbers are a report-time
  reference task, deliberately not pinned in code.
