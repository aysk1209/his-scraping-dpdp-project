# Benchmark protocol

What a reader needs to reproduce every number in the report, and what they
would need to change to get a different one. Everything here is fixed in the
repository; nothing depends on the machine except wall-clock time, which is
reported and never relied on.

## Workload

| Item | Value | Where |
|---|---|---|
| Tasks (in memory) | 8: `patient-summary`, `ward-census`, `medication-review`, `appointment-reminder`; traps `claim-reconciliation`, `desk-registration`, `ward-summary-registry`, `consultant-file` | `scripts/run_benchmark.py` |
| Single-patient tasks | 6 of 8 (`single_subject=True`); the patient is the source's first registration record, bound at run time | `compliance.benchmark.bind_subject` |
| Tasks (portal) | 4: `patient-summary`*, `ward-census`, `appointment-reminder`, `claim-reconciliation`* (* single-patient) | `scripts/run_pipeline.py` |
| Purposes | 3, pairwise non-nested: care coordination (90 d), billing settlement (365 d), patient registration (180 d) | `src/compliance/policy.py` |
| Rules | 7, each weight 1.0; DM-01 scores the field axis and, for single-patient tasks, the record axis | `src/compliance/rules/` |
| Capability register | `DEFAULT_REGISTER`: TLS, ENC-REST, ACL-STORE, PSEUDO-EXPORT, PURGE-01, NOTICE-REG-2026, DPO, AUDIT-LOG, ROPA, LU-CARE/LU-BILL/LU-REG; TLS, PSEUDO-EXPORT, PURGE-01 and AUDIT-LOG carry evidence the pipeline produces | `src/compliance/capabilities.py` |

## Sources

| Source | Parameters | Notes |
|---|---|---|
| In memory | 50 records per layer, seed 42 | `MockHISDataSource`; record *i* of every layer is patient *i* |
| Portal | 20 records per module, 10 per page, 0 ms latency, seed 42, served over TLS (ad-hoc certificate, trusted on loopback only) | `tools/mock_portal`; browser Chromium via Playwright, headless |
| Public export | the Synthea sample: 18 CSV files, 108 synthetic patients; column map `docs/access/synthea-column-map.json`; the portal's four tasks | fetched by `scripts/fetch_public_dataset.py` into `data/public_synthea/` with a provenance note and no synthetic manifest, so the handling gate treats it as real; result `benchmark-public.{json,md}` |
| Dataset (any other) | a directory of CSV/Excel with `PROVENANCE.md`, under `data/`, git-ignored | `DatasetHISDataSource`; the handling gate refuses anything else. A hospital export is not assumed |

## Repeats and scoring

- Every task is run up to **5 times** per technique in memory (1 on the portal
  and the public export); an AI model is repeated at most as often as it has
  recorded samples — 5 for Gemini, 2 told the policy and 1 unaided for the
  Claude models. **Every run is scored.** A technique's score is the mean over
  all its runs; the per-task table carries the range where runs differed.
- *Stable*: repeats after the first that reproduced the first run's decision
  (fields pulled and manifest structure), over tasks × (runs − 1): 32 for a
  technique run five times, 8 for one run twice, none for one run once.
- *Traps held*: trap runs (4 tasks × runs) on which no out-of-scope category
  was pulled, no onward use declared, and retention stayed within the ceiling;
  a task is *held* only when every repeat held.
- *Coverage*, *excess ratio*, *record excess*: micro-averaged over every run;
  counts shown per pass of the technique's *own* runs (fixed 2026-09-23: counts
  had been divided by the benchmark's repeats rather than the technique's).
- *Coverage ceiling*: counted from the source once per task, outside the
  meter, never read off a technique (`benchmark.reachable_fields`). It counts
  the needed fields the source carries and, on a single-patient task, only
  those that patient's own records carry. A technique that finds a field in
  other patients' records can show coverage above the ceiling; that is records
  read, not a higher ceiling. On the synthetic and portal workloads every
  needed field is reachable (35/35 and 18/18), so the ceiling is 1.0.
