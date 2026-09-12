# Review-II — presentation flow, executables, and the code behind them

A presenter's script: what to run, in what order, what to say at each point,
and which Python files and functions each moment rests on. The deck
(`Review-II.pptx`, built by `tools/build_review_deck.py` on the institution's
Review-2 template) carries the fixed slide sequence; this document is about the
*live* part and the explanation.

**From the template:** Review-II is 30.09.2026, 40 marks (40%), 12–15 minutes,
focus "75% work completion & implementation progress". Marks: technical depth 15,
implementation quality 15, results analysis 5, presentation 3, Q&A 2. The two
15-mark items are exactly what the live run and the code walk-through show, so
budget **6–7 minutes live** out of the slot and keep the slides brisk. The
literature review must list **at least 15 papers**; we have 12 — three to add
before the day.

---

## 0. Before the room (15 minutes, once)

| Do | Why |
|---|---|
| `python -m playwright install chromium` on the demo machine | Browser binaries are not in `pip install`; first run downloads ~150 MB |
| `python scripts/run_pipeline.py` once, discard output | Warms Chromium and the Python imports; the first run is slowest |
| Open in browser tabs: `docs/benchmark_results/benchmark-portal.md`, `care-pull--compliance-aware--purpose-matrix.md`, `billing-pull--compliance-aware--purpose-matrix.md`, `navigation-map.json` | These are the same tables the live run prints — the fallback if anything fails |
| Terminal: dark theme, font ≥ 16 pt, window at least 100 columns wide | The benchmark tables are wide |
| `python scripts/run_pipeline.py --records 20 --page-size 10` as the live command | ~30 s; enough pages to show pagination, not enough to bore |

If the browser cannot launch in the room: `python scripts/run_benchmark.py` runs
the same three techniques in memory in two seconds, and the portal artefacts in
the open tabs carry the real-page-load numbers. Say so plainly and move on.

---

## 1. The flow

Six beats. Slides carry beats 1, 2 and 6 (template slides 4, 7 and 12); the
terminal carries 3, 4 and 5, with template slides 8–11 as the fallback tables.

### Beat 1 — the thesis (slide, 45 s)

> DPDP compliance can be a **measured property of a scraping technique**, not a
> paragraph in a report. We built the measurement, and everything else in this
> project exists to demonstrate it.

Name the three legs the 100% was defined as: scrape → compliance pipeline →
staff assistant. Say that all three run, end to end, in one command, and that
you are about to run it.

### Beat 2 — the working blocks (slide, 60 s)

One diagram: **Sources → Acquisition → Semantics → Extraction → {Scoring, Export,
Guidance} ← Policy.** The sentence that matters:

> One policy table is read by three different blocks: it scores the extraction,
> it gates what leaves as HL7/FHIR, and it gates what the assistant may tell a
> member of staff. That is why this is one project and not two.

### Beat 3 — the pipeline, live (terminal, ~3 min)

```
python scripts/run_pipeline.py --records 20 --page-size 10
```

Talk over it stage by stage. Each stage has exactly one thing to point at.

**[1] PORTAL.** "A login-gated hospital portal has just started on this laptop.
We wrote it — but as a system we *don't control*: a login form, a session cookie,
HTML tables, a robots.txt that says no. No API, no hooks. The scraper only has a
username and a password."

**[2] DISCOVER.** Point at the `inferred layer` column.
"The browser logged in and crawled it. It was never told the layout. The URL says
`/m/registration/`; the scraper concluded *patient administration* from the field
names it found — mrn, full name, date of birth. Point it at a portal with
different names and this map re-derives itself." *(This is the Review-1
heterogeneity doubt, answered.)*

**[3] BENCHMARK.** Point at the `score` column, then the `pages` column.
"Three scraping methods ran against that portal — the same code that ran against
in-memory data, unchanged. Same seven DPDP rules. Ours: 1.0. The baseline, which
grabs everything: 0.13. In the middle, the *morality model* — it decides what's
private by instinct, the way a general AI model would from a column name. It
scores 0.48." Then cost: "The baseline loaded four to five times as many pages for
the same coverage. That surplus is exactly what the minimisation rule penalises —
compliance and cost move together. And look at coverage: the morality model got
only 90% of what the tasks required, because it refused a name and a phone number
that an appointment reminder lawfully needs. Privacy by instinct fails in both
directions." *(This is the Review-I processing-time request, answered with a
number that reproduces on any machine.)*

