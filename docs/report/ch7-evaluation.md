# Chapter 7 — Evaluation

*Draft 1, 2026-09-15. Target ~2200 words of prose plus tables; this draft is
~2600 of prose. Every number is taken from a tracked artefact in
`docs/benchmark_results/` (the file is named beside each table) or from the
pipeline's own output, and can be regenerated with the command given. Sections
marked **[real data]** are slots for the hospital dataset and are to be written
when it arrives; nothing else in the chapter changes when it does.*

---

> **Revision pending (2026-09-16).** The middle rows of Tables 1 and 2 will be
> the recorded AI agents (Claude / OpenAI / Gemini, unaided and told the Act)
> once `scripts/record_ai_agents.py` has been run with the keys; Table 2 gains a
> *stable runs* column, and §7.2 a paragraph on determinism. The morality-model
> rows and their reading below are draft-1 text and will be replaced by the real
> numbers, not edited around.

The evaluation asks four questions of the framework and answers each with an
artefact the reader can regenerate. Does compliance, as scored in Chapter 3,
discriminate between *techniques* rather than merely between careful and
careless configurations of one? Does the verdict on an unchanged extraction
change when only its purpose changes? Do compliance and cost trade off, or move
together? And is what a technique *declares* about its output borne out by what
is *in* its output? A fifth section reports the properties of the acquisition
layer that the benchmark rests on, and a sixth shows the same policy table
gating the staff assistant.

## 7.1 Setup

**Techniques.** The three of Chapter 4: compliance-aware, the morality model,
and the unconstrained baseline.

**Tasks.** Each task names a purpose and the minimum necessary fields for it.
The in-memory workload has four; the portal workload has three, omitting
`medication-review`, which differs from `patient-summary` only in one field and
adds pages without adding information.

| Task | Purpose | Minimum necessary fields |
|---|---|---|
| `patient-summary` | care coordination | mrn, date of birth, sex; primary diagnosis, medication, allergy |
| `ward-census` | care coordination | mrn, admission ward; encounter time (the in-memory variant also asks for admission time) |
| `medication-review` (in-memory only) | care coordination | mrn, date of birth; primary diagnosis, medication, allergy |
| `appointment-reminder` | patient registration | mrn, full name, phone, admission time |

The fourth task was added deliberately: it is the one where instinct and law
disagree. A registration desk lawfully needs a name and a phone number to
confirm an appointment; the morality model refuses both.

**Sources.** Two, and a slot for a third.

- *In memory* — 50 synthetic records per layer across five layers, seed 42.
  Deterministic, instant, and the reproducible reference for the paper
  (`benchmark.md`, `python scripts/run_benchmark.py`).
- *Portal* — the same generator served as a login-gated HTML portal, 20 records
  per module, ten per page, scraped by a real browser that logs in, discovers the
  modules, reads list tables and opens record pages (`benchmark-portal.md`,
  `python scripts/run_pipeline.py`). Cost here includes real page loads.
- **[real data]** *Hospital dataset* — read through the dataset adapter with a
  column map; same tasks, same rules, same tables (§7.7).

**Metrics.** Compliance score and per-rule scores from Chapter 3; the cost
profile of Chapter 4. Every metric except wall-clock is deterministic: the same
inputs produce the same numbers on any machine. Wall-clock is reported in the
tables and labelled hardware-dependent; on the development machine it varied by
a factor of nearly two between runs of the same portal workload on the same
day, which is the reason it is not relied upon.

**Evidence of properties.** Where the chapter claims a structural property —
that no purpose's scope contains another's, that the assistant's gate runs before
any input is collected, that every instruction step is grounded in the HIS model
— the claim is asserted by a test in the 230-test suite, and the test is named.

## 7.2 Compliance × cost — the benchmark

**Table 1.** Compliance per rule, portal workload (`benchmark-portal.md`; three
tasks; 20 records per module; identical rule set for every technique).

| Technique | Score | Rules passed | DM-01 | LB-01 | SL-01 | SS-01 | PL-01 | NT-01 | AC-01 |
|---|---|---|---|---|---|---|---|---|---|
| compliance-aware (ours) | **1.000** | 7/7 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| morality (privacy by instinct) | 0.484 | 2/7 | 1.00 | 0.50 | 0.00 | 0.56 | 1.00 | 0.00 | 0.33 |
| unconstrained (baseline) | 0.135 | 0/7 | 0.67 | 0.00 | 0.00 | 0.28 | 0.00 | 0.00 | 0.00 |

**Table 2.** Cost profile, portal and in-memory workloads. Deterministic
columns lead; wall-clock is hardware-dependent and is the median of one run.

