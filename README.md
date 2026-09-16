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

`python scripts/run_benchmark.py` — four tasks, in memory, five repeats:

| Technique | Compliance | Coverage | Excess ratio | Reproduced its decision |
|---|---:|---:|---:|---:|
| compliance-aware (ours) | **1.000** | 1.00 | 1.00× | **5 / 5** |
| AI agent — Gemini, told the Act | 0.991 | 0.74 | 1.05× | 2 / 5 |
| AI agent — Gemini, unaided | 0.955 | 0.74 | 1.10× | 3 / 5 |
| unconstrained baseline | 0.134 | 1.00 | 6.53× | 5 / 5 |

A current public model nearly matches the rule-driven technique on the *manifest
it declares* — even unaided it cites a lawful basis, retention, a notice and an
accountable party. It differs on **what it takes** (a name where the task needs
the record number; an e-mail where it needs the phone — lawful categories, so the
score never notices, but 74% of the job) and on **whether it takes the same
fields twice** (two or three of five identical runs). Ours reproduces itself by
construction. On the portal the baseline loads 330 pages to our 70 for the same
coverage; its 7× surplus is exactly the overreach the minimisation rule penalises.

One-page figure: [`docs/benchmark_results/techniques-compared.html`](docs/benchmark_results/techniques-compared.html).
Full tables: [`benchmark.md`](docs/benchmark_results/benchmark.md),
[`benchmark-portal.md`](docs/benchmark_results/benchmark-portal.md).

## Run it

```bash
python -m venv .venv && .venv\Scripts\activate      # POSIX: source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium                # once per machine
pytest                                               # 236 tests, ~30 s
python scripts/run_pipeline.py                       # the whole chain, ~1.5 min
```

`run_pipeline.py` serves a login-gated portal, logs a headless browser into it,
discovers its modules, runs every technique with real page loads as cost, shapes
the compliant run into HL7 v2 / FHIR with identifiers pseudonymised and audited,
re-judges one pull under every purpose, and puts one question per role to the
assistant. No network, no key: the AI agents replay their recorded decisions.

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
                    pseudonymisation, real-data handling gate
  extraction/       HISDataSource interface; adapters (in-memory, portal via Playwright, dataset);
                    techniques (compliance-aware, AI agents + recordings, baseline); metering; tier2 crawler
  data_synthetic/   field catalogue (field -> layer -> DPDP category), generator, schemas, export
  interop/          five-layer HIS model, layer <-> standard map, HL7 v2 / FHIR shapers, export audit
  agent/            rule-based staff assistant: registry, session (recognise -> gate -> collect), guidance
scripts/            run_pipeline, run_benchmark, trace_one_patient, record_ai_agents, check_source, ...
tools/mock_portal/  the login-gated portal fixture (Flask); tools/build_review_deck.py
tests/              236 tests
docs/
  compliance/       approach.md, dpdp-provision-map.md (section mapping, to verify against the Gazette)
  report/           outline.md and chapters 1-8 (drafts)
  review/           review-ii-flow.md (presenter script)
  access/           when-access-lands.md (day-one procedure for real data)
  benchmark_results/ tracked results, the navigation map, the one-page figure
```

## Documents

- [`CLAUDE.md`](CLAUDE.md) — operating rules, build order, conventions
- [`PLAN.md`](PLAN.md) — definition of done, completion ledger, workstreams, decisions
- [`PROJECT_CONTEXT.md`](PROJECT_CONTEXT.md) — research framing and background
- [`docs/compliance/approach.md`](docs/compliance/approach.md) — the method in one page

## Team

Avanindra (23BLC1089) · Ananya (23BLC1017) · Guide: Dr. Manoj Kumar