**[4] NORMALISE.** Point at the two `audit:` lines.
"The compliant run's data went out as HL7 v2 and FHIR with identifiers replaced by
tokens. Then we *audited* the export for the real identifiers: none. The
baseline's export: all of them. The compliant method *claimed* pseudonymisation in
its manifest; we checked the output instead of believing it." Show the `PID|…PSN-…`
line.

**[5] PURPOSE.** Point at the two scores.
"Same records, same paperwork, same rules — 1.0 for care coordination, 0.83 for
billing. Nothing changed but what the data was *for*. Compliance is a property of
a pull and its purpose together."

**[6] ASSIST.** Let the receptionist's refusal come up last.
"A rule-based assistant — no model, no training — answers a question per role,
and each step is stamped with the page the crawler found a minute ago. Then the
receptionist asks for a diagnosis and is refused, *before* being asked for a
single detail, with the rule named. That refusal comes from the same policy table
that scored stage 3." *(This is the Review-1 "how is the agent trained" doubt:
it isn't.)*

### Beat 4 — both directions (terminal, 20 s)

```
python scripts/compare_purposes.py
```

Only if there is time; otherwise the open tab. The point: care may see clinical
data and not billing data; billing may see billing data and not clinical data.
Neither purpose is "stricter". Out of scope means *not necessary for this
purpose*, not *more sensitive*.

### Beat 5 — hand the keyboard over (terminal, optional, 60 s)

```
python scripts/ask_agent.py --interactive
```

Offer a panel member the keyboard: pick a role, type a request. Whatever they
type, the outcome is one of: guidance with pages, a clarifying question, a
refusal with the rule cited, or "I can help with…" listing only that role's
functions. Nothing it can say is unsafe, because it can only say what is in the
registry and only after the gate. If they type something rude, it says it didn't
recognise it.

### Beat 6 — results, limitations, next (slide, 60 s)

The `benchmark-portal.md` table on the slide. Then the limitations, said before
anyone asks: the portal is cleaner than a real vendor system, so this demonstrates
the mechanism, not robustness; the hospital dataset is not in yet, and the adapter
that takes it is built and tested against a synthetic export of the same shape.
Then next: the report, the manuscript, the real data when it lands.

---

## 2. Anticipated questions, and where the answer is

| They ask | Point at | Because |
|---|---|---|
| "How does this cope with different hospital systems?" | Stage [2], the `inferred layer` column | Structure is discovered by crawling and classified from field names; the layer inference is `data_synthetic.catalogue.infer_layer` and is shared by the portal crawler and the dataset adapter |
| "How is the agent trained?" | Stage [6] | It isn't. `src/agent/functions.py` is a fixed registry; recognition is token overlap; the gate is `compliance.roles.authorise` |
| "Where's the processing time?" | Stage [3], `pages` and `ms` columns | `extraction/metering.py` counts real page loads; wall-clock is shown but labelled hardware-dependent |
| "Isn't the baseline a strawman?" | — | The panel has accepted that most real systems sit at the baseline; the model in between is the morality model |
| "What is the morality model, exactly?" | `FEELS_PRIVATE` in `techniques/morality.py` | An explicit table of what feels private from a field name; deliberately not DPDP; wrong in both directions |
| "Why is compliance cheaper here — isn't that suspicious?" | `excess_ratio` | Fields pulled beyond the purpose are both the cost and the overreach the minimisation rule penalises — one quantity, two readings; the morality model is cheaper still and that cheapness *is* its failure (coverage 0.90) |
| "What happens when you get the real data?" | `extraction/adapters/dataset_his.py` | Drop it in `data/`, write a `column_map`, run the same pipeline; tested with hospital-named columns |
| "And a real portal?" | `PortalHISDataSource(field_aliases=…)` | Display labels map to fields as headers are read; tested against the fixture in label mode |
| "Is the pseudonymisation real or declared?" | Stage [4], the audit line | `interop.normalise.audit` searches the emitted artefacts for raw identifiers |
| "Which DPDP sections?" | `docs/compliance/dpdp-provision-map.md` | Rules cite principles; sections are pinned in the report, deliberately not in code |

---

## 3. The executables, one line each

