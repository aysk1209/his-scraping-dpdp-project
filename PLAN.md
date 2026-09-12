# Build Plan — Review-II and Review-III

Working plan for the remainder of the project. Complements `CLAUDE.md` (operating
rules) and `PROJECT_CONTEXT.md` (background). Written 2026-09-12, after Review-I
cleared; revised the same day following the team's scope decisions. Revise in
place rather than appending revisions.

---

## 1. Definition of done (100%)

Fixed by the team on 2026-09-12. The project is complete when we can demonstrate,
in one continuous run:

1. **Scraping** — data pulled out of a HIS portal by real browser automation.
2. **The DPDP pipeline** — that data carried through our compliance layer, scored
   per principle, with techniques compared against each other on both compliance
   and cost.
3. **The agent** — recognises a pre-defined function from what a staff member types,
   asks for the input details that function needs, and replies with simple
   operating instructions, differentiated by staff role (administrator / nurse /
   reception) and by task type.

Deployment is **not** part of 100%.

## 2. Where the contribution lies — and what follows from it

**The DPDP compliance work is the novelty.** The research paper and the project
report are about compliance as a measurable, benchmarkable property of an
extraction technique. Everything else exists to make that contribution
demonstrable and the project complete.

**The agent is a completeness deliverable, not a research contribution.** It is
deliberately simple: pre-defined functions, recognised from user input, slot-filled
by asking for the details, answered with templated instructions. **No LLM, no
model, no training, no fine-tuning.** Build it to work and to look complete; do not
invest research effort in it, do not benchmark it, and do not let it grow.

Three consequences that this plan is built around:

- **Effort follows the contribution.** Compliance-related components carry the most
  weight in §5 and are sequenced to be finished, not merely started.
- **The agent earns its place through one property only:** its function registry is
  **DPDP-gated per role**. Reception asking how to look up a diagnosis is declined,
  because reception carries no clinical-category access under the purpose policy.
  That single check is what connects the agent to the contribution instead of
  sitting beside it. Without it the agent is decoration; with it, it is a second
  application of the same rule set.
- **The LLM extraction agent is cut.** The AXE-inspired agent-as-a-fourth-technique
  is dropped from the build (see W7). AXE remains a literature-survey citation and
  related work; it is no longer something we implement.

## 3. Quantifying the difference between techniques

The Review-I panel asked for processing time. The deeper requirement is simply **a
defensible way to quantify what separates the techniques** beyond their compliance
scores. Precise numbers matter less than a metric that holds up.

**Wall-clock time alone is a weak metric here.** It moves with the machine, the
dataset size, and network conditions, so it is not reproducible by a reader of the
paper — which is exactly what a published benchmark needs to be.

**An extraction cost profile, reported alongside the compliance score.** Implemented 2026-09-12 in `src/extraction/metering.py`; `coverage` was added to the set below as a guard rail, since without it a technique could score perfectly by pulling nothing.

| Metric | Deterministic | What it captures |
|---|---|---|
| `fields_pulled` | yes | Total field-values extracted |
| `fetches` | yes | Fetch calls — page loads once the Tier 2 adapter is in place |
| `excess_ratio` | yes | Fields pulled ÷ fields the purpose actually needs (≥ 1.0) |
| `coverage` | yes | Needed fields actually obtained ÷ fields needed — the guard rail |
| `elapsed_ms` | no | Wall-clock, median of n runs — answers the panel's literal question |

All but the last are reproducible on any machine and independent of dataset size,
so they are what the paper leans on. Wall-clock is reported as a secondary,
labelled as hardware-dependent.

**Why `excess_ratio` is the one that matters.** It is simultaneously a cost measure
and a compliance measure: fields pulled beyond what the purpose needs *are* the
data-minimisation overreach the DPDP rule penalises. Cost and compliance turn out
to be the same underlying quantity viewed from two directions, which lets the paper
make a sharper claim than "compliance is affordable" — namely that **on this axis,
the compliant technique is the cheap one, and the overreach the baseline pays for
is exactly the overreach the law objects to.**

