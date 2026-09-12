# Build Plan — Review-II and Review-III

Working plan for the remainder of the project. Complements `CLAUDE.md` (operating
rules) and `PROJECT_CONTEXT.md` (background). Written 2026-09-12, after Review-I
cleared. Revise in place rather than appending revisions.

---

## 1. Definition of done (100%)

Fixed by the team on 2026-09-12. The project is complete when we can demonstrate,
in one continuous run:

1. **Scraping** — data pulled out of a HIS portal by real browser automation.
2. **The DPDP pipeline** — that data carried through our compliance layer, scored
   per principle, with techniques compared against each other.
3. **The agent** — an agent that demonstrably understands the structure of the HIS
   and returns **simple operating instructions for hospital staff**, differentiated
   by **role** (administrator, nurse, receptionist) and by **the type of task being
   performed**.

Deployment is explicitly **not** part of 100%. Live hospital data access is
explicitly **not** part of 100% — see §3.

### What this changed

Part 3 was previously framed as the project's long-term motivation, "beyond this
project's scope". It is now inside the graded scope, and `CLAUDE.md` /
`PROJECT_CONTEXT.md` have been corrected accordingly. Two consequences follow:

- The agent stops being an optional fourth benchmark technique and becomes a
  **headline deliverable**. Work on it is re-prioritised upward.
- The compliance layer acquires a **second job**. Until now it scored extraction
  runs after the fact. It now also *gates* what the agent may instruct a given role
  to do — see §2.

## 2. The architectural insight this plan is built on

Role-based staff guidance and DPDP purpose limitation are the **same mechanism**.

A receptionist asking "how do I look up this patient's diagnosis?" should not
receive instructions, because reception's role does not carry clinical-category
access under the `care_coordination` purpose. The agent declines, and cites the
rule. A nurse asking the same question is guided through it.

This matters beyond a demo flourish. It is what makes the two halves of the
project one project rather than two bolted together:

```
  Tier 2 scraper  --discovers-->  HIS structure  --grounds-->  Agent guidance
        |                          (layers, fields,                  ^
        |                           navigation map)                  |
        v                                 |                          |
  Extraction runs --scored by-->  DPDP compliance layer --gates------+
                                  (7 rules + purpose policy
                                   + role x task policy)
```

The scraper discovers the architecture; that structure becomes the agent's
knowledge of the HIS; the compliance layer both scores the extraction and
constrains the guidance. One rule set, two applications. This is also the
strongest available answer to the Review-1 panel's heterogeneity doubt: point the
scraper at a different HIS and the agent's understanding re-derives itself.

## 3. Standing constraint: no live HIS data

Credentialed access has now missed a full review cycle with no committed date.
**Plan as though it never arrives.** Nothing in §1 depends on it.

The substitute is a **mock HIS portal we author ourselves** (W1): a login-gated web
application serving synthetic records as HTML. Playwright scrapes it for real —
real browser, real authentication, real DOM, real latency. It is a test fixture,
not a product. `LiveHISDataSource` stays a stub; if access ever lands, it becomes a
matter of selectors and credentials rather than unwritten code.

**Named limitation, to state in the deck rather than have found:** a self-authored
portal is friendlier than a real one — clean markup, no bot defences, no vendor
quirks. It validates that the pipeline works, not that it is robust in the wild.

## 4. Completion ledger

Component weights are our own judgement, recorded so that any percentage we claim
is arithmetic rather than assertion. They sum to the 100% defined in §1.

| # | Component | Weight | Now | At Review-II |
|---|---|---:|---:|---:|
| 1 | DPDP compliance framework (7 rules, policy, scoring, report) | 15 | 15 | 15 |
| 2 | Synthetic data: catalogue, generator, per-layer schemas | 10 | 6 | 9 |
| 3 | Extraction: adapter interface + three techniques | 10 | 10 | 10 |
| 4 | Mock HIS portal fixture | 8 | 0 | 8 |
| 5 | Tier 2 browser extraction (Playwright) | 12 | 0 | 12 |
| 6 | Benchmark harness, including per-technique timing | 10 | 8 | 10 |
| 7 | Interop normalisation wired into a live run | 5 | 2 | 5 |
| 8 | Agent A — extraction agent as a scored technique | 8 | 0 | 2 |
| 9 | Agent B — role- and task-aware staff guidance | 12 | 0 | 7 |
| 10 | Role x task compliance policy | 5 | 0 | 5 |
| 11 | End-to-end pipeline demonstration | 5 | 0 | 5 |
| | **Total** | **100** | **41** | **88** |