- *Veracity*: substantiated ÷ declared controls over every run; substantiated
  claims split into *demonstrated* (evidence the pipeline produced) and
  *attested* (the register's word). Transport is observed from the connection.
- Wall-clock: the median over repeats per task, summed; hardware-dependent.

## The AI agents

| Item | Value |
|---|---|
| Providers / models | Gemini, `gemini-3.1-flash-lite` (free API tier; the reference model). Claude, `claude-haiku-4-5` and `claude-sonnet-5`, through the Claude Code command line on a subscription sign-in (`--provider claude-code`; no API key): headless `claude -p` from an empty directory, our brief as the whole system prompt, no tools, no MCP servers, no skills, effort pinned to `high`, `ANTHROPIC_API_KEY` stripped. A free-tier Gemini flagship was attempted on 2026-09-22 and dropped (one or two calls a day in practice); its partial recordings were deleted |
| Briefings | `unaided`; `informed` (the Act's seven obligations in plain words); `policy` (the purpose envelope and every field's category, in the prompt). The reference model is recorded on all three; a further model, if one is recorded, on `policy` and `unaided`. Tables are read per model at `policy`; the full grid is kept |
| What the model sees | the job in words, the purpose, whether the job is about one patient, the field *names* of the **canonical catalogue** (not of any particular source), the capability register. Never a value, never a record number, never the task's own needed list. A recording is therefore a property of the model and replays against every source; only a catalogue, register or wording change stales it |
| What it returns | a flat JSON decision: fields, `scope` (`subject` / `all`), and the manifest |
| Sampling | provider default — no temperature or seed set; the recording says so |
| Recording | `scripts/record_ai_agents.py`: 5 samples per task per briefing for the reference model; the minimum for a further model — 2 per task at `policy` (one to enter the tables, one to measure repeatability) and 1 at `unaided`; each sample stores field names and manifest choices only, with a fingerprint (SHA-256 of the exact prompt) so a change to the brief marks the recording stale. Calls are paced to the model's per-minute allowance and budgeted per day; samples are taken breadth-first (one per task, then the next), so an interrupted recording leaves every task equally sampled. The benchmark repeats an agent at most as often as it has samples |
| Replay | `AI_AGENT_MODE=replay` is the default; every demo and test replays. Only the recorder makes live calls |

## Reproduce

```
pytest                                  # the suite
python scripts/run_benchmark.py         # benchmark.{json,md}; agents replay
python scripts/run_pipeline.py          # benchmark-portal.{json,md}, exports, audit log
python scripts/run_pipeline.py --dataset data/public_synthea --column-map data/public_synthea/column_map.json --artefact benchmark-public
python tools/weight_sweep.py            # weight-sweep.md
python tools/build_demo_page.py         # the demo page's data block
python tools/report_tables.py           # every table in the report and the README
```

CI (`.github/workflows/ci.yml`) runs the suite from a clean checkout, then
regenerates `benchmark.json` and diffs it against the committed file with
timestamps and wall-clock excluded, and checks every report table against the
artefacts (`tools/report_tables.py --check`). Any drift fails the build.

## What would change a number

- The **catalogue** (`data_synthetic/catalogue.py`): a field's category moves
  DM-01 and the purpose matrix; adding a field changes every agent brief and
  marks the recordings stale.
- The **policy** (`compliance/policy.py`): an allowed category or a ceiling
  moves DM-01, SL-01 and the traps' verdicts; a purpose that nests inside
  another is refused by a test.
- The **register**: a control removed makes our technique declare less, and
  makes an agent's citation of it unsubstantiated.
- The **brief** (`ai_agent.py`): any wording change stales the recordings;
  the demos say so and run without agents until re-recorded.
- The **seed** or record count: values change, categories do not; scores are
  invariant, counts and page loads are not.
