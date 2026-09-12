# Project Context

Deeper background for `CLAUDE.md`. Read this once at project start and revisit when scope questions come up.

## Research Framing

Hospital Information Systems (HIS) hold high-value, high-sensitivity data. Existing web scraping techniques for extracting data from HIS portals are typically evaluated on speed, robustness, and coverage — rarely on data-protection compliance. This project's core contribution is showing that **DPDP Act 2023 compliance can be treated as a measurable, benchmarkable property of a scraping technique**, not just a legal afterthought bolted on post-hoc.

The applied use case — an AI agent that helps hospital staff operate the HIS — was originally the long-term motivating vision, justifying *why* extraction matters without itself being graded. **As of 2026-09-12 that changed: it is now part of the team's definition of 100%** (`PLAN.md` §1). The project is complete when we can show, in one run, data scraped from a portal, carried through the DPDP compliance pipeline, and an agent that understands the HIS structure well enough to return simple operating instructions differentiated by staff role (administrator / nurse / reception) and by task type.

**The compliance work remains the contribution.** The agent is a completeness deliverable — deliberately simple, rule-based, no LLM: it recognises a pre-defined function from user input, asks for the details that function needs, and returns templated instructions. The paper and the report stay focused on compliance throughout.

What keeps the agent from being decoration is a single property: role-based guidance and DPDP purpose limitation are **the same mechanism**. A receptionist has no clinical-category access under the purpose policy, so the agent declines and cites the rule. The compliance layer therefore does two jobs with one rule set — it scores extraction runs, and it gates staff guidance. The scraper discovers the HIS structure; that structure grounds the instructions; the compliance layer constrains both.

## Review Structure

Two reviews remain. Review-I was presented on 02.09.2026 and **cleared satisfactorily**.

- **Review 1 (done):** Background, motivation, architecture, proposed methodology, DPDP framing. Deliverables: 16-slide deck, briefing doc, background review report.
- **Review-I (done, 02.09.2026 — satisfactory).** Explained the architecture, the compliance-as-benchmarkable-property thesis, and how progress continues without live HIS data; demoed the runnable benchmark. Delivered on the mandatory VIT/SENSE Project-I 2026 template with the literature-survey table. **Panel suggestion to carry forward: show processing time for each of the three techniques** (compliance-aware, minimising, coverage-optimised baseline) next to the compliance score.
- **Review-II (next).** Floor **~75% completion**, but the stated preference is stronger and different in kind: **demonstrate the whole pipeline working end to end, minor shortcomings accepted**. Read that as "breadth of a working path beats depth of any one component". Expected: real Tier 2 browser extraction (against our own locally served mock portal), the agent layer running rather than stubbed, a real baseline technique scored, wider synthetic coverage, and the benchmark reporting compliance **and** cost.
- **Review-III — everything, including the full project report and a publication-ready manuscript.** Deployment is explicitly **not** required; the graded contribution is the extraction + compliance-benchmarking work and its write-up.

### Why "processing time" matters more than it looks

The suggestion reads as a small table column, but it changes what the benchmark argues. Today the headline claim is one-dimensional: technique A is more compliant than technique C on identical rules. The obvious reviewer question — *and what does that compliance cost?* — currently has no measured answer. Adding time makes the evidence a two-axis comparison (compliance × cost) and lets us state the trade-off explicitly, whichever way it falls: if compliance-aware extraction is *cheaper* (it pulls fewer fields), that is a result in our favour; if it is dearer, quantifying the premium is more credible than not measuring it. Either way it is a stronger paper. Note that timing only becomes meaningful once extraction does real work — against in-memory dicts every technique finishes in microseconds, which is the second reason the mock portal matters.

## Technical Foundations Already Established

- **Five-layer HIS architecture** — a functional decomposition (Patient Administration / Clinical-EHR / Ancillary-Departmental / Administrative-Financial / Infrastructure-Integration), canonical in code as the `HISLayer` enum in `src/interop/layers.py`, with a field catalogue and a pydantic schema per layer. The fifth layer's records are audit events (compliance instrumentation), not patient records. Everything downstream imports the enum rather than re-declaring layers. The Review-1 deck's technical tiers were conceptual and are superseded by this. Not flattened into a single schema.
- **Four interoperability standards:** HL7, FHIR, DICOM, ISO/IEEE 11073 — mapped per layer in `src/interop/mapping.py`. HL7 v2 and FHIR shaping of extracted rows is implemented (`src/interop/hl7`, `fhir`, `normalise`); DICOM and 11073 remain stubs. Shaping adds nothing that was not extracted, applies pseudonymisation when the run's manifest declares it, and the export is audited for raw identifiers.
- **AXE method (Cairo University)** — LLM-based agentic extraction technique. **Related work only.** The plan to implement an AXE-inspired extraction agent was cut on 2026-09-12; AXE keeps its place in the literature survey but we do not build against it.
- **AutoScraper (EMNLP 2024)** — comparison baseline technique. Venue confirmed. Currently represented by a generic "coverage-optimised baseline" technique in the benchmark; a real implementation is Review-II work.

