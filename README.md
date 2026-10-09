# AI-Driven HIS Management Agent with DPDP-Compliant Web Scraping

A final-year research project (VIT, SENSE) that treats **compliance with India's
Digital Personal Data Protection Act, 2023 as a measurable, benchmarkable property
of a data-extraction technique** — not a legal checkbox applied afterwards.

Seven principles of the Act are written as executable rules. Every extraction
technique declares a manifest of what it pulled and why; the same rules score
every technique on equal terms, beside a cost profile measured in units that
reproduce on any machine. The comparison is our purpose-bound technique against
**publicly available AI agents given the same job**, and against a
coverage-optimised baseline.

Three layers:

1. **Extraction** — credentialed, browser-driven scraping of a login-gated HIS
   portal (Playwright), with each module's HIS layer inferred from the field names
   found on its pages, never from the URL.
2. **Compliance** — the research contribution: seven DPDP rules, a declarative
   purpose policy, a scored report, a two-axis benchmark, pseudonymisation on
   export verified by audit.
3. **Staff assistant** — a small rule-based assistant (no model) that explains HIS
   tasks to reception, nursing and administration, gated by the same policy
   table: a request outside a role's lawful purpose is declined with the rule cited.

## Status

**99% by the completion ledger** (`PLAN.md` §5). The pipeline runs end to end in
one command; all eight report chapters, the appendices and a first manuscript
draft are written on the real numbers. What remains is fitting the manuscript to
a venue's template and page budget, once the venue is chosen. Review-II is
30 Sep 2026, Review-III 28 Oct 2026.

**No hospital data, by design of the plan.** A hospital's export is its
patients' personal data and may never be released to a student project; nothing
here assumes it. Everything runs on synthetic data of a realistic five-layer
structure, on a login-gated portal fixture that a real browser scrapes, and on a
**public export we did not generate** (Synthea's sample: 18 files, 108 synthetic
patients), which passed through the real handling gate and found five defects
our own data could not have. If a hospital export is ever released, it is one
column map and the same command (`docs/access/when-access-lands.md`).

## The result

`python scripts/run_benchmark.py` — eight tasks (four worded to invite a
violation, six about one patient), in memory, every repeat scored; every
technique is told what the deployment provides. One row per technique, each AI
model **handed the purpose policy itself** (the fairest briefing: it knows
everything ours knows); every briefing is in
[`benchmark.md`](docs/benchmark_results/benchmark.md):

<!-- table:agents -->
| Technique | Runs per task | Compliance | Trap runs held | Coverage | Excess | Record excess | Stable |
|---|---|---|---|---|---|---|---|
| compliance-aware (ours) | 5 | **1.000** | **20 / 20** | 1.00 | 1.00 | 1.00 | **32 / 32** |
| claude-sonnet-5-5, told the policy | 5 | 1.000 | 20 / 20 (0.84–1.00) | 0.71 | 1.04 | 0.64 | 18 / 32 (0.39–0.72) |
| claude-opus-5-5, told the policy | 5 | 0.997 | 20 / 20 (0.84–1.00) | 0.76 | 1.42 | 0.73 | 17 / 32 (0.36–0.69) |
| claude-haiku-4-5, told the policy | 5 | 0.995 | 20 / 20 (0.84–1.00) | 0.78 | 1.61 | 0.91 | 5 / 32 (0.07–0.32) |
| gemini-3.1-flash-lite, told the policy | 5 | 0.984 | 10 / 20 (0.30–0.70) | 0.74 | 1.43 | 0.98 | 21 / 32 (0.48–0.80) |
| unconstrained (baseline) | 5 | 0.100 | 0 / 20 | 1.00 | 7.77 | 136.4 | 32 / 32 |

Brackets: 95% Wilson interval on the share of runs, for the models only -- ours and the baseline do not sample. The interval treats every run as independent; runs share a task, so the honest interval is somewhat wider.
<!-- /table:agents -->

