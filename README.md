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

**98% by the completion ledger** (`PLAN.md` §5). Everything that does not need
live hospital access is built; the pipeline runs end to end in one command; all
eight chapters of the report are drafted on real numbers. What remains is the
report's second pass and the manuscript. Review-II is 30 Sep 2026, Review-III
28 Oct 2026.

**No live HIS access yet.** Everything runs against synthetic data of a realistic
five-layer structure, served through a portal fixture that a real browser scrapes.
A hospital dataset is expected; the dataset adapter and a handling gate (provenance
and de-identification recorded before anything is read) are ready for it.

## The result

`python scripts/run_benchmark.py` — eight tasks (four of them worded to invite a
violation, six about one patient), in memory, five repeats; every technique is
told what the deployment provides:

One row per model, each AI agent **handed the purpose policy itself** (the
fairest briefing — it knows everything ours knows); the other briefings are in
the full grid in [`benchmark.md`](docs/benchmark_results/benchmark.md):

| Technique | Compliance | Trap runs held | Coverage | Excess ratio | Repeats that reproduced run 1 |
|---|---:|---:|---:|---:|---:|
| compliance-aware (ours) | **1.000** | **20 / 20** | 1.00 | 1.00× | **32 / 32** |
| AI agent — gemini-3.1-flash-lite, told the policy | 0.984 | 10 / 20 | 0.74 | 1.43× | 21 / 32 |
| unconstrained baseline | 0.100 | 0 / 20 | 1.00 | 7.77× | 32 / 32 |

Unaided, or told the Act in plain words, the same model scores 0.942 / 0.948
and holds **0 / 20** trap runs. Every one of the forty runs per technique is
scored; a score is a mean, not a draw. Recorded 2026-09-18. (The flagship of
the same family was tried and dropped: its free tier served one or two calls a
day; a further model is one recorder command away if a key with credit appears.)

A current public model matches the rule-driven technique on the *manifest it
declares* — told what the deployment provides, it cites it correctly, every run.
It differs on everything the score cannot see. Told to reconcile an invoice
"against the diagnosis", it takes the diagnosis, every run, even with the Act in
its prompt — **and even with the purpose policy itself in its prompt**, stating
that clinical data is not permitted for billing and that the diagnosis is
clinical. Handed the policy it obeys the numbers (every retention lands exactly
on the ceiling, the onward use disappears) and not the categories: a sentence in
the request outranks a table in the same prompt. It takes a name where the task
needs the record number (67–74% of the job), and reproduces its first decision
in 18–21 of 32 repeats. Ours reads the purpose policy, not the prose, so it
holds every trap and repeats itself, by construction. On the portal the baseline
loads 440 pages to our 32 for the same coverage; its 7× surplus is exactly the
overreach the minimisation rule penalises.

Minimisation has a record axis too. A task about one patient is bound to that
patient at run time and ours reads only their records — through the portal's
search box, one page per module: **32 page loads to the baseline's 440** on the
live run. DM-01 scores the record axis from the harness's own count, so a
technique that reads every patient's record to answer for one is halved on that
task whatever its fields.

Four of the controls a manifest can cite are **demonstrated, not declared**: the
adapter observes whether the connection was encrypted (the fixture serves TLS; a
manifest claiming TLS over plain http is marked unsubstantiated), the harness
writes every run to an audit log at the metering boundary, the export audit
searches the written files for raw identifiers, and every export carries a
retention sidecar that `scripts/purge_exports.py` erases on the day and logs.

Demo page: [`docs/benchmark_results/rules-vs-just-ai.html`](docs/benchmark_results/rules-vs-just-ai.html).
One-page figure: [`docs/benchmark_results/techniques-compared.html`](docs/benchmark_results/techniques-compared.html).
Full tables: [`benchmark.md`](docs/benchmark_results/benchmark.md),
[`benchmark-portal.md`](docs/benchmark_results/benchmark-portal.md).

## Run it

```bash
python -m venv .venv && .venv\Scripts\activate      # POSIX: source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium                # once per machine
pytest                                               # 274 tests, ~40 s
python scripts/run_pipeline.py                       # the whole chain, ~2 min
```

`run_pipeline.py` serves a login-gated portal over TLS, logs a headless browser
into it, discovers its modules, runs every technique with real page loads as cost
(every run audit-logged by the harness; the connection observed, not assumed),
shapes the compliant run into HL7 v2 / FHIR with identifiers pseudonymised and
audited, schedules the export for erasure, re-judges one pull under every
purpose, puts one question per role to the assistant, and finally runs the purge
as of the day the retention ends. No network, no key: the AI agents replay their
recorded decisions (`AI_AGENT_MODE=replay` is the default; only
`record_ai_agents.py` goes live).

Other demos: `run_benchmark.py` (headline table), `trace_one_patient.py` (one
record, every technique, field by field, and the agent's five answers to the same
brief), `compare_purposes.py` (purpose limitation as a result), `show_role_access.py`
(the role gate), `ask_agent.py` (the assistant). Plain-language guide:
[`DEMO_GUIDE.md`](DEMO_GUIDE.md).

**Recording the AI agents yourself** (optional — recordings are committed):
set `GEMINI_API_KEY` / `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` in your own shell,
then `python scripts/record_ai_agents.py --list-models` and
`python scripts/record_ai_agents.py --repeats 5`. The model is briefed with field
*names* and the job; no patient value ever leaves the machine, and the recordings
hold only field names and manifest choices.

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
  agent/            rule-based staff assistant: registry, session (recognise -> gate -> collect), guidance
scripts/            run_pipeline, run_benchmark, trace_one_patient, record_ai_agents, purge_exports, check_source,
                    rehearse_day_one (the real-data procedure on a hospital-shaped export, with a leak audit), ...
tools/mock_portal/  the login-gated portal fixture (Flask, TLS); tools/build_review_deck.py, tools/build_demo_page.py
tests/              274 tests
docs/
  compliance/       approach.md, dpdp-provision-map.md (section mapping, to verify against the Gazette)
  report/           outline.md and chapters 1-8 (drafts)
  review/           review-ii-flow.md (presenter script)
  access/           when-access-lands.md (day-one procedure for real data)
  methodology/      benchmark-protocol.md (every parameter behind the numbers; what would change one)
  benchmark_results/ tracked results, the navigation map, the demo page
.github/workflows/  ci: the suite, then the benchmark regenerated and diffed against the committed numbers
```

## Documents

- [`CLAUDE.md`](CLAUDE.md) — operating rules, build order, conventions
- [`PLAN.md`](PLAN.md) — definition of done, completion ledger, workstreams, decisions
- [`PROJECT_CONTEXT.md`](PROJECT_CONTEXT.md) — research framing and background
- [`docs/compliance/approach.md`](docs/compliance/approach.md) — the method in one page

## Team

Avanindra (23BLC1089) · Ananya (23BLC1017) · Guide: Dr. Manoj Kumar
