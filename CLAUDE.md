# CLAUDE.md

This file gives Claude Code persistent context for this repository. Read it fully before doing any work.

## Project Identity

**Name:** AI-Driven HIS Management Agent with DPDP-Compliant Web Scraping
**Institution:** VIT, SENSE department — final-year research project
**Team:** Avanindra (23BLC1089), Ananya (23BLC1017)
**Guide:** Dr. Manoj Kumar
**Stage:** Review-I cleared 02.09.2026 (outcome satisfactory). Building toward **Review-II**, which is the current focus. Implemented and demoable today: repo scaffolding, the full DPDP compliance framework (7 rules), the synthetic-data + extraction slice, and the benchmarking harness. Two reviews remain (as of 2026-09-12).

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

The two halves join through one mechanism: **role-based guidance and DPDP purpose limitation are the same check.** The compliance layer does not only score extraction runs after the fact — it also gates what the agent may instruct a given role to do (reception asking for clinical data is declined, with the rule cited). See `PLAN.md` §2.

## Current Phase Constraint — READ THIS FIRST

**We still do NOT have live HIS data access.** Unchanged as of 2026-09-12: credentialed access exists on paper but has not become usable, and has now failed to materialise across a full review cycle. **Plan the rest of the build as though it never arrives.** If it unblocks, that is upside folded in via the adapter boundary — it is not a dependency any remaining deliverable rests on.

This means, until told otherwise:
- Do NOT build against a real HIS endpoint.
- Do NOT wait on data access to make progress — work on everything that doesn't need it (see "Build Order" below).
- Any scraping module should be built against **mock/synthetic HIS data** we generate ourselves, with a clean interface boundary so the real HIS can be swapped in later without refactoring.
- If a task seems to require live data, stop and flag it rather than assuming/fabricating a workaround.

**The proposed workaround (Review-II — proposed 2026-09-12, confirm with the team before building):** a **locally served mock HIS portal** — a login-gated web application we author ourselves, rendering synthetic records as HTML across the five-layer module structure. The Tier 2 Playwright machinery then scrapes it *for real*: real browser, real authentication, real DOM traversal, real pagination, real latency. This unblocks build step 4's browser layer and makes per-technique processing time a meaningful measurement rather than a microsecond artefact of in-memory dict access — without touching any real hospital system. The portal is a test fixture, not a product: it gets its own `HISDataSource` adapter, and `LiveHISDataSource` stays a stub.

## Build Order (with current status)

Status as of 2026-09-12, re-baselined against the Review-II target.

1. **Done.** Repo scaffolding + project structure.
2. **Done.** DPDP compliance framework — 7 criteria as code-checkable pydantic rules (`src/compliance/rules/`), a declarative purpose policy, and a scored `ComplianceReport` artifact.
3. **Thin slice done; Review-II work remains.** Synthetic HIS data generator — a field catalogue (name → HIS layer → DPDP category) and a Faker-seeded record generator (`src/data_synthetic/`). Still to do: per-layer pydantic schemas, the fifth layer's fields, and volume/variety wide enough to make timing differences legible.
4. **Substantially done; browser layer is the Review-II gap.** `HISDataSource` adapter interface, a working `MockHISDataSource`, and three techniques (compliance-aware, minimising, coverage-optimised baseline). `src/extraction/tier2/` is still empty — it is now unblocked by the local mock portal (see "Current Phase Constraint") and is the single highest-value remaining item.
5. **Working; needs the timing axis.** `run_benchmark` scores every technique against every task with the same rule set and emits a ranked comparison table (`src/compliance/benchmark.py`). This is the paper's core evidence. Review-I feedback adds **per-technique processing time** to it.
6. **Not started — now a headline deliverable, not scaffolding.** The agent has two roles: **(A)** an AXE-inspired extraction assistant that enters the benchmark as a further scored technique, and **(B)** the **role- and task-aware staff-guidance agent** that the 100% definition names. B outranks A — if time is short, sacrifice A. Both use off-the-shelf Claude via the Anthropic API, driven agentically — no fine-tuning, and the deck must say so. B is grounded in real artifacts (the `HISLayer` enum, the field catalogue, the navigation map the Tier 2 crawler discovers), never in hand-written prose, so its output is checkable rather than merely plausible.
7. **Blocked until data access; assume it stays blocked.** Swap synthetic source for live HIS, re-run benchmarks, tune.