Four public models — `gemini-3.1-flash-lite` (free API tier) and
`claude-haiku-4-5`, `claude-sonnet-5-5` and `claude-opus-5-5` (through a
subscription's command line, no API credit), each recorded five times per task
under three briefings — match the rule-driven technique on the *manifest they
declare*. They differ on everything the score cannot see:

- **Traps.** Unaided or told the Act, no model held more than 11 of 20 trap
  runs, and two held none. Handed the purpose policy itself, the three Claude
  models hold every trap — they comply when given the table ours applies — while
  Gemini still takes the diagnosis to reconcile an invoice, in every run.
- **The job.** Told the policy, they take 1.04–1.61× the fields the tasks need and
  still obtain only 71–78% of what the tasks need. One scores a perfect 1.000
  while doing 71% of the job.
- **Repeatability.** Given the same brief again, they reproduced their first
  decision in 5–21 of 32 repeats; ours in 32 of 32.

Ours reads the purpose policy, not the prose, so it holds every trap and repeats
itself, by construction. On the portal it reads one patient through the search
box — **32 page loads to the baseline's 440** — and its export carries no raw
identifier where the baseline's carries all 60. Five of the controls a manifest
can cite are **demonstrated, not declared**: the observed connection, an audit
log written by the harness, the export audit, a retention sidecar that the purge
erases and logs, and a record of processing generated from the log.

**The demo portal** (offline, one file, built from real runs, no raw identifier on any tab): [`docs/review/portal.html`](docs/review/portal.html) — six tabs: the portal run with its crawl replayed, rules vs AI, one entry's journey, patient rights (an access request and a breach), the staff assistant, and the HIS update. `python tools/build_review_pages.py` rebuilds it.

## Run it

```bash
python -m venv .venv && .venv\Scripts\activate      # POSIX: source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium                # once per machine
pytest                                               # the suite, ~1 min
python scripts/run_pipeline.py                       # the whole chain, ~2 min
```

`run_pipeline.py` serves a login-gated portal over TLS, logs a headless browser
into it, discovers its modules, runs every technique with real page loads as cost
(every run audit-logged by the harness; the connection observed, not assumed),
shapes the compliant run into HL7 v2 / FHIR with identifiers pseudonymised and
audited, schedules the export for erasure, re-judges one pull under every
purpose, puts one question per role to the assistant, and finally runs the purge
as of the day the retention ends. No network, no key: the AI models replay their
recorded decisions (`AI_AGENT_MODE=replay` is the default; only
`record_ai_agents.py` goes live).

The public export: `python scripts/fetch_public_dataset.py`, then
`python scripts/run_pipeline.py --dataset data/public_synthea --column-map data/public_synthea/column_map.json`.
Every demo page: `python tools/build_review_pages.py`. Every table in the report:
`python tools/report_tables.py`. Other demos: `run_benchmark.py`,
`trace_journey.py` (one entry through every stage), `compare_purposes.py`, `show_role_access.py`,
`ask_agent.py`, `check_ui_update.py`, `answer_access_request.py`, `breach_drill.py`, `run_ablation.py`, `run_scale.py`, `run_injection.py`, `rehearse_day_one.py`. Plain-language guide:
[`DEMO_GUIDE.md`](DEMO_GUIDE.md).

**Recording the AI models yourself** (optional — recordings are committed):
with `GEMINI_API_KEY` / `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` set in your own
shell, `python scripts/record_ai_agents.py --list-models`, then
`python scripts/record_ai_agents.py --repeats 5`; with a Claude subscription and
no key, `--provider claude-code --model claude-opus-5-5` (or `claude-sonnet-5-5`, `claude-haiku-4-5`). The model is briefed
with field *names* and the job; no patient value ever leaves the machine, and the
recordings hold only field names and manifest choices.

## Repository layout

```
src/
  compliance/       seven DPDP rules, purpose policy, roles, report, benchmark, purpose matrix,
                    pseudonymisation, real-data handling gate, capability register + veracity,
                    audit log (harness-written), retention sidecar + purge
  extraction/       HISDataSource interface; adapters (in-memory, portal via Playwright, dataset);
                    techniques (compliance-aware, AI agents + recordings, baseline); metering; tier2 crawler
  data_synthetic/   field catalogue (field -> layer -> DPDP category), generator, schemas, export
  interop/          five-layer HIS model, layer <-> standard map, HL7 v2 / FHIR shapers, export audit
  agent/            rule-based staff assistant: registry, session (recognise -> gate -> collect), guidance,
                    ui (words steps from the crawl), drift (what a HIS update changed)
scripts/            run_pipeline, run_benchmark, trace_journey, record_ai_agents, purge_exports, check_source,
                    rehearse_day_one (the real-data procedure on a hospital-shaped export, with a leak audit), ...
tools/              mock_portal/ (the login-gated portal fixture, Flask, TLS); the demo pages, the deck and the
                    report tables, each built from the artefacts (build_review_pages, build_review_deck, report_tables)
tests/              the suite (pytest)
docs/
  compliance/       approach.md, dpdp-provision-map.md (section mapping, verified against the Gazette)
  report/           outline.md, chapters 1-8, appendices, manuscript
  review/           review-ii-flow.md (presenter script), the demo pages and their index
  access/           when-access-lands.md (day-one procedure for real data)
  methodology/      benchmark-protocol.md (every parameter behind the numbers; what would change one)
  benchmark_results/ tracked results, the navigation map, the demo page
.github/workflows/  ci: the suite; the benchmark regenerated and diffed; the report's tables checked
```

## Documents

- [`CLAUDE.md`](CLAUDE.md) — operating rules, build order, conventions
- [`PLAN.md`](PLAN.md) — definition of done, completion ledger, workstreams, decisions
- [`PROJECT_CONTEXT.md`](PROJECT_CONTEXT.md) — research framing and background
- [`docs/compliance/approach.md`](docs/compliance/approach.md) — the method in one page

## Team

Avanindra (23BLC1089) · Ananya (23BLC1017) · Guide: Dr. Manoj Kumar
