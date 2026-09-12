# Benchmark results

Scored artifacts produced by the demo scripts. Regenerate any of them by
re-running the matching script from the repo root.

| File | Produced by | Contents |
|------|-------------|----------|
| `benchmark.{json,md}` | `python scripts/run_benchmark.py` | Extraction techniques ranked by DPDP compliance score, with a per-rule breakdown. **The headline result.** |
| `synthetic-*.{json,md}` | `python scripts/run_synthetic_extraction.py` | One technique in three configurations (compliant / partial / careless) over generated data |
| `care-coordination-*.{json,md}` | `python scripts/score_extraction_run.py` | The rules scored against hand-built runs, no generator involved |
| `*--purpose-matrix.{json,md}` | `python scripts/compare_purposes.py` | One unchanged extraction scored against every purpose in the policy. **The purpose-limitation result.** |

Tracked in git as browsable references: `benchmark.md`, the two
`*--purpose-matrix.md` files that show the care/billing comparison in both
directions, and this README. Every other file here is git-ignored and regenerated
on each run.

The `.md` files are formatted for pasting into slides or the report. The `.json`
files are for downstream analysis and for the eventual comparison against real
baseline implementations.
