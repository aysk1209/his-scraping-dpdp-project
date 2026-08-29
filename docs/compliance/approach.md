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
check mechanism, each citing a DPDP provision (all `TODO: verify` against the
Act text):

| Rule | Provision | Mechanism |
|------|-----------|-----------|
| `DM-01` data minimisation | s.6(1) | extracted categories ⊆ policy-allowed; score = 1 − excess/total |
| `LB-01` lawful basis | s.4 | basis declared, recognised, carries a reference |
| `SL-01` storage limitation | s.8(7) | `retention_days` present and ≤ policy max; deletion mechanism declared |
| `SS-01` security safeguards | s.8(5) | fraction of required safeguards satisfied |

Each returns a status (`pass` / `fail` / `not_applicable`), a 0–1 score, and
plain-language findings.

## The output

`compliance.checkers.run_all(run, records)` →
[`ComplianceReport`](../../src/compliance/report.py): an overall
`compliance_score` (mean of applicable rule scores), a `pass_rate`, and the
per-rule breakdown. `to_json_file()` writes it to
`docs/benchmark_results/<run_id>.json`. This artifact is the comparison unit —
the same rules will score a baseline technique (e.g. AutoScraper, EMNLP 2024).

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

Two demos:

- `python scripts/score_extraction_run.py` — hand-built records, isolates the rules.
- `python scripts/run_synthetic_extraction.py` — records come from the generator
  via the adapter; a compliant field selection vs. a "request everything, declare
  nothing" selection.

Current contrast: **~1.0** for the compliant run vs **~0.2** for the careless
one. The gap is the thesis, demonstrated.

## Assumptions still to confirm

- DPDP section numbers (every `provision` string).
- The five-layer HIS model ([`interop/layers.py`](../../src/interop/layers.py)) —
  working reconstruction, not from the source docs.
- The `care_coordination` purpose and its allowed-category set.
- Staff names categorised as `administrative`, not `direct_identifier`.