Review-II's floor is ~75%. The plan below targets 88 so that slippage on any one
workstream still clears it. Treat the margin as insurance, not as spare capacity.

## 5. Workstreams

Acceptance criteria are written so that "done" is observable, not a matter of
opinion.

### W1 — Mock HIS portal *(component 4)*

A small Flask application serving the **existing** synthetic generator as HTML, so
portal data and `MockHISDataSource` data agree by construction.

- Login page, session cookie, logout.
- Module navigation mirroring the five layers.
- Paginated patient list; per-patient detail page; labs view; billing view.
- At least one field reachable **only** via detail-page navigation — this is what
  makes different techniques cost different amounts, and without it the timing
  numbers in W3 are meaningless.
- Modest artificial latency, so timing is dominated by navigation rather than noise.

**Done when:** one command serves a portal a human can log into and browse, and no
real hospital system is involved.

### W2 — Tier 2 Playwright extraction *(component 5)*

Fills `src/extraction/tier2/` and adds `src/extraction/adapters/portal_his.py`
implementing `HISDataSource` over it: browser session, login, navigation, list and
detail parsing, pagination.

Additionally, and importantly for W5: emit a **navigation map artifact** — the
portal structure the crawler discovered, as layers to pages to fields. This is the
artifact that later grounds the agent's understanding of the HIS.

**Done when:** all three existing techniques run unchanged against
`PortalHISDataSource` and produce the same shape of output they produce against
`MockHISDataSource`. Unchanged is the point — it is the proof the adapter boundary
was designed correctly, and the demonstration of the heterogeneity answer.

### W3 — Per-technique processing time *(component 6)*

The Review-I panel's suggestion. Extend `TechniqueScore` with `mean_elapsed_ms`,
`ms_per_record` and `page_fetches`; add a time column to `render_table` and
`render_markdown`; rewrite `BenchmarkResult._takeaway()` to state the trade-off
rather than dismissing speed as it currently does.

Report the **median of n>=3 runs**, not a single sample. Report timings measured
against the portal; in-memory timings are microsecond noise and should be labelled
as such if shown at all.

**Do not predict the result.** The compliance-aware technique will most likely be
*faster*, since it fetches fewer pages — but manifest construction adds overhead,
and the honest move is to measure and report whichever way it falls. Quantifying a
compliance premium is more credible than not measuring one.

**Done when:** the headline table carries compliance **and** cost, and the takeaway
line states the trade-off in measured numbers.

### W4 — Agent A: extraction agent *(component 8, deliberately deprioritised)*

AXE-inspired: Claude via the Anthropic API, given tools to inspect layers and
fields, proposing an `ExtractionTask` plus compliance manifest from a
natural-language request. It then enters the benchmark as a fourth technique,
scored by the same seven rules.

This serves the **paper** — an LLM technique scored on identical terms is a genuine
contribution. It does **not** serve the §1 demonstration. Scaffold it for
Review-II; complete it for Review-III.

### W5 — Agent B: role- and task-aware staff guidance *(component 9 — the headline)*

The deliverable §1.3 names. Given a **staff role** and a **task**, return short,
numbered operating instructions for the HIS.

New types:

- `StaffRole` — `RECEPTION`, `NURSE`, `ADMINISTRATOR` (extensible; three is enough
  to demonstrate differentiation).
- `TaskType` — grounded in the five layers, roughly:
  - reception: register a patient, book or reschedule an appointment, check in an
    arrival, verify insurance eligibility;
  - nurse: record vitals, view the active medication list, request a lab, prepare a
    discharge checklist;
  - administrator: allocate a bed, generate a bill, reconcile a claim, run a census.
- `StaffGuidance` — the returned artifact: numbered steps, the HIS layer and portal
  page each step touches, the data categories involved, and a DPDP note wherever a
  step touches a sensitive category.

The agent's understanding of the HIS comes from real artifacts, not from prose we
hand it: the `HISLayer` enum, the field catalogue, the interop mappings, and the
navigation map W2 discovered. Guidance is therefore **checkable** — see W5-eval.

**W5-eval (what makes this research rather than a chatbot).** Two measurable
properties, both reusing machinery we already have:

- **Groundedness** — the proportion of generated steps that reference a page or
  field actually present in the discovered navigation map. Catches hallucinated
  instructions, which in a hospital setting are the failure mode that matters.
- **Guidance compliance** — the proportion of guidance that stays inside the
  requesting role's DPDP-allowed categories, scored by the existing rule set.

