# CLAUDE.md

This file gives Claude Code persistent context for this repository. Read it fully before doing any work.

## Project Identity

**Name:** AI-Driven HIS Management Agent with DPDP-Compliant Web Scraping
**Institution:** VIT, SENSE department — final-year research project
**Team:** Avanindra (23BLC1089), Ananya (23BLC1017)
**Guide:** Dr. Manoj Kumar
**Stage:** Post Review-1 (approved). In the build phase. Three reviews remain (as of 2026-08-29).

For full background, methodology, and research framing, see `PROJECT_CONTEXT.md` in this same directory — read it before starting any non-trivial task.

## Review Cadence — CURRENT FOCUS

Three reviews remain (as of 2026-08-29). This supersedes the earlier "Review 2 (~70% completion) then Final review" framing (still worded the old way in `PROJECT_CONTEXT.md`).

**The upcoming review is the immediate priority.** For it:
- There is **no fixed percentage of work** expected — do not optimise for volume of implemented code.
- What is graded: a **precise, on-point explanation to the reviewer** — the architecture, the "DPDP compliance as a benchmarkable property" thesis, and how progress continues without live HIS data access.
- Plus **one small, concrete deliverable** to demonstrate (e.g. a runnable compliance-scoring demo), not a large build.

Scope for the two later reviews is not yet fixed — revisit after this one.

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

## Build Order (current priority)

1. Repo scaffolding + project structure (this session)
2. DPDP compliance framework — define the compliance criteria as code-checkable rules/schema, not just prose
3. Synthetic HIS data generator — fake patient/admin records matching the five-layer HIS architecture, used to develop and test everything downstream
4. Extraction module skeleton — interface/abstract layer for Tier 2 scraping, implemented first against the synthetic data source
5. Compliance benchmarking harness — measures any extraction run against the DPDP criteria (this is the paper's core evidence)
6. LLM-agent scaffolding (AXE-method-inspired extraction assistant) — built against synthetic data
7. (Blocked until data access) — swap synthetic source for live HIS, re-run benchmarks, tune

Do not skip ahead to step 7 work. Do not silently substitute real HIS assumptions into steps 1–6 — keep the data source pluggable.

## Tech Stack

- **Language:** Python (primary — scraping, compliance logic, data handling)
- **Scraping:** Selenium / Playwright (Tier 2, headless browser automation) — stubbed until data access
- **LLM integration:** Anthropic API (Claude) for agentic extraction logic (AXE-method inspired)
- **Data handling:** pandas for structured records; synthetic data generation via Faker or custom generators shaped to HIS schemas (HL7/FHIR-like)
- **Testing:** pytest
- **Docs:** Markdown, kept in `/docs`

Confirm before introducing a new major dependency or language — don't assume.

## Coding & Writing Conventions

- No vendor names hard-coded into core logic (matches the academic-writing convention already used in slides/reports — keep code and docs consistent with that stance).
- All compliance-relevant code paths must be traceable to a specific DPDP Act 2023 provision — comment with the section reference (e.g., `# DPDP Act 2023, Sec 8(5) — data retention limitation`).
- Keep the data-source layer abstracted (interface/adapter pattern) so `mock_his` and `live_his` are interchangeable without touching downstream code.
- Prefer small, reviewable commits/modules over large monolithic scripts — this is a research codebase that needs to produce legible artifacts for the paper, not just working software.
- When generating documentation or report-facing text (not code comments), use group-authored voice ("we"), no first-person singular — matches existing academic artifacts.

## Repo Structure (target)

```
/src
  /compliance        # DPDP rule definitions, checkers, benchmarking harness
  /data_synthetic     # synthetic HIS data generator
  /extraction         # scraping/extraction layer (adapter pattern: mock vs live)
  /agent              # LLM-based extraction agent (AXE-inspired)
  /interop            # HL7/FHIR/DICOM/ISO-IEEE-11073 schema helpers
/tests
/docs
  PROJECT_CONTEXT.md
  benchmark_results/
CLAUDE.md
README.md
requirements.txt
```

## Open Research Questions (do not resolve unilaterally)

- **Login-gated portal vs public-documentation scraping priority** — unresolved, pending Dr. Manoj Kumar's input. Build the extraction layer so either path is supportable; don't commit architecture to one exclusively.
- **AutoScraper citation** — venue is EMNLP 2024, needs to be finalized in the references list of any report output.

## Working Style

- Discussion-first, then execution — for any non-trivial module, propose the approach briefly before writing significant code.
- Iterative refinement over rewrites — small targeted changes preferred once something exists.
- Flag assumptions explicitly, especially anything that implicitly assumes live HIS access or a resolved methodology question.
