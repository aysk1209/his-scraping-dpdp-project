# Project report — outline and drafting plan

The last item on the completion ledger (6 of 100), and Review-III's deliverable
together with the manuscript. The compliance chapters need no real data and can
be drafted now; the results chapter is written against the synthetic runs with a
clearly marked slot for the hospital dataset. Group voice throughout ("we"); no
vendor names; DPDP cited by section only after the mapping in
`docs/compliance/dpdp-provision-map.md` has been verified against the Gazette
text.

Each chapter below lists what it argues, the artefact it draws from, and its
status. Word counts are targets for the report; the manuscript is a compression
of chapters 3–6 to conference length.

---

## 1. Introduction *(~900 words — draft now)*

**Argues.** Hospital Information Systems hold high-sensitivity personal data;
techniques for extracting data from them are evaluated on speed, robustness and
coverage, never on data-protection compliance; under the DPDP Act 2023 that gap
is a legal exposure and a research gap at once. Thesis: **compliance can be a
measured, benchmarkable property of an extraction technique.**

**Draws from.** `PROJECT_CONTEXT.md` (research framing); Review-I deck slide 2;
`docs/compliance/approach.md` opening.

**Contents.** Motivation · the applied setting (an assistant for hospital staff,
which frames why extraction matters) · thesis · contributions (numbered — see
§8) · report structure.

## 2. Background and related work *(~1800 words — draft now)*

**Argues.** Three literatures meet here and none measures compliance.

**Draws from.** The 12-reference literature-survey pool (Review-I deck slides 3–4
and memory `axe-autoscraper-citations`); `docs/architecture/five-layer-his.md`;
`src/interop/README.md`.

**Contents.**
- 2.1 Hospital Information Systems: the five-layer functional model; heterogeneity
  as the standing obstacle; the interoperability standards (HL7 v2, FHIR R4,
  DICOM, ISO/IEEE 11073) and what each carries.
- 2.2 Web data extraction: wrapper induction (AutoScraper, EMNLP 2024), headless
  browser automation, LLM-driven agentic extraction (AXE) — and the evaluation
  metrics each reports.
- 2.3 The DPDP Act 2023: the seven obligations as principles; the Act's structure
  (ss.4–8); how it differs from the GDPR where relevant (no free-standing
  minimisation article); Rules status.
- 2.4 Compliance evaluation in the literature: checklists and qualitative
  guidance; the absence of a per-technique score. **The gap, stated.**

## 3. The compliance framework *(~2500 words — draft now; the core chapter)*

**Argues.** Seven DPDP principles can be written as executable rules over a
structured declaration of an extraction run, and a policy table makes "necessary
for the purpose" machine-checkable.

**Draws from.** `src/compliance/models.py`, `rules/*.py`, `policy.py`,
`checkers.py`, `report.py`; `docs/compliance/dpdp-provision-map.md` (section
mapping, once verified).

**Contents.**
- 3.1 The extraction manifest (`ExtractionRun`): what a run must declare about
  itself — purpose, lawful basis, retention, safeguards, notice, governance — and
  why scoring the *declaration* rather than the intention is the right unit.
- 3.2 Valueless records: scoring field *categories*, never values, so that
  benchmark artefacts carry no personal data and the framework is HIS-agnostic.
- 3.3 The seven rules, one subsection each: principle → provision → check →
  scoring → findings. Include the compatibility assessment in PL-01 and the
  conditional pseudonymisation requirement in SS-01.