| Script | Shows | Time |
|---|---|---|
| `scripts/run_pipeline.py` | **The whole chain**: portal → discover → benchmark → normalise + audit → purpose → assistant | 30–40 s |
| `scripts/run_benchmark.py` | The three techniques on in-memory data, compliance × cost | 2 s |
| `scripts/compare_purposes.py` | One pull judged under every purpose, both directions, plus the retention case | 2 s |
| `scripts/show_role_access.py` | Each role's derived scope; one request through all three roles | 1 s |
| `scripts/ask_agent.py [--interactive]` | The assistant: four scripted scenes, or live typing | 1 s |
| `scripts/run_synthetic_extraction.py` | One method, three configurations — why a score moves | 1 s |
| `scripts/score_extraction_run.py` | The seven rules on hand-built runs, no data involved | 1 s |
| `scripts/trace_one_patient.py` | One record through every stage | 1 s |
| `scripts/generate_dataset.py` | Writes a synthetic export the dataset adapter reads | 2 s |
| `python -m tools.mock_portal --records 500` | The portal alone, to browse by hand | — |

---

## 4. Key files and functions

Grouped by the block they belong to. The names in **bold** are the ones a
reviewer might ask to see on screen.

### Policy — `src/compliance/`

| File | What to know |
|---|---|
| `models.py` | The vocabulary. `FieldCategory` (six DPDP categories), `Purpose` (three, pairwise non-nested), **`ExtractionRun`** — the manifest a technique writes about itself: purpose, `LawfulBasis`, retention, `SecurityPosture`, `Notice`, `Governance`. `ExtractedRecord` carries *categories only*, never values. |
| `policy.py` | **`PURPOSE_POLICY`** — per purpose: allowed categories, retention ceiling, whether pseudonymisation is required, the legitimate use relied on. The comment block explains why the three purposes are non-nested and why claims adjudication is deliberately absent. `policy_for(purpose)`. |
| `roles.py` | **`ARTEFACTS`** — HL7 v2 / FHIR / DICOM / 11073 objects with the categories each carries. **`ROLE_POLICY`** — a role's purposes and artefacts; `RolePolicy.allowed_categories()` is the *intersection*. **`authorise(role, purpose, artefacts)`** — three checks, three principles: PL-01, DM-01, SS-01. |
| `rules/*.py` | One class per principle; each `evaluate(run, records) → RuleResult` (status, 0–1 score, findings). `purpose_limitation.py` also assesses declared onward uses for compatibility. |
| `checkers.py` | `run_all(run, records)` → `ComplianceReport` — the entry point everything else calls. |
| `pseudonymise.py` | `token_for(value, key)` — HMAC-SHA256 token; `pseudonymise_row(layer, row, key)` replaces direct identifiers. |

### Semantics — `src/data_synthetic/`

| File | What to know |
|---|---|
| `catalogue.py` | **`FIELD_CATALOGUE`** — field → layer → category for all five layers (the fifth is audit events). `categories_for_fields()` is how a pulled row becomes something a rule can score. **`infer_layer(field_names)`** — the inverse: which layer explains these names — used by both the crawler and the dataset adapter. |
| `generators/records.py` | `build_dataset(n, seed)` — Faker rows for every layer. |
| `schemas/__init__.py` | One pydantic model per layer, derived from the catalogue; `validate_rows()`. |
| `export.py` | `write_export()` — one CSV per layer + manifest into `data/` (git-ignored). |

### Acquisition — `src/extraction/`

| File | What to know |
|---|---|
| `base.py` | **`HISDataSource`** — `layers()` and `fetch(layer, fields=…)`. The single boundary between any source and everything downstream. |
| `adapters/mock_his.py` | In-memory synthetic rows. |
| `adapters/portal_his.py` | **`PortalHISDataSource`** — a real browser behind the interface; opens detail pages only when a requested field is not in the list table; exposes `page_loads`; takes `field_aliases` for display labels. |
| `adapters/dataset_his.py` | **`DatasetHISDataSource`** — a directory of CSV/Excel; classifies each file by columns; takes `column_map`; drops and reports unknown columns. |
| `adapters/live_his.py` | The stub for live access. Still a stub, on purpose. |
| `tier2/browser.py` | `PortalBrowser` — `login()` (fills the form, the browser carries the token), `read_table()` (headers → names, rows, the detail link), `read_detail()`, `iter_table_pages()` (follows "Next"). Counts `page_loads`. |
| `tier2/navigation.py` | **`discover(browser)`** → `NavigationMap`: modules, columns, detail-only fields, page counts, and the *inferred* layer with a confidence. `NavigationMap.agent_pages()` hands the assistant a page per artefact. |