## Scraping Tier Decision

Tiering (as established pre-build):
- **Tier 2 — headless browser automation (Playwright):** chosen primary methodology, for credentialed portal scraping. Playwright chosen over Selenium. **Built** against the mock portal, which is deliberately a system we do not control: the adapter logs in through the form, follows links, turns pages, parses tables, and infers what each module holds from its field names. Re-targeting to a real portal is selectors, credentials and a label→field mapping — not new code.
- **Public-documentation scraping:** retained as an undocumented fallback, not the primary path.
- **Open question:** whether to prioritize login-gated portal scraping vs public-documentation scraping determines which Tier 3/4 techniques get developed further downstream. Still unresolved; should go to Dr. Manoj Kumar before Review-II implementation locks in. The mock portal is login-gated, which implicitly leans toward the first path — worth confirming rather than letting the fixture decide the methodology.

## Data Access Status

Credentialed live access was secured as the intended primary data source but is **still not usable** as of 2026-09-12 — it did not arrive before Review-I and there is no committed date. **What is expected by Review-II is a large dataset from the hospital**, with live access possible but not assumed.

Four sources, with distinct jobs: the **synthetic generator** (development, tests, reproducible benchmark runs for the paper), the **hospital dataset** (volume and realism for the benchmark), the **rough mock portal** (demonstrating the scraping mechanism), and **live HIS** (upside only). The adapter boundary absorbs all four. Nothing may *depend* on the dataset or on live access arriving; the synthetic path stays complete on its own.

**Handling requirement:** a real hospital dataset is almost certainly real patient data. Confirm de-identification, `.gitignore` the path before it lands, record provenance and the basis for sharing, and check whether ethics approval applies. Being non-compliant with the Act we benchmark against would be a serious and highly visible problem. See `PLAN.md` section 4.

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

- **Done:** repo scaffolding; the 7-rule DPDP compliance framework + policy + scored `ComplianceReport`; the benchmarking harness (`run_benchmark`) with a three-technique comparison on two axes, compliance and cost (`extraction/metering.py`); the hand-rolled HL7 / FHIR / DICOM / ISO-IEEE-11073 shapers and the five-layer mapping; three non-nested purposes and the cross-purpose matrix; role access derived from purposes × interop artefacts (`compliance/roles.py`) with a three-principle gate; the rule-based staff-guidance agent (`src/agent/`, 13 functions across three roles, gate-before-collect, groundedness-tested).
- **Slice done:** synthetic data generator (field catalogue covering four of the five layers + Faker generator); extraction adapter (`MockHISDataSource`) + technique layer.
- **Done (fixture):** the mock HIS portal (`tools/mock_portal/`, Flask) — login-gated, paginated, built as a black box the scraper does not control.
- **Done:** Tier 2 browser extraction (`src/extraction/tier2/` + `adapters/portal_his.py`) — real Playwright login, crawl-based navigation map with layers inferred from field names, techniques run unchanged, page loads metered as cost; `scripts/run_pipeline.py` runs every stage end to end.
- **Done:** HL7 v2 / FHIR shaping with pseudonymisation-on-export and an export audit (`src/interop/normalise.py`, `src/compliance/pseudonymise.py`); the pipeline now has all six stages.
- **Done:** fifth-layer audit-event fields, per-layer schemas, a synthetic export writer, the dataset adapter (`adapters/dataset_his.py`, column-map driven), and the portal adapter's label→field mapping.
- **Not started:** full per-layer pydantic schemas; a real AutoScraper baseline.
- Five runnable scripts, ~90 passing tests, a browsable result at `docs/benchmark_results/benchmark.md`. See `DEMO_GUIDE.md` and `docs/compliance/approach.md`.

## Known Loose Ends

- Login-gated vs public-documentation prioritization — pending guide input; the mock portal quietly presumes login-gated, so confirm it.
- Live HIS access — no committed date; **treated as never arriving** for planning purposes.
- Five-layer model and the modelled purposes are working assumptions, not sourced from Review-1 artifacts — accepted for now, reconfigure if real HIS access differs.