That argument does not depend on any particular number coming out a particular way,
which is the point.

## 4. Data situation

**Expected by Review-II: a large dataset from the hospital**, and possibly live
access. This is a change from the previous "assume nothing arrives" stance, and it
reshapes what each data source is for:

| Source | Role |
|---|---|
| Synthetic generator | Development, tests, reproducible benchmark runs for the paper |
| **Hospital dataset (expected)** | Volume and realism for the compliance benchmark |
| Rough mock portal | Demonstrating the *scraping* mechanism |
| Live HIS (may not arrive) | Upside only; nothing depends on it |

The adapter boundary already absorbs this: the dataset arrives as a
`DatasetHISDataSource` (W2) beside the existing mock, and no downstream code
changes. **Do not delay other work waiting for it**, and do not design anything
that breaks if it never comes.

### Handling requirement — flagged deliberately, and enforced

*2026-09-13: `src/compliance/handling.py` turns this list into a gate the dataset
adapter applies before reading anything non-synthetic; `scripts/check_source.py`
reports and writes the mapping template; `docs/access/when-access-lands.md` is the
day-one procedure.*

A large hospital dataset is, in all likelihood, **real personal data of real
patients**. A project whose entire contribution is data-protection compliance
cannot be careless with it. Before any such dataset is used:

- Confirm it is **de-identified at source**, or de-identify it on receipt before it
  touches the repository.
- **Never commit it to git** — add the data path to `.gitignore` first, not after.
- Record its **provenance and the basis on which it was shared** with us; the report
  will need to state this, and a reviewer is entitled to ask.
- Check whether institutional ethics approval is required for handling it.

This is not bureaucratic caution — being non-compliant with the Act we are
benchmarking against would be a serious and highly visible problem.

## 5. Completion ledger

Component weights are our own judgement, recorded so that any percentage we claim
is arithmetic rather than assertion. They sum to the 100% defined in §1, and they
are weighted toward the contribution described in §2.

| # | Component | Weight | Now | At Review-II |
|---|---|---:|---:|---:|
| 1 | DPDP compliance framework (7 rules, policy, scoring, report) | 15 | 15 | 15 |
| 2 | Benchmark harness + cost profile (§3) | 12 | 12 | 12 |
| 3 | Role × task DPDP policy (gates the agent) | 7 | 7 | 7 |
| 4 | Extraction: adapter interface + three techniques | 10 | 10 | 10 |
| 5 | Tier 2 browser extraction (Playwright) | 12 | 12 | 12 |
| 6 | Synthetic data: catalogue, generator, schemas | 8 | 8 | 8 |
| 7 | Dataset adapter for the hospital export | 5 | 5 | 5 |
| 8 | Rough mock HIS portal | 5 | 5 | 5 |
| 9 | Interop normalisation wired into a run | 5 | 5 | 5 |
| 10 | Rule-based staff-guidance agent | 10 | 10 | 10 |
| 11 | End-to-end demonstration | 5 | 5 | 5 |
| 12 | Project report + manuscript (compliance-focused) | 6 | 1 | 1 |
| | **Total** | **100** | **95** | **95** |

Review-II's floor is ~75%; the build stands at 94. The residual 6 points are the
report and the manuscript — Review-III work by definition. The residual 11 points to Review-III are almost entirely the report and
the manuscript — which is exactly what Review-III is for.

*Updated 2026-09-12: W3 complete, component 2 closed — 41 to 45. W5 complete, component 3 closed — 45 to 52. W4 complete, component 10 at 8 of 10 — 52 to 60; the last two points are the navigation-map pages filled in once the portal exists. W1 complete, component 8 closed — 60 to 65. W2 (Tier 2) at 10 of 12 and W9 rough at 4 of 5, agent pages now filled — 65 to 81. **The 75% floor is crossed with a working end-to-end chain.** Interop shaping + export audit wired in, components 9 and 11 closed — 81 to 85. 2026-09-13: fifth-layer fields + schemas, dataset adapter against a synthetic export, label→field mapping — components 5, 6, 7 closed — 85 to 94. **Everything not requiring live access is built; the remaining points are the report and manuscript.** 2026-09-13 later: report outline with chapter→artefact mapping (`docs/report/outline.md`) and the DPDP section mapping drafted for verification — 94 to 95.*