**Done when:** the same task asked by three different roles yields three
appropriately different answers, and an out-of-role request is declined with the
rule cited. That decline is the single most demonstrable moment in the project —
build toward it deliberately.

### W6 — Role x task compliance policy *(component 10)*

Extends `src/compliance/policy.py` with a role-aware envelope: which field
categories and layers each `StaffRole` may be instructed to access, for a given
task and purpose. Declarative table, same as `PURPOSE_POLICY` — the "what is
allowed" stays inspectable in one place, which is itself an artifact for the paper.

This is what W5's decline behaviour is enforced by. Build it before W5 finishes.

### W7 — Widen synthetic data *(component 2)*

Per-layer pydantic schemas; fields for the fifth layer; and **a second processing
purpose** (`billing_settlement` is the natural candidate). The second purpose is
cheap and matters more than it looks: with only one purpose modelled, the
purpose-limitation rule has nothing to discriminate between, which quietly weakens
one of the seven.

### W8 — Real baseline technique *(Review-III)*

An AutoScraper-style learn-by-example scraper implemented against the portal,
replacing the hand-written `unconstrained` stand-in.

**Risk being managed here:** the current baseline is written by us, which makes it a
strawman an examiner can push on at Review-III. Scheduling it late is acceptable;
leaving it undone is not.

### W9 — End-to-end pipeline demonstration *(component 11)*

`scripts/run_pipeline.py` — one command: start the portal, log in, run every
technique, normalise to FHIR/HL7, score, write the ranked table with timings, then
ask the agent for staff guidance on a task per role and show the out-of-role
decline. This is what gets demoed and screenshotted.

Build it **early and rough**, then thicken. Review-II rewards a complete chain over
a polished fragment.

## 6. Sequence

Close the chain first; thicken it second.

| Order | Work | Rationale |
|---|---|---|
| 1 | W3 (against current mock) | Small, self-contained, visibly actions the panel's feedback even if everything else slips |
| 2 | W1 | Unblocks W2 and W5; nothing else moves without it |
| 3 | W2 | The spine — and produces the navigation map W5 needs |
| 4 | W9 (rough) | Chain closed end to end, early |
| 5 | W6 | Must precede W5's decline behaviour |
| 6 | W5 | The headline deliverable |
| 7 | W7, W3 re-run against portal | Real timing numbers; stronger rule discrimination |
| 8 | W4 scaffold, W9 polish | Review-II presentation state |
| — | W8, W4 complete, report, manuscript | Review-III |

## 7. Open decisions and external requirements

Items we cannot resolve alone, roughly in the order they block work.

1. **Sign-off on the mock portal (W1).** Load-bearing for everything downstream.
2. **New dependency: Flask.** `CLAUDE.md` requires confirmation before adding one.
   Flask over FastAPI here — it is a fixture, and synchronous with no ASGI server is
   less machinery to explain.
3. **Anthropic API key** for W4/W5, plus a decision on live-versus-cached for the
   review demo. Recommendation: cached transcripts, live as backup. A network
   failure in the review room should not cost us the demo.
4. **`playwright install chromium`** on whichever machine presents — roughly 150 MB
   of browser binaries that `pip install` does not fetch.
5. **Review-II date.** Not yet recorded anywhere; the sequence above is ordered but
   not calendared.
6. **Guide input — login-gated versus public-documentation priority.** Formally
   still open. The mock portal presumes login-gated, so W1 quietly settles a
   methodology question. Confirm with Dr. Manoj Kumar before it does.
7. **Staff task list.** The `TaskType` set in W5 is our reconstruction of hospital
   workflow, not sourced from a real hospital. Worth a sanity check with anyone with
   ward-level experience; wrong task names would be visible to a clinical reviewer.

## 8. Known risks

| Risk | Consequence | Mitigation |
|---|---|---|
| Live access never arrives | None to the plan | Already assumed; §3 |
| Self-authored portal is unrealistically clean | Robustness claims overstated | State the limitation in the deck (§3) |
| Hand-written baseline reads as a strawman | Examiner pushback at Review-III | W8 |
| Agent hallucinates HIS steps | Guidance is unsafe and indefensible | W5-eval groundedness metric; ground in the discovered navigation map, not prose |
| Agent demo depends on a live API call | Demo fails in the room | Cached transcripts (§7.3) |
| W5 slips | The §1.3 deliverable is the one that cannot be cut | Sequenced before polish work; W4 sacrificed first if time is short |
