# CLAUDE.md

This file gives Claude Code persistent context for this repository. Read it fully before doing any work.

## Project Identity

**Name:** AI-Driven HIS Management Agent with DPDP-Compliant Web Scraping
**Institution:** VIT, SENSE department — final-year research project
**Team:** Avanindra (23BLC1089), Ananya (23BLC1017)
**Guide:** Dr. Manoj Kumar
**Stage:** Post Review-1 (approved). In the build phase — repo scaffolding, the full DPDP compliance framework (7 rules), the synthetic-data + extraction slice, and the benchmarking harness are implemented and demoable. Three reviews remain (as of 2026-08-29).

For full background, methodology, and research framing, see `PROJECT_CONTEXT.md` in this same directory — read it before starting any non-trivial task.

## Review Cadence — CURRENT FOCUS

Three reviews remain (as of 2026-08-29), superseding the earlier "Review 2 (~70%) then Final review" framing:

- **Review-I (upcoming, 02.09.2026) — the immediate priority. No fixed percentage of work.** Do not optimise for volume of implemented code. What is graded: a **precise, on-point explanation to the reviewer** — the architecture, the "DPDP compliance as a benchmarkable property" thesis, and how progress continues without live HIS data access — plus **one small, concrete deliverable** to demonstrate (the runnable compliance-scoring / benchmark demo). The deck must use the mandatory VIT/SENSE Project-I 2026 template (fixed 11-slide sequence, white background, navy `1D2F82`, 8–10 min); a literature-survey table of 8–10 recent references is required.
- **Review-II — a solid ~75% completion.** Real implemented breadth: extraction layer built out, agent scaffolding, benchmark harness scoring at least one real baseline, wider synthetic coverage; live HIS folded in if access unblocks.
- **Review-III — everything, including the full project report and a publication-ready manuscript.** Deployment is explicitly **not** required — the graded contribution is the extraction + compliance-benchmarking work and its write-up.

## What This Project Is

We're building a system that scrapes and interfaces with Hospital Information Systems (HIS), with two layers of contribution:

1. **The scraping/extraction layer** — techniques for pulling structured data out of HIS portals (credentialed, Tier 2: headless browser automation).
2. **The compliance layer** — this is our actual research differentiator. Every scraping/extraction technique is designed and benchmarked against DPDP Act 2023 compliance criteria. Compliance is not a wrapper we add later; it constrains design choices from the start.

The long-term vision (beyond this project's scope, but informs architecture) is an AI agent that helps hospital staff use and adapt to HIS systems without workflow disruption.

## Current Phase Constraint — READ THIS FIRST

**We do NOT have live HIS data access yet.** Credentialed access exists on paper but is not usable right now.

This means, until told otherwise:
- Do NOT build against a real HIS endpoint.
- Do NOT wait on data access to make progress — work on everything that doesn't need it (see "Build Order" below).
- Any scraping module should be built against **mock/synthetic HIS data** we generate ourselves, with a clean interface boundary so the real HIS can be swapped in later without refactoring.
- If a task seems to require live data, stop and flag it rather than assuming/fabricating a workaround.

## Build Order (with current status)

1. **Done.** Repo scaffolding + project structure.
2. **Done.** DPDP compliance framework — 7 criteria as code-checkable pydantic rules (`src/compliance/rules/`), a declarative purpose policy, and a scored `ComplianceReport` artifact.
3. **Thin slice done.** Synthetic HIS data generator — a field catalogue (name → HIS layer → DPDP category) and a Faker-seeded record generator (`src/data_synthetic/`). Full per-layer pydantic schemas + HL7/FHIR shaping still to do.
4. **Substantially done.** Extraction layer — `HISDataSource` adapter interface, a working `MockHISDataSource`, and a technique layer with three techniques (compliance-aware, minimising, coverage-optimised baseline). Tier 2 browser machinery still stubbed.
5. **Working.** Compliance benchmarking harness — `run_benchmark` scores every technique against every task with the same rule set and emits a ranked comparison table (`src/compliance/benchmark.py`). This is the paper's core evidence.
6. **Not started.** LLM-agent scaffolding (AXE-method-inspired extraction assistant) — to be built against synthetic data.
7. **Blocked until data access.** Swap synthetic source for live HIS, re-run benchmarks, tune.

Do not skip ahead to step 7 work. Do not silently substitute real HIS assumptions into steps 1–6 — keep the data source pluggable.

Three runnable demos exist: `scripts/run_benchmark.py` (headline — technique comparison), `scripts/run_synthetic_extraction.py` (one technique, three configs), `scripts/score_extraction_run.py` (rules in isolation). See `DEMO_GUIDE.md` and `docs/compliance/approach.md`.

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