## 6. Workstreams

Acceptance criteria are written so that "done" is observable rather than a matter
of opinion.

### W1 — Rough mock HIS portal *(component 8)* — **DONE 2026-09-12**

`tools/mock_portal/`, Flask 3. Built to two constraints the team set after the
original spec below: **assume we do not control it** (no JSON endpoint, no scraper
hooks, portal vocabulary in URLs, a per-session login token, `robots.txt`
disallowing all — the adapter must earn its data as it would against a real
system) and **it may have to serve a large dataset** (records snapshotted from the
`HISDataSource` once at start-up, pagination real, `--records 5000` gives 200
pages per module). Fields on the list page are a subset; the rest are only on the
detail page. It serves the hospital dataset unchanged when that arrives.
`python -m tools.mock_portal`; account `frontdesk / letmein`. Tests drive it
through Flask's test client; it has also been driven over real HTTP.

Original spec, kept for the record. **Deliberately minimal.** Not a simulation of a
hospital system — just enough structure for a browser to log into, navigate, and
scrape. A small Flask app:

- Login page and session cookie.
- A handful of pages mapped to the five layers.
- A paginated patient list and a per-patient detail page.
- At least one field reachable **only** via the detail page, so that techniques
  differ in `pages_fetched` and the cost profile has something to measure.

Resist adding realism. Its only jobs are to exercise the browser layer and to
produce cost differences.

**Done when:** one command serves a portal a human can log into and browse.

### W2 — Data sources: Tier 2 scraping and the hospital dataset *(components 5, 7)* — **Tier 2 DONE 2026-09-12; dataset adapter pending the export's format**

**Dataset adapter: DONE 2026-09-13**, against a synthetic export of the right
shape. `scripts/generate_dataset.py` writes one CSV per layer plus a manifest into
`data/` (git-ignored, so the rule is in force before any real data exists).
`adapters/dataset_his.py` reads any directory of CSV/Excel files, classifies each
by its *columns* via `infer_layer` — the same classification the crawler applies
to a portal module — and takes a `column_map` for hospital-named headers. A file
called `PatientMaster_2026.csv` with columns "Patient ID", "DOB", "Gender" is
served correctly given the map and nothing else; unknown columns are dropped and
reported, never carried through. The real export is that map.

**Label→field mapping: DONE 2026-09-13.** The fixture renders display labels on
request (`labels=`); `PortalHISDataSource(field_aliases=...)` maps them back as
headers are read, so discovery, inference and fetching all see catalogue names.
Tested both ways: without the map the labelled module cannot be classified; with
it, everything downstream is unchanged.

Tier 2 is built exactly as the black-box rule demands. `tier2/browser.py` logs in
through the form (the browser carries the token and cookie), parses tables by
header text, opens records by the link in the actions column, follows "Next" until
it stops, and counts every page load. `tier2/navigation.py` crawls from the home
page and **infers each module's HIS layer from the field names it finds**, matched
against the catalogue — the URL says `/m/registration/`, the scraper concludes
"patient administration" from `mrn`, `full_name`, `date_of_birth`. That is the
heterogeneity answer as code. `adapters/portal_his.py` puts it behind
`HISDataSource`; the three techniques run against it unchanged (tested). Detail
pages are opened only when a requested field is absent from the list table, so
over-asking costs real page loads, and `extraction/metering.py` now reports them:
on a 30-record portal the compliant technique loads ~88 pages to the baseline's
~336 at identical coverage. Remaining 2 points: a label→field mapping for a real
portal whose headers are display labels, which belongs in the adapter.

Original specification, kept for the record. Two adapters behind the existing
`HISDataSource` interface.

