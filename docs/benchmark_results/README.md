# Benchmark results

Scored artifacts produced by the demo scripts. Regenerate any of them by
re-running the matching script from the repo root.

| File | Produced by | Contents |
|------|-------------|----------|
| `benchmark.{json,md}` | `python scripts/run_benchmark.py` | Extraction techniques ranked by DPDP compliance score, with a per-rule breakdown. **The headline result.** |
| `synthetic-*.{json,md}` | `python scripts/run_synthetic_extraction.py` | One technique in three configurations (compliant / partial / careless) over generated data |
| `care-coordination-*.{json,md}` | `python scripts/score_extraction_run.py` | The rules scored against hand-built runs, no generator involved |

Only `benchmark.md` and this README are tracked in git (a browsable reference of
the current result); every other file here is git-ignored and regenerated on each
run.

The `.md` files are formatted for pasting into slides or the report. The `.json`
files are for downstream analysis and for the eventual comparison against real
baseline implementations.
