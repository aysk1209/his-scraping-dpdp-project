# Project Context

Deeper background for `CLAUDE.md`. Read this once at project start and revisit when scope questions come up.

## Research Framing

Hospital Information Systems (HIS) hold high-value, high-sensitivity data. Existing web scraping techniques for extracting data from HIS portals are typically evaluated on speed, robustness, and coverage — rarely on data-protection compliance. This project's core contribution is showing that **DPDP Act 2023 compliance can be treated as a measurable, benchmarkable property of a scraping technique**, not just a legal afterthought bolted on post-hoc.

The applied use case — an AI agent that helps hospital staff operate the HIS — was originally the long-term motivating vision, justifying *why* extraction matters without itself being graded. **As of 2026-09-12 that changed: it is now part of the team's definition of 100%** (`PLAN.md` §1). The project is complete when we can show, in one run, data scraped from a portal, carried through the DPDP compliance pipeline, and an agent that understands the HIS structure well enough to return simple operating instructions differentiated by staff role (administrator / nurse / reception) and by task type.

That shift improves the project's coherence rather than diluting it. Role-based guidance and DPDP purpose limitation turn out to be the same mechanism: a receptionist has no clinical-category access under the purpose policy, so the agent declines and cites the rule. The compliance layer therefore does two jobs with one rule set — it scores extraction runs, and it gates agent guidance. The scraper discovers the HIS architecture; that discovered structure grounds the agent; the compliance layer constrains both.

## Review Structure

Two reviews remain. Review-I was presented on 02.09.2026 and **cleared satisfactorily**.

- **Review 1 (done):** Background, motivation, architecture, proposed methodology, DPDP framing. Deliverables: 16-slide deck, briefing doc, background review report.
- **Review-I (done, 02.09.2026 — satisfactory).** Explained the architecture, the compliance-as-benchmarkable-property thesis, and how progress continues without live HIS data; demoed the runnable benchmark. Delivered on the mandatory VIT/SENSE Project-I 2026 template with the literature-survey table. **Panel suggestion to carry forward: show processing time for each of the three techniques** (compliance-aware, minimising, coverage-optimised baseline) next to the compliance score.
- **Review-II (next).** Floor **~75% completion**, but the stated preference is stronger and different in kind: **demonstrate the whole pipeline working end to end, minor shortcomings accepted**. Read that as "breadth of a working path beats depth of any one component". Expected: real Tier 2 browser extraction (against our own locally served mock portal), the agent layer running rather than stubbed, a real baseline technique scored, wider synthetic coverage, and the benchmark reporting compliance **and** cost.
- **Review-III — everything, including the full project report and a publication-ready manuscript.** Deployment is explicitly **not** required; the graded contribution is the extraction + compliance-benchmarking work and its write-up.

### Why "processing time" matters more than it looks

The suggestion reads as a small table column, but it changes what the benchmark argues. Today the headline claim is one-dimensional: technique A is more compliant than technique C on identical rules. The obvious reviewer question — *and what does that compliance cost?* — currently has no measured answer. Adding time makes the evidence a two-axis comparison (compliance × cost) and lets us state the trade-off explicitly, whichever way it falls: if compliance-aware extraction is *cheaper* (it pulls fewer fields), that is a result in our favour; if it is dearer, quantifying the premium is more credible than not measuring it. Either way it is a stronger paper. Note that timing only becomes meaningful once extraction does real work — against in-memory dicts every technique finishes in microseconds, which is the second reason the mock portal matters.

## Technical Foundations Already Established

- **Five-layer HIS architecture** — a functional decomposition (Patient Administration / Clinical-EHR / Ancillary-Departmental / Administrative-Financial / Infrastructure-Integration), now canonical in code as the `HISLayer` enum in `src/interop/layers.py`. Everything downstream imports it rather than re-declaring layers. The Review-1 deck's technical tiers were conceptual and are superseded by this. Not flattened into a single schema.
- **Four interoperability standards:** HL7, FHIR, DICOM, ISO/IEEE 11073 — mapped per layer in `src/interop/mapping.py`. Synthetic data and extraction outputs should be structurable into at least HL7/FHIR-shaped records; hand-rolled lightweight shapers, HL7/FHIR prioritised.
- **AXE method (Cairo University)** — LLM-based agentic extraction technique; conceptual basis for the `/agent` module's *extraction* role (not yet built). The module's *staff-guidance* role, added to scope 2026-09-12, is our own contribution and has no direct antecedent in the surveyed literature — which is worth saying plainly in the manuscript.
- **AutoScraper (EMNLP 2024)** — comparison baseline technique. Venue confirmed. Currently represented by a generic "coverage-optimised baseline" technique in the benchmark; a real implementation is Review-II work.

