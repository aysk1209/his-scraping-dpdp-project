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

## Comparing techniques — the core evidence

A **technique** ([`extraction/technique.py`](../../src/extraction/technique.py))
is a strategy that fulfils an `ExtractionTask` *and* produces its own compliance
manifest — so "compliance-aware" is a property of the technique's design, not a
label added afterwards. Three are implemented
([`extraction/techniques/`](../../src/extraction/techniques/)):

| Technique | Behaviour |
|-----------|-----------|
| compliance-aware (ours) | pulls exactly the task's needed fields; full manifest |
| minimising, undocumented | pulls only needed fields, but no paperwork / partial safeguards |
| unconstrained (baseline) | ignores the task, grabs every field of every layer; no manifest. Stands in for a coverage-optimised scraper (cf. AutoScraper, EMNLP 2024) |

[`compliance.benchmark.run_benchmark`](../../src/compliance/benchmark.py) runs
every technique against every task, scores each run with the **same** rule set,
and aggregates. `python scripts/run_benchmark.py`:

| Technique | Compliance score | Pass rate | DM-01 | LB-01 | SL-01 | SS-01 |
|-----------|-----------------|-----------|-------|-------|-------|-------|
| compliance-aware (ours) | 1.000 | 100% | 1.00 | 1.00 | 1.00 | 1.00 |
| minimising, undocumented | 0.625 | 25% | 1.00 | 0.50 | 0.50 | 0.50 |
| unconstrained (baseline) | 0.229 | 0% | 0.67 | 0.00 | 0.00 | 0.25 |

This table is the paper's central claim made concrete: compliance discriminates
between *techniques*, and it is produced by one harness that will later score
real baseline implementations on equal terms.

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

Three demos:

- `python scripts/run_benchmark.py` — **the headline**: three techniques
  compared, the table above.
- `python scripts/run_synthetic_extraction.py` — one technique, three
  configurations (compliant / partial / careless), records from the generator.
- `python scripts/score_extraction_run.py` — hand-built records, isolates the
  rules with no generator or adapter in the way.

## Assumptions in play (accepted as the working set)

- The five-layer HIS model ([`interop/layers.py`](../../src/interop/layers.py)) —
  a working reconstruction; the team has accepted it for now and will reconfigure
  if real HIS access shows a different structure.
- The `care_coordination` purpose and its allowed-category set.
- Staff names categorised as `administrative`, not `direct_identifier`.
- Rules cite DPDP principles by name; exact section numbers are a report-time
  reference task, deliberately not pinned in code.