### Extraction — `src/extraction/`

| File | What to know |
|---|---|
| `technique.py` | `ExtractionTask` — a purpose plus the minimum fields it needs; `field_refs()` is the denominator for excess ratio and coverage. `TechniqueOutput` — manifest + valueless records + raw rows. |
| `techniques/compliant.py` | **Ours.** Pulls exactly `task.needed`; writes a full manifest from the policy (basis, retention within ceiling, all safeguards, notice, governance). |
| `techniques/morality.py` | **The morality model.** `FEELS_PRIVATE` — the intuition table; refuses those fields whatever the purpose, takes the rest; manifest by instinct (consent assumed, no notice, no retention, logs). |
| `techniques/unconstrained.py` | **The baseline.** Every field of every layer; no purpose declared; TLS only. |
| `metering.py` | **`MeteredSource`** wraps any source and counts fetches, rows, fields, page loads without the technique knowing. `ExtractionCost` — `excess_ratio`, `coverage`, `page_loads`, `elapsed_ms`. |

### Scoring — `src/compliance/`

| File | What to know |
|---|---|
| `benchmark.py` | **`run_benchmark(techniques, tasks, source)`** — every technique × every task, metered, scored, aggregated. `BenchmarkResult.render_table()` prints the two tables; **`_takeaway()`** derives the compliance-vs-cost sentence from the numbers, including the under-coverage line. |
| `purpose_matrix.py` | **`score_across_purposes(run, records)`** — same extraction, every purpose; the notice is treated as not covering an undeclared purpose, and the output says so. |
| `report.py` | `ComplianceReport` — score, pass rate, per-rule results; console / JSON / Markdown. |

### Export — `src/interop/`

| File | What to know |
|---|---|
| `mapping.py` | `LAYER_STANDARDS` — which standards each layer carries (audit layer → FHIR only). |
| `hl7/messages.py` | `Segment`, `Message`; builders `adt_a04`, `orm_o01`, `oru_r01`, `dft_p03`; `shape_hl7(layer, row)`. Sets only fields present in the row. |
| `fhir/resources.py` | `shape_fhir(layer, row)` → Patient, Encounter, Condition, MedicationRequest, AllergyIntolerance, ServiceRequest, Observation, DiagnosticReport, Invoice, Coverage, AuditEvent — the same names `ARTEFACTS` uses. |
| `normalise.py` | **`normalise(output)`** — pseudonymises when the manifest declares it, then shapes per layer. **`audit(output, normalised)`** — searches the artefacts for raw identifiers; `ExportAudit.one_line()`. |

### Guidance — `src/agent/`

| File | What to know |
|---|---|
| `functions.py` | **`REGISTRY`** — 13 `FunctionSpec`s: purpose, artefacts, `InputSlot`s, `Step`s grounded in layer + artefact + catalogue fields. `capabilities(role)` — derived from the gate, not stored. |
| `session.py` | **`Session.respond(text)`** — the state machine: `recognise()` (token overlap; ties ask) → **gate before collecting** → slot filling → `build_guidance`. Declines cite the rule and name who can. |
| `guidance.py` | `StaffGuidance.render()` — numbered steps with `[layer / artefact / page]`, cautions, and a footer stating purpose, lawful basis, categories touched, retention. |

### Fixture — `tools/mock_portal/`

| File | What to know |
|---|---|
| `__init__.py` | `create_app(source, …)` — Flask over any `HISDataSource`; login token; `LIST_COLUMNS` (what the table shows; the rest is detail-only); `MODULE_SLUGS` use portal vocabulary; `labels=` renders display labels. |
| `serve.py` | `BackgroundPortal` — the portal in a thread for tests and `run_pipeline`. |

---

## 5. The one-sentence version of each block, for the presenter's card

- **Acquisition** — any source, one interface, nothing downstream knows which.
- **Semantics** — field name → layer → DPDP category; the rules score categories, never values.
- **Extraction** — a technique pulls *and* declares; the manifest is scored, not the intention.
- **Scoring** — seven principles, two axes; the takeaway is derived, not written.
- **Export** — shaping adds nothing; pseudonymisation is applied when declared and audited afterwards.
- **Guidance** — no model; gate before collect; every step grounded in something the HIS has.
- **Policy** — one table, three readers.