## Scraping Tier Decision

Tiering (as established pre-build):
- **Tier 2 — headless browser automation (Playwright):** chosen primary methodology, for credentialed portal scraping. Playwright chosen over Selenium. The machinery is still unwritten, but is **no longer blocked** — it is now built and exercised against our own locally served mock portal (see "Data Access Status"), with the live portal as a later re-targeting.
- **Public-documentation scraping:** retained as an undocumented fallback, not the primary path.
- **Open question:** whether to prioritize login-gated portal scraping vs public-documentation scraping determines which Tier 3/4 techniques get developed further downstream. Still unresolved; should go to Dr. Manoj Kumar before Review-II implementation locks in. The mock portal is login-gated, which implicitly leans toward the first path — worth confirming rather than letting the fixture decide the methodology.

## Data Access Status

Credentialed access to a live hospital HIS was secured as the intended primary data source but is **still not usable** as of 2026-09-12 — it did not arrive before Review-I and there is no committed date. **The working position is now that it does not arrive at all.** Every remaining deliverable must be reachable without it; live access, if it lands, is folded in through the adapter boundary as an improvement to results, never as a prerequisite.

The workaround proposed for the Review-II end-to-end demonstration (2026-09-12, not yet confirmed) is a **locally served mock HIS portal**: a login-gated web application we author, serving synthetic records as HTML pages organised by the five-layer module structure (pagination, a search form, per-patient detail pages, a session cookie). Playwright drives it exactly as it would drive a real portal. This is the piece that converts "the browser layer is stubbed" into "the browser layer works, just not yet pointed at a hospital" — a materially different thing to present, and it makes the swap to a real portal a matter of selectors and credentials rather than unwritten code.

The extraction layer is built adapter-style (`HISDataSource` → `MockHISDataSource` today, a portal-scraping adapter next, `LiveHISDataSource` stub) so the substitution is a config change, not a rewrite.

## DPDP Act 2023 — Why It's Central

Framed as a comparative advantage over existing scraping literature, not a compliance checkbox. Practical implication for build: every extraction technique implemented is paired with a compliance check that produces a *score plus a per-principle breakdown*, not a paragraph. **This is implemented:** seven rules (data minimisation, lawful basis, storage limitation, security safeguards, purpose limitation, transparency/notice, accountability), a declarative purpose policy, and `run_benchmark`, which scores every technique against every task with the same rule set and emits a ranked comparison table. That table is what will be run against a real AutoScraper baseline at Review-II.

## Writing/Artifact Conventions (carried over from Review 1 artifacts)

- Group-authored voice ("we"), no first-person singular, in all report-facing text.
- No vendor names in HIS-related sections or in core code.
- **Review-I and later decks must use the mandatory VIT/SENSE Project-I 2026 template** — white background, navy `1D2F82`, fixed 11-slide sequence. Do not restyle it. (This overrides the earlier "teal palette / follow the Review-1 deck" note.)
- Content-rich over sparse — avoid padding, but don't under-fill when a length/depth expectation exists.

## Current Implementation State (2026-09-12)

- **Done:** repo scaffolding; the 7-rule DPDP compliance framework + policy + scored `ComplianceReport`; the benchmarking harness (`run_benchmark`) with a three-technique comparison; the hand-rolled HL7 / FHIR / DICOM / ISO-IEEE-11073 shapers and the five-layer mapping.
- **Slice done:** synthetic data generator (field catalogue covering four of the five layers + Faker generator); extraction adapter (`MockHISDataSource`) + technique layer.
- **Not started:** LLM agent (`src/agent/` is a docstring); real Tier 2 browser code (`src/extraction/tier2/` is empty); the mock HIS portal; per-technique timing in the benchmark; full per-layer pydantic schemas; a real AutoScraper baseline.
- Five runnable scripts, ~90 passing tests, a browsable result at `docs/benchmark_results/benchmark.md`. See `DEMO_GUIDE.md` and `docs/compliance/approach.md`.

## Known Loose Ends

- Login-gated vs public-documentation prioritization — pending guide input; the mock portal quietly presumes login-gated, so confirm it.
- Live HIS access — no committed date; **treated as never arriving** for planning purposes.
- Five-layer model and the `care_coordination` purpose are working assumptions, not sourced from Review-1 artifacts — accepted for now, reconfigure if real HIS access differs.
- A second processing purpose is still unmodelled, which limits what the purpose-limitation rule can discriminate between.
- **Review-II date is not yet recorded** — everything downstream of it is sequenced but not calendared.
