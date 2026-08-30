# Project Context

Deeper background for `CLAUDE.md`. Read this once at project start and revisit when scope questions come up.

## Research Framing

Hospital Information Systems (HIS) hold high-value, high-sensitivity data. Existing web scraping techniques for extracting data from HIS portals are typically evaluated on speed, robustness, and coverage — rarely on data-protection compliance. This project's core contribution is showing that **DPDP Act 2023 compliance can be treated as a measurable, benchmarkable property of a scraping technique**, not just a legal afterthought bolted on post-hoc.

The applied use case (an AI agent that helps hospital staff manage/adapt to HIS systems) is the long-term motivating vision — it justifies *why* extraction matters, but the graded research contribution for this project is the extraction + compliance benchmarking work itself.

## Review Structure

Three reviews remain from the build phase (fixed by the team 2026-08-29; this replaces the earlier "Review 2 then Final review" two-step framing).

- **Review 1 (done):** Background, motivation, architecture, proposed methodology, DPDP framing. Deliverables: 16-slide deck, briefing doc, background review report.
- **Review-I (upcoming, 02.09.2026) — no fixed percentage of work.** On-point explanation to the reviewer (architecture, the compliance-as-benchmarkable-property thesis, progress without live HIS data) plus one small concrete deliverable (the runnable benchmark demo). Deck must use the mandatory VIT/SENSE Project-I 2026 template — fixed 11-slide sequence, white background, navy `1D2F82`, 8–10 min, 5% weight, problem-clarity weighted highest. A literature-survey table of 8–10 recent references is mandatory.
- **Review-II — a solid ~75% completion.** Extraction layer built out, agent scaffolding, benchmark harness scoring at least one real baseline, wider synthetic coverage; live HIS folded in if access unblocks.
- **Review-III — everything, including the full project report and a publication-ready manuscript.** Deployment is explicitly **not** required; the graded contribution is the extraction + compliance-benchmarking work and its write-up.

## Technical Foundations Already Established

- **Five-layer HIS architecture** — a functional decomposition (Patient Administration / Clinical-EHR / Ancillary-Departmental / Administrative-Financial / Infrastructure-Integration), now canonical in code as the `HISLayer` enum in `src/interop/layers.py`. Everything downstream imports it rather than re-declaring layers. The Review-1 deck's technical tiers were conceptual and are superseded by this. Not flattened into a single schema.
- **Four interoperability standards:** HL7, FHIR, DICOM, ISO/IEEE 11073 — mapped per layer in `src/interop/mapping.py`. Synthetic data and extraction outputs should be structurable into at least HL7/FHIR-shaped records; hand-rolled lightweight shapers, HL7/FHIR prioritised.
- **AXE method (Cairo University)** — LLM-based agentic extraction technique; conceptual basis for the `/agent` module (not yet built).
- **AutoScraper (EMNLP 2024)** — comparison baseline technique. Venue confirmed. Currently represented by a generic "coverage-optimised baseline" technique in the benchmark; a real implementation is Review-II work.

## Scraping Tier Decision

Tiering (as established pre-build):
- **Tier 2 — headless browser automation (Playwright):** chosen primary methodology, for credentialed live-HIS portal scraping. Playwright chosen over Selenium; the browser machinery is stubbed until data access.
- **Public-documentation scraping:** retained as an undocumented fallback, not the primary path.
- **Open question:** whether to prioritize login-gated portal scraping vs public-documentation scraping determines which Tier 3/4 techniques get developed further downstream. Still unresolved; should go to Dr. Manoj Kumar before Review-II implementation locks in.

## Data Access Status

Credentialed access to a live hospital HIS has been secured as the intended primary data source, but is **not currently usable** for building, and may slip past Review-I. Build phase must not stall on this — everything not strictly requiring live records (compliance framework, architecture, agent scaffolding, synthetic-data-driven extraction) proceeds now. The extraction layer is built adapter-style (`HISDataSource` → `MockHISDataSource` today, `LiveHISDataSource` stub) so swapping synthetic → live is a config change, not a rewrite.

## DPDP Act 2023 — Why It's Central

Framed as a comparative advantage over existing scraping literature, not a compliance checkbox. Practical implication for build: every extraction technique implemented is paired with a compliance check that produces a *score plus a per-principle breakdown*, not a paragraph. **This is implemented:** seven rules (data minimisation, lawful basis, storage limitation, security safeguards, purpose limitation, transparency/notice, accountability), a declarative purpose policy, and `run_benchmark`, which scores every technique against every task with the same rule set and emits a ranked comparison table. That table is what will be run against a real AutoScraper baseline at Review-II.

## Writing/Artifact Conventions (carried over from Review 1 artifacts)

- Group-authored voice ("we"), no first-person singular, in all report-facing text.
- No vendor names in HIS-related sections or in core code.
- **Review-I and later decks must use the mandatory VIT/SENSE Project-I 2026 template** — white background, navy `1D2F82`, fixed 11-slide sequence. Do not restyle it. (This overrides the earlier "teal palette / follow the Review-1 deck" note.)
- Content-rich over sparse — avoid padding, but don't under-fill when a length/depth expectation exists.

## Current Implementation State (2026-08-30)

- **Done:** repo scaffolding; the 7-rule DPDP compliance framework + policy + scored `ComplianceReport`; the benchmarking harness (`run_benchmark`) with a three-technique comparison.
- **Slice done:** synthetic data generator (field catalogue + Faker generator); extraction adapter (`MockHISDataSource`) + technique layer.
- **Not started:** LLM agent; full per-layer schemas + HL7/FHIR shaping; real Tier 2 browser code; a real AutoScraper baseline.
- Three runnable demos, ~90 passing tests, a browsable result at `docs/benchmark_results/benchmark.md`. See `DEMO_GUIDE.md` and `docs/compliance/approach.md`.

## Known Loose Ends

- Login-gated vs public-documentation prioritization — pending guide input.
- Live HIS access timeline — unresolved; likely to slip past Review-I.
- Five-layer model and the `care_coordination` purpose are working assumptions, not sourced from Review-1 artifacts — accepted for now, reconfigure if real HIS access differs.
