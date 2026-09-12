# CLAUDE.md

This file gives Claude Code persistent context for this repository. Read it fully before doing any work.

## Project Identity

**Name:** AI-Driven HIS Management Agent with DPDP-Compliant Web Scraping
**Institution:** VIT, SENSE department — final-year research project
**Team:** Avanindra (23BLC1089), Ananya (23BLC1017)
**Guide:** Dr. Manoj Kumar
**Stage:** Review-I cleared 02.09.2026 (outcome satisfactory). Building toward **Review-II**, which is the current focus. **The pipeline runs end to end** (`python scripts/run_pipeline.py`): a served login-gated portal, a real browser that logs in and crawls it, three techniques scored on the same seven DPDP rules with real page loads as cost, exports shaped to HL7 v2 / FHIR with identifiers pseudonymised and audited, one pull judged under every purpose, and the staff-guidance assistant placing its steps on the pages the crawler found. Ledger 85% (`PLAN.md` §5). Two reviews remain (as of 2026-09-12).

For full background, methodology, and research framing, see `PROJECT_CONTEXT.md` in this same directory — read it before starting any non-trivial task. For the definition of 100%, the completion ledger, and the sequenced workstreams to Review-II/III, see `PLAN.md`.

## Review Cadence — CURRENT FOCUS

**Review-I is done (02.09.2026) and the outcome was satisfactory.** Two reviews remain (as of 2026-09-12).

**Feedback carried forward from Review-I.** The panel's one substantive suggestion: **report processing time alongside the compliance score, for all three benchmarked techniques** (compliance-aware, minimising, coverage-optimised baseline). The harness currently times the benchmark as a whole (`BenchmarkResult.elapsed_ms`) but not each technique. Per-technique timing is now a required column in the headline table — it lets us answer "what does compliance cost you?" with a measured number rather than an assertion, and it turns the comparison into a genuine two-axis benchmark (compliance × cost) instead of a single-axis one.

- **Review-II — the immediate priority.** Floor: **~75% completion**. The stronger recommendation on top of that floor: **show that the entire pipeline runs end to end**, minor shortcomings accepted. A complete-but-rough pipeline demonstrates more than polished fragments. Concretely: one command that goes portal → extraction → normalisation → compliance scoring → ranked benchmark with per-technique timings, plus an agent layer that actually runs rather than a stub. Deck continues to use the mandatory VIT/SENSE Project-I 2026 template.
- **Review-III — everything, including the full project report and a publication-ready manuscript.** Deployment is explicitly **not** required — the graded contribution is the extraction + compliance-benchmarking work and its write-up.

## What This Project Is

We're building a system that scrapes and interfaces with Hospital Information Systems (HIS), with two layers of contribution:

1. **The scraping/extraction layer** — techniques for pulling structured data out of HIS portals (credentialed, Tier 2: headless browser automation).
2. **The compliance layer** — this is our actual research differentiator. Every scraping/extraction technique is designed and benchmarked against DPDP Act 2023 compliance criteria. Compliance is not a wrapper we add later; it constrains design choices from the start.
3. **The agent layer** — an agent that understands the HIS structure and returns simple, role-appropriate operating instructions to hospital staff (administrator / nurse / reception), differentiated by the type of task being performed.

**Scope change, 2026-09-12:** layer 3 was previously described here as a long-term vision "beyond this project's scope". It is now inside the graded scope and is part of the team's definition of 100% — see `PLAN.md` §1. Do not treat the staff-guidance agent as optional or future work.

**Where the contribution lies — read before prioritising anything.** The **DPDP compliance work is the novelty**; the paper and the report are about it. The agent is a deliverable that makes the project look complete, not a research contribution. Effort follows the contribution: compliance components get finished, the agent gets built small and left alone. Do not benchmark the agent, do not make it clever, and do not spend a session on it that a compliance component needed.

The two halves join through one mechanism: **role-based guidance and DPDP purpose limitation are the same check.** The compliance layer does not only score extraction runs after the fact — it also gates what the agent may instruct a given role to do (reception asking for clinical data is declined, with the rule cited). See `PLAN.md` §2.

## Current Phase Constraint — READ THIS FIRST