- 3.4 The purpose policy: three purposes, pairwise non-nested, and why non-nesting
  is the load-bearing property (out of scope = not necessary, not "more
  sensitive"); the deliberate exclusion of claims adjudication.
- 3.5 Aggregation: `ComplianceReport` — weighted score, pass rate, per-rule
  findings.

## 4. Extraction techniques and the cost axis *(~1800 words — draft now)*

**Argues.** Techniques differ in what they pull *and* what they declare; cost can
be measured in reproducible units; excess ratio is simultaneously a cost measure
and the minimisation overreach.

**Draws from.** `src/extraction/technique.py`, `techniques/*.py`,
`metering.py`; `PLAN.md` §3.

**Contents.**
- 4.1 The adapter boundary (`HISDataSource`) and why every downstream component
  is written once.
- 4.2 The three techniques: compliance-aware (purpose-bound, full manifest);
  the **morality model** (privacy by instinct — the explicit intuition table,
  no concept of purpose, wrong in both directions); the unconstrained baseline.
  State plainly that the baseline is hand-written and why that is acceptable
  (most deployed systems sit there).
- 4.3 Metering at the boundary: fields pulled, fetches, page loads, excess
  ratio, coverage, wall-clock — deterministic metrics lead; wall-clock is
  reported as hardware-dependent.
- 4.4 Why excess ratio and DM-01 are one quantity seen twice; why coverage is the
  guard rail that catches the morality model.

## 5. Acquisition: portal, browser, dataset *(~1600 words — draft now; extend with real data)*

**Argues.** Structure can be discovered rather than declared, and classified from
content rather than labels — which is the heterogeneity answer.

**Draws from.** `tools/mock_portal/`, `src/extraction/tier2/`,
`adapters/portal_his.py`, `adapters/dataset_his.py`, `data_synthetic/catalogue.py`
(`infer_layer`), `compliance/handling.py`; `docs/benchmark_results/navigation-map.json`.

**Contents.**
- 5.1 The mock portal as a system we do not control: what it offers and
  deliberately does not. **Limitation, stated:** cleaner than a real vendor
  system.
- 5.2 Tier-2 browser extraction: login, crawl, table parsing, pagination, page
  counting; the navigation map; layer inference from field names; label→field
  aliases as the one piece of portal-specific knowledge.
- 5.3 The dataset adapter: file classification by columns, the column map, the
  handling gate (provenance, de-identification, ignore rules) — and why a
  compliance project must gate its own inputs.
- 5.4 Synthetic data: catalogue, generator, per-layer schemas, the fifth layer as
  audit events. **[Real-data slot: the hospital export — structure, column map,
  what differed from the catalogue.]**

## 6. Export and the staff assistant *(~1400 words — draft now)*

**Argues.** The same policy table gates two more things: what leaves as HL7/FHIR,
and what a member of staff may be told.

**Draws from.** `src/interop/normalise.py`, `hl7/`, `fhir/`,
`compliance/pseudonymise.py`; `compliance/roles.py`; `src/agent/`.

**Contents.**
- 6.1 Shaping adds nothing: only extracted fields appear in the artefacts.
- 6.2 Pseudonymisation on export (keyed tokens; stable within, unlinkable across)
  and the **export audit** — the manifest's claim verified against output.
- 6.3 Role access derived from purposes ∩ interoperability artefacts; the three
  checks; artefacts granted to no role and why.
- 6.4 The assistant: registry, recognition, gate-before-collect, grounded steps.
  Say explicitly: no model, no training; a completeness deliverable whose one
  research-relevant property is the gate.

## 7. Evaluation *(~2200 words — draft on synthetic now; add real-data tables when available)*

**Argues.** Compliance discriminates between techniques; purpose changes the
verdict for an unchanged extraction; cost and compliance move together for the
baseline and low cost is the morality model's failure; the export audit
separates declared from actual.

**Draws from.** `docs/benchmark_results/benchmark.md` (in memory),
`benchmark-portal.md` (real browser, real page loads), the two purpose matrices,
`navigation-map.json`; the 224-test suite as evidence of the properties claimed
(non-nesting, groundedness, gate ordering).

**Contents.**
- 7.1 Setup: tasks, purposes, sources (in-memory / portal / **[dataset]**),
  metrics; what is deterministic and what is not.
- 7.2 Compliance × cost (Table 1: the benchmark). Reading: the 0.87 gap; the
  baseline's 6–7× excess at equal coverage; the morality model at 0.48 with
  coverage 0.85–0.90.
- 7.3 The purpose matrix (Table 2): one extraction, three verdicts; the retention
  case; the notice caveat, stated.
- 7.4 Discovery and transfer: the navigation map; layers inferred at 100% on the
  fixture; label-mode result (cannot classify without aliases, 100% with).
- 7.5 Export audit (Table 3): 0 of N vs N of N.
- 7.6 Role gate and assistant: the three-roles-three-outcomes table; the
  decline-before-collect property.
- 7.7 **[Real data: the same tables on the hospital dataset, and what changed.]**
- 7.8 Threats to validity: self-authored fixture; hand-written baseline; synthetic
  distributions; a single hospital; section mapping pending verification.

## 8. Conclusion *(~700 words — draft now)*

Contributions, numbered: (1) a DPDP compliance framework as executable rules over
an extraction manifest; (2) a two-axis benchmark with a cost measure that is also
a compliance measure; (3) the purpose matrix — compliance as a property of pull
*and* purpose; (4) content-based structure discovery with layer inference; (5)
pseudonymisation on export verified by audit; (6) a role gate derived from
purposes and interoperability artefacts, applied to a staff assistant. Then: what
real data would change; what deployment would require (out of scope); future
work — a fourth purpose (claims adjudication, with its own envelope), DICOM /
11073 shaping, a real portal.

## Appendices

- A. The section mapping table (verified).
- B. The field catalogue, all five layers.
- C. The purpose policy and role policy tables, verbatim from code.
- D. The 13 assistant functions and their intuition-table counterpart
  (`FEELS_PRIVATE`).
- E. Reproducibility: seeds, commands, the test suite, how to regenerate every
  table in the report.

---

## Drafting order

1. Chapters 3 and 4 first — the contribution, and entirely available.
2. Chapter 7 on synthetic data, with the real-data slots marked.
3. Chapters 5 and 6.
4. Chapters 1, 2, 8 and the appendices.
5. When the hospital dataset lands: §5.4, §7.7, and a pass over §7.8.

## The manuscript

A compression of chapters 3–7 to conference length: framework (3), techniques and
cost (4), evaluation (7), with acquisition and the assistant reduced to a
paragraph each. The contribution list from §8 becomes the abstract's last
sentence. Target venue and page budget to be decided with the guide.
