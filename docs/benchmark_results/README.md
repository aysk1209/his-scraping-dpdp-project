# Benchmark results

Scored artifacts produced by the demo scripts. Regenerate any of them by
re-running the matching script from the repo root.

| File | Produced by | Contents |
|------|-------------|----------|
| `benchmark.{json,md}` | `python scripts/run_benchmark.py` | Extraction techniques ranked by DPDP compliance score, with a per-rule breakdown. **The headline result.** |
| `synthetic-*.{json,md}` | `python scripts/run_synthetic_extraction.py` | One technique in three configurations (compliant / partial / careless) over generated data |
| `care-coordination-*.{json,md}` | `python scripts/score_extraction_run.py` | The rules scored against hand-built runs, no generator involved |
| `*--purpose-matrix.{json,md}` | `python scripts/compare_purposes.py` | One unchanged extraction scored against every purpose in the policy. **The purpose-limitation result.** |
| `benchmark-portal.{json,md}` | `python scripts/run_pipeline.py` | The same techniques scraping the served portal through a real browser; cost includes real page loads; the transport is observed; every run is audit-logged. **The end-to-end result.** |
| `rules-vs-just-ai.html` | `python tools/build_demo_page.py` after either benchmark (page hand-built 2026-09-17; its data block is regenerated) | **The Review-II demo page**: tabs; a shared legend that overlays or hides techniques on every chart; a radar of the five axes; a tab on where "just AI" fails (traps, retention, coverage, stability); per-rule overlay; field matrix per task; the numbers. |
| `techniques-compared.html` | hand-built 2026-09-16, **superseded** by `rules-vs-just-ai.html`; kept for the pre-trap figure in the deck history | The one-page figure from the first recording (four plain tasks). Numbers predate the trap tasks and the every-repeat scoring; do not quote from it. |
| `weight-sweep.md` | `python tools/weight_sweep.py` | The ranking re-scored under twenty-one rule weightings; ties are marked as ties. |
| `benchmark.json`, `benchmark-portal.json` | the two benchmarks | The data the deck builder, the demo page and the weight sweep read. Tracked, and CI regenerates and diffs the in-memory one. |
| `*.retention.json` (git-ignored) | `python scripts/run_pipeline.py` | The retention sidecar beside each export: run, purpose, retention declared, the date after which `scripts/purge_exports.py` erases the files. |
| `navigation-map.{json,md}` | `python scripts/run_pipeline.py` | What the crawler discovered about the portal and which HIS layer it inferred for each module. The `.md` is the report table (paths only). |
| `patient-summary--compliance-aware.{hl7,fhir.json}` | `python scripts/run_pipeline.py` | The compliant run's export as shaped: HL7 v2 messages and a FHIR `collection` Bundle, direct identifiers pseudonymised. Only the pseudonymised export is written; the baseline's raw one is audited and discarded. |

`data/synthetic_export/` (git-ignored) is written by `python scripts/generate_dataset.py` and read by the dataset adapter.

Tracked in git as browsable references: `benchmark.md`, `benchmark-portal.md`,
`navigation-map.json`, `navigation-map.md`, the two `*--purpose-matrix.md` files that show the
care/billing comparison in both directions, and this README. Every other file here is git-ignored and regenerated
on each run.

The `.md` files are formatted for pasting into slides or the report. The `.json`
files are for downstream analysis and for the eventual comparison against real
baseline implementations.