**We still do NOT have live HIS data access.** Credentialed access exists on paper but has not become usable and has now missed a full review cycle. **Expected by Review-II, however: a large dataset from the hospital**, and possibly live access. Plan for the dataset; treat live access as upside. Nothing built may *depend* on either arriving — the synthetic path must stay complete and runnable on its own.

**If a real hospital dataset arrives it is almost certainly real patient data.** A project whose whole contribution is data-protection compliance cannot be careless with it: confirm it is de-identified (or de-identify on receipt), `.gitignore` the data path *before* it lands, record its provenance and the basis on which it was shared, and check whether ethics approval is needed. See `PLAN.md` section 4.

This means, until told otherwise:
- Do NOT build against a real HIS endpoint.
- Do NOT wait on data access to make progress — work on everything that doesn't need it (see "Build Order" below).
- Any scraping module should be built against **mock/synthetic HIS data** we generate ourselves, with a clean interface boundary so the real HIS can be swapped in later without refactoring.
- If a task seems to require live data, stop and flag it rather than assuming/fabricating a workaround.

**The workaround (approved and built 2026-09-12): a locally served mock HIS portal** — `tools/mock_portal/`, Flask, login-gated, server-rendered HTML over any `HISDataSource`. The Tier 2 Playwright machinery scrapes it *for real*: real browser, real authentication, real DOM traversal, real pagination, real latency. It is a test fixture, not a product, and it is built on one rule the team set: **assume we do not control it.** The scraper holds a username and password and nothing else — no JSON endpoint, no data attributes, no hooks for the scraper's convenience; module URLs use portal vocabulary (`/m/registration/`, `/m/billing/`), not our layer names. If the adapter can read it, it is because it does what it would do against a real portal. It must scale to a **large dataset** (pagination is real, `--records 5000` pages for a while) and it serves the hospital dataset unchanged when that arrives. `LiveHISDataSource` stays a stub.

Run it: `python -m tools.mock_portal --records 500 --seed 42 --port 8765` (account `frontdesk` / `letmein`).

## Build Order (with current status)

Status as of 2026-09-12, re-baselined against the Review-II target.