**Tier 2 (Playwright)** — fills `src/extraction/tier2/` and adds
`adapters/portal_his.py`: browser session, login, navigation, list and detail
parsing, pagination. Also emits a **navigation map** — layers → pages → fields —
which W4 reuses.

**Dataset adapter** — `adapters/dataset_his.py`, reading the hospital export
(CSV/Excel via pandas, most likely) and mapping its columns onto the field
catalogue's layers and DPDP categories. Write it against the synthetic generator's
output shape now, so that when the real export lands the work is a column mapping
rather than new code. See §4 before pointing it at real data.

**Done when:** all three existing techniques run unchanged against both adapters
and produce the same shape of output they produce against `MockHISDataSource`.
Unchanged is the point — it is what proves the adapter boundary was designed right,
and it is the demonstration of the answer to the panel's heterogeneity doubt.

### W3 — Cost profile in the benchmark *(component 2)* — **DONE 2026-09-12**

Implements §3. `extraction/metering.py` meters every technique identically at the
adapter boundary (`MeteredSource`), so no technique cooperates in its own
measurement. `TechniqueScore.cost` carries fetches, records, fields pulled,
coverage, excess ratio and wall-clock; both renderers show a cost block; and
`_takeaway()` now states the compliance-versus-cost relationship from the measured
numbers instead of asserting that the gap is "not coverage or speed".

`coverage` was added beyond the original design as a guard rail — without it a
technique could score perfectly by pulling nothing, which would make the whole
cost axis gameable.

**Result on the synthetic workload (four tasks, five layers):** the compliant
technique pulls exactly what each purpose requires (excess 1.00, coverage 1.00);
the baseline pulls 6.53x at the same coverage; the morality model pulls 0.90x at
coverage 0.90 — cheaper because it refused a name and a phone number the
appointment-reminder task lawfully needed. Compliance and cost move together for
the baseline; for the morality model, low cost *is* the failure. Both axes are
needed to tell the story.

### W4 — Staff-guidance agent *(component 10)* — **DONE 2026-09-12** (8 of 10)

Built as specified below. `src/agent/functions.py` holds 13 functions across the
three roles; `session.py` is the state machine (recognise → gate → collect →
instruct); `guidance.py` renders the answer with its own compliance footer. The
gate runs **before** any input is collected. `scripts/ask_agent.py` plays four
scenes or runs `--interactive`. Tests assert groundedness against the artefact
vocabulary and the field catalogue, so no step can name something the HIS model
lacks. The remaining 2 points are the `page` on each step, which the Tier 2
navigation map fills in via `Session(role, navigation=...)` — the seam exists and
is tested; only the portal is missing.

Original specification, kept for the record — rule-based, deterministic, no LLM.
Four parts:

1. **Function registry** — pre-defined staff functions, each declaring: an id and
   label, the roles permitted to perform it, the HIS layers and field categories it
   touches, its required inputs, and its instruction-step template. Roughly:
   - reception — register a patient, book or reschedule an appointment, check in an
     arrival, verify insurance eligibility;
   - nurse — record vitals, view the active medication list, request a lab, prepare
     a discharge checklist;
   - administrator — allocate a bed, generate a bill, reconcile a claim, run a census.
2. **Recognition** — match user input against function labels and a synonym list by
   token overlap; ask the user to choose when the match is ambiguous. No new
   dependency needed, and nothing here can hallucinate.
3. **Slot filling** — ask for each required input in turn until the function's
   inputs are satisfied.
4. **DPDP gate** — before returning anything, check role × function against the
   role policy (W5). If the role is not permitted, **decline and cite the rule**.

Output is a `StaffGuidance` artifact: numbered steps, the HIS layer and portal page
each step touches, and a DPDP note wherever a step touches a sensitive category.
Steps reference the navigation map from W2, so the instructions correspond to pages
that actually exist.

**Done when:** the same request from three different roles yields three
appropriately different answers, and an out-of-role request is declined with the
rule cited. **That decline is the most demonstrable moment in the project** — it is
where the compliance layer visibly does work outside the benchmark. Build toward it
deliberately.

