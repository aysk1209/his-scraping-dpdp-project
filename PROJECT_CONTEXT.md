# Project Context

Deeper background for `CLAUDE.md`. Read this once at project start and revisit when scope questions come up.

## Research Framing

Hospital Information Systems (HIS) hold high-value, high-sensitivity data. Existing web scraping techniques for extracting data from HIS portals are typically evaluated on speed, robustness, and coverage — rarely on data-protection compliance. This project's core contribution is showing that **DPDP Act 2023 compliance can be treated as a measurable, benchmarkable property of a scraping technique**, not just a legal afterthought bolted on post-hoc.

The applied use case (an AI agent that helps hospital staff manage/adapt to HIS systems) is the long-term motivating vision — it justifies *why* extraction matters, but the graded research contribution for this project is the extraction + compliance benchmarking work itself.

## Review Structure

- **Review 1 (done):** Background, motivation, architecture, proposed methodology, DPDP framing. Deliverables: 16-slide deck, briefing doc, background review report.
- **Review 2 (next, target ~70% completion):** Working implementation of chosen extraction tier against a data source (synthetic now, live HIS if access resolves in time), initial compliance benchmark results, resolved technique-tier decision.
- **Final review:** Full execution, complete benchmarking across techniques, target publication.

## Technical Foundations Already Established

- **Five-layer HIS architecture** — informs how the synthetic data generator and extraction interfaces should be structured (don't flatten this into a single schema).
- **Four interoperability standards:** HL7, FHIR, DICOM, ISO/IEEE 11073 — synthetic data and extraction outputs should be structurable into at least HL7/FHIR-shaped records to keep the work realistic.
- **AXE method (Cairo University)** — LLM-based agentic extraction technique; conceptual basis for the `/agent` module.
- **AutoScraper (EMNLP 2024)** — comparison baseline technique; citation needs the venue/year finalized in any reference list.

## Scraping Tier Decision

Tiering (as established pre-build):
- **Tier 2 — headless browser automation (Selenium/Playwright):** chosen primary methodology, for credentialed live-HIS portal scraping.
- **Public-documentation scraping:** retained as an undocumented fallback, not the primary path.
- **Open question:** whether to prioritize login-gated portal scraping vs public-documentation scraping determines which Tier 3/4 techniques get developed further downstream. This is unresolved and should ideally go to Dr. Manoj Kumar before Review 2 implementation locks in.

## Data Access Status

Credentialed access to a live hospital HIS has been secured as the intended primary data source, but is **not currently usable** for building. Build phase must not stall on this — everything not strictly requiring live records (compliance framework, architecture, agent scaffolding, synthetic-data-driven extraction) proceeds now. The extraction layer must be built adapter-style so swapping synthetic → live is a config change, not a rewrite.

## DPDP Act 2023 — Why It's Central

Framed as a comparative advantage over existing scraping literature, not a compliance checkbox. Practical implication for build: every extraction technique implemented should be paired with a compliance check (e.g., data minimization, purpose limitation, storage limitation, consent/legitimate-use basis, security safeguards) that produces a *score or pass/fail artifact*, not just a paragraph in the report. This is what gets benchmarked against AutoScraper and other baseline techniques.

## Writing/Artifact Conventions (carried over from Review 1 artifacts)

- Group-authored voice ("we"), no first-person singular, in all report-facing text.
- No vendor names in HIS-related sections.
- Teal / dark-teal visual palette for any future decks (Review 2 slides will likely follow the Review 1 deck's visual language).
- Content-rich over sparse — avoid padding, but don't under-fill when a length/depth expectation exists.

## Known Loose Ends

- AutoScraper reference needs venue (EMNLP 2024) added to bibliography.
- Login-gated vs public-documentation prioritization — pending guide input.
- Live HIS access timeline — unresolved as of build-phase start.