Do not skip ahead to step 7 work. Do not silently substitute real HIS assumptions into steps 1–6 — keep the data source pluggable. The local mock portal is explicitly *not* step 7: it is a fixture that exercises step 4's browser code.

Three runnable demos exist: `scripts/run_benchmark.py` (headline — technique comparison), `scripts/run_synthetic_extraction.py` (one technique, three configs), `scripts/score_extraction_run.py` (rules in isolation), plus `scripts/trace_one_patient.py` and `scripts/generate_dataset.py`. See `DEMO_GUIDE.md` and `docs/compliance/approach.md`. Review-II wants one further script above these: a single end-to-end pipeline run.

## Tech Stack

- **Language:** Python 3.10+ (primary — scraping, compliance logic, data handling)
- **Schema modelling:** pydantic v2 — DPDP compliance rules, the extraction manifest, and HIS record shapes
- **Scraping:** Playwright (Tier 2, headless browser automation) — chosen over Selenium; machinery stubbed until data access
- **LLM integration:** Anthropic API (Claude) for agentic extraction logic (AXE-method inspired) — not yet built
- **Data handling:** pandas for structured records; synthetic data via Faker, generators shaped to the five-layer HIS model
- **Interoperability:** hand-rolled lightweight HL7 / FHIR / DICOM / ISO-IEEE-11073 shapers — no external interop libraries, no HIS vendor names
- **Testing:** pytest (`pytest.ini` sets `pythonpath = src`)
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
  /compliance         # models, policy, rules/, checkers, summary, benchmark, report
  /data_synthetic     # catalogue (field → layer → DPDP category), generators/
  /extraction         # base (HISDataSource), adapters/ (mock_his, live_his stub),
                      #   technique + techniques/ (compliant, minimising, unconstrained), tier2/ stub
  /agent              # LLM-based extraction agent (AXE-inspired) — stub
  /interop            # layers (five-layer HIS enum), mapping, hand-rolled hl7/fhir/dicom/iso_ieee_11073
/scripts              # run_benchmark, run_synthetic_extraction, score_extraction_run
/tests
/docs
  /architecture        # five-layer-his.md
  /compliance          # approach.md, dpdp-provision-map.md
  /benchmark_results    # benchmark.md tracked; per-run artifacts git-ignored
CLAUDE.md   PROJECT_CONTEXT.md   README.md   DEMO_GUIDE.md   requirements.txt
```

## Working assumptions (accepted; revisit if inputs change)

- **Five-layer HIS model** — the functional decomposition in `src/interop/layers.py` is canonical (Patient Administration / Clinical-EHR / Ancillary-Departmental / Administrative-Financial / Infrastructure-Integration). The Review-1 deck's technical tiers were conceptual and are superseded. Reconfigure if real HIS access reveals a different structure.
- **DPDP citations** — rules name principles, not sections; exact sections finalised at report time.
- **Processing purpose** — one modelled so far (`care_coordination`) with a declarative allowed-category policy.

## Open Research Questions (do not resolve unilaterally)

- **Login-gated portal vs public-documentation scraping priority** — unresolved, pending Dr. Manoj Kumar's input. Build the extraction layer so either path is supportable; don't commit architecture to one exclusively.
- **AutoScraper citation** — resolved: EMNLP 2024. A 12-paper literature-survey pool is researched for the Review-I deck's mandatory survey table.

## Working Style

- Discussion-first, then execution — for any non-trivial module, propose the approach briefly before writing significant code.
- Iterative refinement over rewrites — small targeted changes preferred once something exists.
- Flag assumptions explicitly, especially anything that implicitly assumes live HIS access or a resolved methodology question.