Being rule-based makes the whole thing unit-testable with no network and no API
key, which also means it cannot fail in the review room.

### W5 — Role × task DPDP policy *(component 3)* — **DONE 2026-09-12**

`src/compliance/roles.py`. Role access is **derived, not listed**, from two
independent sources: the purposes a role acts under (nurse → care; administrator →
billing + registration; reception → registration + billing for eligibility) and the
interoperability artefacts it handles — HL7 v2 message types, FHIR resource types,
DICOM, ISO/IEEE 11073 (team decision: assume access follows the standards). The
effective scope is the intersection; either source alone over-grants, and tests
show both cases.

`authorise(role, purpose, artefacts)` is the gate W4 will call: three checks, three
principles — PL-01 (lawful purpose for this role), DM-01 (every category necessary
for it), SS-01 (role handles these artefacts). Every decline names its rule. A
third purpose, `patient_registration`, was added for reception, pairwise non-nested
with the other two. `fhir:Claim` and `dicom:Study` are granted to no role by design.
The consistency test also corrected a gap in `interop/mapping.py` — HL7 v2 `DFT`
and `BAR` carry billing, so the Administrative/Financial layer now lists HL7 v2.

`scripts/show_role_access.py` is the visible artifact.

### W6 — Widen the compliance surface *(components 6, 9)*

**Second and third processing purposes: DONE 2026-09-12.** `billing_settlement` and
`patient_registration` are modelled alongside `care_coordination`, pairwise **non-nested** — neither scope
contains the other, so purposes are not ranked strict-to-lax and "out of scope"
keeps its proper meaning. Three rules now vary with the purpose (`DM-01` allowed
categories, `SL-01` retention ceiling, `SS-01` whether pseudonymisation is
required at all). `compliance/purpose_matrix.py` scores one unchanged extraction
against every purpose, and `scripts/compare_purposes.py` shows the failure running
in both directions. PL-01 gained a real compatibility assessment for declared
onward uses, which was unbuildable with one purpose.

*Preserve the non-nesting when adding a third purpose.* A purpose whose scope is a
superset of an existing one collapses the distinction the demonstration rests on —
which is why claims adjudication is deliberately left unmodelled.

**Interop normalisation: DONE 2026-09-12.** `src/interop/hl7` and `fhir` are
implemented (hand-rolled, per convention); `interop/normalise.py` shapes a run's
rows per the layer↔standard matrix, applies `compliance/pseudonymise.py` when the
manifest declares it, and **audits the export** for raw direct identifiers — the
compliant technique's export leaks none, the baseline's leaks all. That turns
SS-01's pseudonymisation check from a declaration into a verified property of the
output. Shaping is tested to add nothing that was not extracted. DICOM and 11073
stay stubs and are reported as skipped.

**Schemas and the fifth layer: DONE 2026-09-13** (team decision: use synthetic
structure now rather than wait). `data_synthetic/schemas` derives one pydantic model
per layer from the catalogue, so the two cannot disagree; the Integration layer
gets an audit-event record set (`audit_event_id`, `event_timestamp`, `actor_role`,
`action`, `source_system`, `subject_mrn`) — compliance instrumentation, not a
patient record, and not identifier-free, which is why it is worth modelling. It
shapes to FHIR `AuditEvent`; the artefact is granted to no role. If the hospital
dataset shows a different structure, the catalogue is the one place to change.

### W7 — Cut: LLM extraction agent

Dropped per §2. AXE stays in the literature survey as related work.

Consequence to action: the `anthropic` dependency in `requirements.txt` becomes
unused and should be removed once this is confirmed.

### W8 — Real baseline technique — **DROPPED 2026-09-13**

The panel accepts the hand-written `unconstrained` baseline: they agree that the
majority of real systems have very little compliance, so a coverage-optimised
scraper with no manifest is a fair stand-in and a literature-faithful AutoScraper
implementation adds nothing the argument needs. AutoScraper stays a citation in the
survey. The effort goes to the report instead.