| Source | Technique | Compliance | Excess ratio | Coverage | Distinct / needed | Fields pulled | Page loads | Wall-clock (ms) |
|---|---|---|---|---|---|---|---|---|
| portal | compliance-aware | 1.000 | 1.00 | 1.00 | 13 / 13 | 260 | **70** | 12 108 |
| portal | morality | 0.484 | 0.85 | 0.85 | 11 / 13 | 220 | 70 | 12 788 |
| portal | unconstrained | 0.135 | 7.15 | 1.00 | 93 / 13 | 1 860 | **330** | 52 162 |
| in memory | compliance-aware | 1.000 | 1.00 | 1.00 | 19 / 19 | 950 | n/a | 1.0 |
| in memory | morality | 0.482 | 0.90 | 0.90 | 17 / 19 | 850 | n/a | 1.0 |
| in memory | unconstrained | 0.134 | 6.53 | 1.00 | 124 / 19 | 6 200 | n/a | 3.9 |

**Reading Table 1.** The gap between the compliant technique and the baseline is
0.865 on the portal and 0.866 in memory, on the same seven rules. The two
sources agree to three decimal places on every compliance figure, because the
rules score categories and manifests, not record volume — the portal changes
what the extraction *costs*, not what it *is*. The baseline fails every rule.
Its DM-01 of 0.67 is the set-containment score: of six categories pulled, three
(clinical, contact, financial) are outside care coordination's scope. Its SS-01
of 0.28 is one safeguard of four under care and one of three under registration,
averaged over tasks.

The morality model is the informative row. It passes DM-01 and PL-01 perfectly:
it pulls the right categories and knows its purpose. It then scores 0.50 on
LB-01 (a basis asserted, never referenced), 0.00 on SL-01 (no retention, no
deletion), 0.00 on NT-01 (no notice), 0.33 on AC-01 (logging only). A technique
that pulls the right data for the wrong reasons and declares almost nothing lands
at 0.484 — roughly halfway between the other two, which is where a reader's
intuition would put "well-meaning but not lawful", and the per-rule columns say
precisely why.

**Reading Table 2.** The baseline touches 93 distinct fields where the tasks
require 13, an excess ratio of 7.15, at the same coverage as the compliant
technique's 1.00. On the portal that overreach is paid for in pages: 330 loads
against 70, because every field only available on a record page costs one load
per record, and the baseline asks for all of them. This is the result Chapter 4
argued for: the fields pulled beyond the purpose are the overreach DM-01
penalises, so compliance and cost move *together* for the baseline, not against
each other. The compliant technique is the cheap one.

The morality model's row is the second half of the argument. Its excess ratio,
0.85, is *lower* than the compliant technique's, and read alone would make it the
most economical of the three. Its coverage is also 0.85: on the
`appointment-reminder` task it refused the name and phone number the desk
lawfully needs, obtaining two of the four fields. Low cost here is the failure,
not efficiency, and it is coverage — the guard rail — that exposes it. The
benchmark's own summary line names both cases: the baseline pulled more than the
purpose needs, the morality model pulled less than the task needs. Privacy by
instinct fails in both directions.

## 7.3 The purpose matrix

**Table 3.** One extraction, every purpose (`*--purpose-matrix.md`;
`python scripts/compare_purposes.py`). Each row block is a single run by the
compliant technique, with a full manifest, scored against all three purposes
with nothing changed but the purpose.

| Run | Purpose judged | Declared | Score | Rules failed | Why |
|---|---|---|---|---|---|
| care pull (clinical, quasi-id, direct-id, admin; 30 d) | care_coordination | yes | **1.000** | — | lawful for this purpose |
| | billing_settlement | no | 0.857 | DM-01, NT-01 | out of scope: clinical, quasi-identifier |
| | patient_registration | no | 0.893 | DM-01, NT-01 | out of scope: clinical |
| billing pull (financial, contact, direct-id, admin; 30 d) | billing_settlement | yes | **1.000** | — | lawful for this purpose |
| | care_coordination | no | 0.857 | DM-01, NT-01 | out of scope: contact, financial |
| | patient_registration | no | 0.893 | DM-01, NT-01 | out of scope: financial |
| billing pull, **365 d** retention | billing_settlement | yes | **1.000** | — | lawful: billing's ceiling is 365 d |
| | care_coordination | no | 0.786 | DM-01, SL-01, NT-01 | out of scope; retention exceeds 90 d |
| | patient_registration | no | 0.821 | DM-01, SL-01, NT-01 | out of scope; retention exceeds 180 d |