1. **Done.** Repo scaffolding + project structure.
2. **Done.** DPDP compliance framework — 7 criteria as code-checkable pydantic rules (`src/compliance/rules/`), a declarative purpose policy, and a scored `ComplianceReport` artifact.
3. **Thin slice done; HL7/FHIR shaping done.** Synthetic HIS data generator — a field catalogue (name → HIS layer → DPDP category) and a Faker-seeded record generator (`src/data_synthetic/`); HL7 v2 and FHIR shaping of extracted rows (`src/interop/`). Still to do: per-layer pydantic schemas and the fifth layer's fields — better done once the hospital dataset shows the real structure.
4. **Done.** `HISDataSource` interface; `MockHISDataSource`; three techniques; the mock portal (`tools/mock_portal/`); and **Tier 2 for real** — `src/extraction/tier2/` (Playwright: form login, table/detail parsing, "Next" following, page-load counting; `navigation.discover()` crawls from the home page and **infers each module's HIS layer from the field names it finds**, never from the URL) behind `adapters/portal_his.PortalHISDataSource`. The three techniques run against it **unchanged** — the proof the adapter boundary holds. Detail pages are opened only when a requested field is not in the list table, so over-asking costs real page loads. Still to do here: a label→field mapping when a real portal's headers are display labels rather than field names (it belongs in the adapter), and the hospital-dataset adapter once its format is known.
5. **Done, on two axes.** `run_benchmark` scores every technique against every task with the same rule set and emits a ranked comparison table (`src/compliance/benchmark.py`) with a **cost profile** (`extraction/metering.py`: fields pulled, fetches, excess ratio, coverage, wall-clock, and **real page loads** when the source is the portal). Against the portal the compliant technique loads ~1/4 the pages the baseline does at identical coverage. Portal runs write `benchmark-portal.{json,md}`; in-memory runs write `benchmark.{json,md}`.
6. **Done (`src/agent/`) — the staff-guidance agent, on top of `compliance/roles.py`, with its steps placed on the crawler's pages via `Session(role, navigation=nav.agent_pages())`. Deliberately simple: NO LLM.** It recognises a **pre-defined function** from what the user types, asks for the input details that function needs, and replies with templated instructions. Rule-based, deterministic, no model, no training, no API key. The AXE-inspired *LLM extraction* agent is **cut** — AXE stays a literature citation only. The agent is a completeness deliverable, not a research contribution (see "Where the contribution lies" above); build it to work, keep it small, do not let it grow. Its one research-relevant property is that the function registry is **DPDP-gated per role** — reception asking for clinical data is declined with the rule cited.
7. **Blocked until data access; assume it stays blocked.** Swap synthetic source for live HIS, re-run benchmarks, tune.

Do not skip ahead to step 7 work. Do not silently substitute real HIS assumptions into steps 1–6 — keep the data source pluggable. The local mock portal is explicitly *not* step 7: it is a fixture that exercises step 4's browser code.

Runnable demos: `scripts/run_benchmark.py` (headline — technique comparison on compliance and cost), `scripts/compare_purposes.py` (one extraction, every purpose — the purpose-limitation result), `scripts/show_role_access.py` (role scopes derived from purpose × interop artefacts; one request through all three roles), `scripts/ask_agent.py` (the assistant in conversation — four scenes, or `--interactive`), `scripts/run_synthetic_extraction.py` (one technique, three configs), `scripts/score_extraction_run.py` (rules in isolation), plus `scripts/trace_one_patient.py` (single-record walkthrough). `scripts/generate_dataset.py` is still a stub that exits with "not implemented" — it belongs to build step 3, not to the demo set. **`scripts/run_pipeline.py` is the Review-II demo** — the whole chain in one command (~30–40 s at the default size; `--show` runs the browser visibly; `--records 200` pages for longer). See `DEMO_GUIDE.md` and `docs/compliance/approach.md`.

## Tech Stack

- **Language:** Python 3.10+ (primary — scraping, compliance logic, data handling)
- **Schema modelling:** pydantic v2 — DPDP compliance rules, the extraction manifest, and HIS record shapes
- **Scraping:** Playwright (Tier 2, headless browser automation) — chosen over Selenium; scrapes the mock portal. Browser binaries are a one-time `python -m playwright install chromium` on each machine (installed here 2026-09-12). Tier 2 tests skip cleanly where they are absent.
- **Mock portal fixture:** Flask 3 (`tools/mock_portal/`) — one dependency, sync, login sessions and templating built in; approved 2026-09-12
- **Agent:** rule-based function recognition + slot filling + templated instructions — plain Python, no LLM, no ML, no external API. (`anthropic` removed from `requirements.txt` 2026-09-12.)
- **Data handling:** pandas for structured records; synthetic data via Faker, generators shaped to the five-layer HIS model
- **Interoperability:** hand-rolled lightweight HL7 v2 / FHIR shapers (`src/interop/`, implemented) with DICOM / ISO-IEEE-11073 as stubs — no external interop libraries, no HIS vendor names. `interop.normalise` shapes a run's rows per the layer↔standard matrix, pseudonymises direct identifiers when the manifest declares it (`compliance.pseudonymise`, keyed tokens), and **audits the export** for raw identifiers — the compliant technique leaks none, the baseline leaks all
- **Testing:** pytest (`pytest.ini` sets `pythonpath = src .` — the `.` is for `tools/`)
- **Docs:** Markdown, kept in `/docs`

Confirm before introducing a new major dependency or language — don't assume.

## Coding & Writing Conventions

- No vendor names hard-coded into core logic (matches the academic-writing convention already used in slides/reports — keep code and docs consistent with that stance).
- All compliance-relevant code paths must be traceable to a DPDP Act 2023 principle — name it in a comment and in the rule's `provision` string (e.g., `# DPDP Act 2023 — storage limitation`). Exact section numbers are a report-time reference task, deliberately not pinned in code (they rot against a mis-transcribed clause).
- Keep the data-source layer abstracted (interface/adapter pattern) so `mock_his` and `live_his` are interchangeable without touching downstream code.
- Prefer small, reviewable commits/modules over large monolithic scripts — this is a research codebase that needs to produce legible artifacts for the paper, not just working software.
- When generating documentation or report-facing text (not code comments), use group-authored voice ("we"), no first-person singular — matches existing academic artifacts.

## Repo Structure (actual)

```
/src
  /compliance         # models, policy, roles, pseudonymise, rules/, checkers, summary, benchmark, report, purpose_matrix
  /data_synthetic     # catalogue (field → layer → DPDP category), generators/
  /extraction         # base (HISDataSource), metering, adapters/ (mock_his, portal_his, live_his stub),
                      #   technique + techniques/ (compliant, minimising, unconstrained),
                      #   tier2/ (browser: Playwright session; navigation: crawl + infer layers)
  /agent              # rule-based staff-guidance agent: functions (registry), session (recognise/gate/collect), guidance (output)
  /interop            # layers (five-layer HIS enum), mapping, normalise (shape + audit), hl7/ fhir/ (implemented), dicom/ iso_ieee_11073/ (stubs)
/scripts              # run_pipeline (end to end), run_benchmark, compare_purposes, show_role_access, ask_agent, ...
/tools
  /mock_portal        # Flask fixture: login-gated HTML portal over any HISDataSource (python -m tools.mock_portal);
                      #   serve.BackgroundPortal runs it in a thread for tests and scripts
/tests
/docs
  /architecture        # five-layer-his.md
  /compliance          # approach.md, dpdp-provision-map.md
  /benchmark_results    # tracked: benchmark.md, benchmark-portal.md, navigation-map.json, two purpose matrices; other runs git-ignored
CLAUDE.md   PROJECT_CONTEXT.md   README.md   DEMO_GUIDE.md   requirements.txt
```

## Working assumptions (accepted; revisit if inputs change)

- **Five-layer HIS model** — the functional decomposition in `src/interop/layers.py` is canonical (Patient Administration / Clinical-EHR / Ancillary-Departmental / Administrative-Financial / Infrastructure-Integration). The Review-1 deck's technical tiers were conceptual and are superseded. Reconfigure if real HIS access reveals a different structure.
- **DPDP citations** — rules name principles, not sections; exact sections finalised at report time.
- **Processing purposes** — three modelled (`care_coordination`, `billing_settlement`, `patient_registration`) with a declarative allowed-category policy. They are deliberately **pairwise non-nested**: no purpose's scope contains another's, so purposes are not ranked strict-to-lax and "out of scope" means *not necessary for this purpose*. Preserve that property when adding a fourth — a purpose that is a superset of an existing one collapses the distinction the benchmark rests on; a test asserts it. Claims adjudication is deliberately unmodelled for that reason.
- **Role access** (`src/compliance/roles.py`) is **derived, not listed**: a role's scope = (categories lawful under its purposes) ∩ (categories carried by the interop artefacts it handles — HL7 v2 / FHIR / DICOM / 11073). Team decision 2026-09-12: assume access follows the interoperability standards. `authorise()` is the gate the agent must call before answering; it denies under PL-01, DM-01 or SS-01 and names the rule. `fhir:Claim` and `dicom:Study` are granted to no role, by design.
- **The agent** (`src/agent/`) declares, per function, a purpose + the interop artefacts it touches + the inputs it needs + templated steps grounded in a layer, an artefact and catalogue fields. Who may perform a function is *not* stored — it is derived from `authorise()`. The gate runs **before** any input is collected (collecting details for a request you will refuse is over-collection). Recognition is token overlap; ties ask rather than guess. Every step's `page` is the seam for the Tier 2 navigation map — pass `Session(role, navigation={artefact: page})` and steps carry it; nothing else changes. Tests assert groundedness against `ARTEFACTS` and `FIELD_CATALOGUE`, so an instruction cannot refer to something the HIS model lacks.

## Open Research Questions (do not resolve unilaterally)

- **Login-gated portal vs public-documentation scraping priority** — unresolved, pending Dr. Manoj Kumar's input. Build the extraction layer so either path is supportable; don't commit architecture to one exclusively.
- **AutoScraper citation** — resolved: EMNLP 2024. A 12-paper literature-survey pool is researched for the Review-I deck's mandatory survey table.

## Working Style

- Discussion-first, then execution — for any non-trivial module, propose the approach briefly before writing significant code.
- Iterative refinement over rewrites — small targeted changes preferred once something exists.
- Flag assumptions explicitly, especially anything that implicitly assumes live HIS access or a resolved methodology question.