The middle technique is renamed and redesigned at the same time: the **morality
model** (`techniques/morality.py`) judges privacy by instinct — what a general AI
model would consider private from a field's name — rather than by purpose. It is
deliberately not DPDP-compliant. Its intuition table is explicit so the comparison
stays fair, and the benchmark gained an appointment-reminder task where instinct
and law disagree, so the model's second failure mode (refusing lawfully needed
data) is visible as coverage < 1.

### W9 — End-to-end demonstration *(component 11)* — **DONE (rough) 2026-09-12**

`scripts/run_pipeline.py` runs six stages in one command, ~30–40 s: serve the
portal; log in and discover; benchmark the three techniques with real page loads;
normalise to HL7 v2 / FHIR with identifiers pseudonymised and the export audited;
re-judge one pull under every purpose; answer one question per role with steps on
the discovered pages and decline the out-of-role one. Every stage of the original
spec is now in the chain.

Original specification: one command: start the portal, log in, scrape, run every
technique, normalise, score, print the ranked table with compliance and cost, then
run the agent through one task per role and show the out-of-role decline.

Build it **early and rough**, then thicken. A complete chain demonstrates more than
a polished fragment.

## 7. Sequence

Close the chain first; thicken it second.

| Order | Work | Rationale |
|---|---|---|
| 1 | W3 | Small and self-contained; actions the panel's feedback immediately |
| 2 | W1 | Unblocks W2; nothing else moves without it |
| 3 | W2 (Tier 2) | The spine — and produces the navigation map W4 needs |
| 4 | W9 (rough) | Chain closed end to end, early |
| 5 | W5 | Compliance work, and must precede W4's decline behaviour |
| 6 | W4 | The completeness deliverable; keep it small |
| 7 | W6 | Contribution work — strengthens the rule set |
| 8 | W2 (dataset adapter), W3 re-run | Whenever the hospital export lands |
| 9 | W9 polish, screenshots | Review-II presentation state |
| — | report, manuscript | Review-III |

## 8. Open decisions and external requirements

Roughly in the order they block work.

1. ~~Sign-off on the rough mock portal (W1) and on Flask~~ — **approved and built 2026-09-12.**
2. **`playwright install chromium`** on whichever machine demos — roughly 150 MB of
   browser binaries that `pip install` does not fetch. Done on the development machine
   2026-09-12; still needed on any other machine that presents.
3. **Hospital dataset: format, size, and de-identification status** (§4). The
   de-identification question should be settled *before* the data arrives, not after.
4. ~~Confirm W7~~ — **done**; the LLM agent is dropped and `anthropic` is removed from `requirements.txt`.
5. ~~Review-II date~~ — the team tracks dates and timeline; the plan is ordered, not
   calendared, and that is by design.
6. **Guide input — login-gated versus public-documentation priority.** Formally still
   open; W1 quietly settles it in favour of login-gated. Worth confirming with
   Dr. Manoj Kumar before it does.
7. **Staff function list (W4).** Our reconstruction of hospital workflow, not sourced
   from a real hospital. Wrong task names are visible to a clinical reviewer in a way
   wrong code is not — worth a short sanity check with anyone with ward experience.

## 9. Known risks

| Risk | Consequence | Mitigation |
|---|---|---|
| ~~Hand-written baseline reads as a strawman~~ | Closed: the panel accepts the baseline (2026-09-13) | — |
| Real patient data mishandled | Serious, and acutely embarrassing for this project specifically | §4 — settle de-identification before arrival |
| Hospital dataset never arrives | Benchmark rests on synthetic data only | Nothing depends on it; synthetic path stays complete |
| Portal is unrealistically clean | Robustness claims overstated | State the limitation in the deck; it demonstrates the mechanism, not robustness |
| Agent scope creeps | Effort drains from the contribution | §2 — it is a completeness deliverable; keep it rule-based and small |
| Wall-clock timings wobble between runs | Benchmark looks unreliable | §3 — deterministic metrics lead, wall-clock is secondary |