**Reading.** The same records, the same manifest, the same seven rules: 1.000
under the declared purpose and 0.857 under the other. Nothing about the
extraction changed — only what it was for. The failure runs in *both*
directions: the care pull is unlawful for billing because clinical data is not
necessary to settle an account, and the billing pull is unlawful for care because
contact and financial data are not necessary to coordinate treatment. Neither
purpose is stricter than the other; that is the non-nesting property of §3.4
showing up as a result, and `test_three_purposes_and_all_pairwise_non_nested`
asserts it holds for every pair.

The retention block shows a second rule varying with purpose. A billing
extraction held for a year is lawful — financial records are retained against
audit obligations, and billing's ceiling is 365 days — and the *same* extraction
would exceed care coordination's 90-day ceiling by four times. A longer
retention is a different necessity, not laxity.

**The notice caveat, stated.** NT-01 fails for every undeclared purpose in every
block. That is by construction, not by adjustment: the notice given to the Data
Principal named the declared purpose, and a notice that named care does not
cover billing. We report it so that the reader can subtract it: the rules that
vary with the purpose *itself* are DM-01, SL-01 and, where onward uses are
declared, PL-01. The table's "Rules failed" column makes the two visible
separately.

## 7.4 Discovery and transfer

The portal results above rest on the crawler having correctly understood a
system it was told nothing about. **Table 4** is the navigation map it built
(`navigation-map.md`; discovered in 11 page loads from the home page after
login).

| Module (as the portal names it) | Path | Pages | Inferred layer | Confidence |
|---|---|---|---|---|
| Patient Registration | `/m/registration/` | 2 | patient administration | 100% |
| Clinical Records | `/m/clinical/` | 2 | clinical / EHR | 100% |
| Departmental Orders | `/m/departments/` | 2 | ancillary / departmental | 100% |
| Billing & Accounts | `/m/billing/` | 2 | administrative / financial | 100% |
| Audit Log | `/m/integration/` | 2 | infrastructure / integration | 100% |

The layer is inferred **from the field names found on each module's pages**,
matched against the catalogue — never from the URL, which uses the portal's own
vocabulary. Confidence is the share of fields seen that the inferred layer's
catalogue explains; on the fixture it is 100% for every module because the
fixture's headers are catalogue names.

That last point is the limitation, and we tested past it. A real portal shows
display labels — "Patient ID", "DOB" — not catalogue names. The fixture renders
labels on request, and two tests establish the transfer property
(`tests/extraction/test_portal_labels.py`): **without** a label map, the
labelled module cannot be classified (confidence below 0.5; "Patient ID" is an
unknown column); **with** a map of label to catalogue field, applied as headers
are read, the same portal is understood at 100% and everything downstream —
discovery, fetching, the three techniques, the benchmark — runs unchanged. The
label map is the one piece of portal-specific knowledge in the chain, and it is
data, not code. The same mechanism serves the hospital export: the dataset
adapter classifies each file by its columns and takes a column map for
hospital-named headers.

The proof that the adapter boundary holds is not a table but a test:
`test_compliant_technique_runs_against_the_portal_unchanged` and
`test_benchmark_runs_all_three_techniques_against_the_portal` run the code
written for the in-memory source against the browser-driven one with no change.

## 7.5 Export audit

Chapter 3 scored whether pseudonymisation was *declared* (SS-01). **Table 5**
reports whether it *happened*: after each run's rows were shaped into HL7 v2 and
FHIR (Chapter 6), the audit searched every artefact for every raw direct-identifier
value the run had extracted (pipeline stage 4; `patient-summary` task, portal
source, 20 records per module).

| Technique | Pseudonymisation declared | Artefacts | Raw identifiers extracted | Found in the export |
|---|---|---|---|---|
| compliance-aware | yes | 40 HL7 v2 messages, 80 FHIR resources | 20 | **0** |
| unconstrained | no | 80 HL7 v2 messages, 260 FHIR resources | 80 | **80 of 80** |

The compliant technique's export carries pseudonymous tokens
(`PSN-…`, keyed and non-reversible) in every identifier position; the baseline's
carries the medical record numbers verbatim. The declaration in the manifest and
the property of the output agree in both cases — which is what makes the
manifest worth scoring. `test_compliant_export_leaks_no_raw_identifier_and_baseline_leaks_all`
asserts it; `test_shaping_adds_nothing_that_was_not_extracted` asserts that the
shaping step introduces no field the technique did not pull.

## 7.6 The role gate and the assistant

The same policy table that scores the benchmark gates what the staff assistant
may instruct a role to do. **Table 6** runs one request through all three roles
(`python scripts/show_role_access.py`).

| Request | Purpose | Reception | Nurse | Administrator |
|---|---|---|---|---|
| Raise an invoice for the visit | billing | declined **SS-01** — does not handle `Account`, `Invoice` | declined **PL-01** — no purpose | permitted |
| Look up the diagnosis and medication | care | declined **PL-01** — no purpose | permitted | declined **PL-01** — no purpose |
| Check whether insurance is active | billing | permitted | declined **PL-01** | permitted |
| Match the patient by name and date of birth | registration | permitted | declined **PL-01** | permitted |
| Reconcile a claim, including diagnosis codes | billing | declined **DM-01** — clinical data not necessary | declined **PL-01** | declined **DM-01** |

Three properties are worth drawing out. First, every decline names its rule,
and the three rules are three different principles: reception is refused an
invoice not because it lacks a purpose (billing is one of its purposes, for
eligibility) but because it does not handle the `Invoice` artefact under the
standards — an access-control failure, SS-01, not a purpose failure. Second, a
role's scope is *derived* as the intersection of its purposes and its artefacts,
not listed, and either source alone would over-grant: purpose alone would let
reception raise invoices; artefacts alone would let the nurse read an address
from `Patient`. Third, the last row: the FHIR `Claim` resource carries diagnosis
codes and is granted to *no* role, so claims reconciliation is declined for the
administrator under DM-01 — clinical data is not necessary for billing — which is
the unmodelled-purpose decision of §3.4 enforced at the desk.

In the assistant, the gate runs **before any input is collected**. A
receptionist who asks how to look up a diagnosis is declined, with PL-01 cited
and a pointer to the role that can, without being asked for a medical record
number first — collecting details for a request that will be refused is itself
over-collection. `test_gate_runs_before_any_input_is_requested` asserts the
ordering; `test_full_conversation_yields_grounded_guidance` asserts that every
step the assistant does give names a layer, an artefact and fields that exist in
the HIS model.

## 7.7 [real data] The hospital dataset

*To be written when the dataset arrives. Contents, fixed now so the section is a
fill-in rather than a redesign:*

- *Provenance and handling: who supplied it, its de-identification status, the
  basis on which it was shared, and the handling gate's report
  (`scripts/check_source.py`).*
- *What the adapter understood: files, columns, the column map, the layer each
  file was classified into and at what confidence; columns dropped as
  unrecognised.*
- *Tables 1 and 2 on the dataset. Expected: identical compliance figures
  (they depend on categories and manifests), different field counts, and — if a
  needed column is absent — a coverage ceiling shared by every technique, which
  the benchmark reports as a property of the source (§4.4).*
- *Table 5 on the dataset, if the export stage is run: the identifier count will
  be the dataset's, the leak count for the compliant technique should remain
  zero.*
- *What changed against synthetic, in one paragraph.*

## 7.8 Threats to validity

We state these plainly because the framework's credibility rests on them being
stated.

**The fixture is self-authored.** The portal was built by us, and although it
was built on the rule that we do not control it — portal vocabulary in URLs, no
data endpoint, no hooks, a per-session token, labels on request — a portal we
wrote cannot surprise us the way a vendor's can. The portal demonstrates the
*mechanism* of browser-driven extraction and produces honest cost differences;
it does not demonstrate robustness against real interfaces. The label-mode
tests of §7.4 narrow this, and the hospital dataset (§7.7) narrows it further on
the data side, but only live access closes it.

**The baseline is hand-written.** It is a coverage-optimised extractor with no
manifest, standing in for the class of published scrapers, not a
reimplementation of one. The panel accepted this on the ground that the majority
of deployed systems sit at that level of compliance; a reader who does not
accept it should read the baseline's row as a lower bound on what such a scraper
would score, since a published one would declare no more.

**The data are synthetic.** Field *distributions* are the generator's, and
nothing in the compliance figures depends on them — the rules see categories,
not values — but the *structure* is ours until a real export is seen. The
catalogue is the single place that changes if the structure differs.

**One hospital, three purposes.** The policy models three purposes for one
setting. The non-nesting property is asserted for these three; a fourth purpose
must preserve it, and the test will fail if it does not, but the framework's
behaviour on a larger purpose set is untested.

**Section mapping pending.** The rules cite principles; the provision mapping
of §3.3 is drafted and marked unverified until checked against the Gazette text.
No result in this chapter depends on a section number.

**Wall-clock.** Reported, not relied upon; see §7.1.

---

*Cross-references to fill in at assembly: Chapter 3 (§3.3 rules; §3.4 policy and
non-nesting), Chapter 4 (§4.2 techniques; §4.3 metrics; §4.4 the guard rail and
the source ceiling), Chapter 5 (portal fixture; label map; dataset adapter and
handling gate), Chapter 6 (shaping and audit; roles; the assistant).*
