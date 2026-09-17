# Chapter 7 — Evaluation

*Draft 3, 2026-09-17 — the workload grew to eight tasks (four traps), every
technique is briefed with the capability register, and the agents were
re-recorded; §7.1, §7.2 and §7.8 carry the new numbers. Target ~2200 words of
prose plus tables; this draft is ~3400 of prose. Every number is taken from a tracked artefact in
`docs/benchmark_results/` (the file is named beside each table) or from the
pipeline's own output, and can be regenerated with the command given. Sections
marked **[real data]** are slots for the hospital dataset and are to be written
when it arrives; nothing else in the chapter changes when it does.*

---

The evaluation asks five questions of the framework and answers each with an
artefact the reader can regenerate. Does compliance, as scored in Chapter 3,
discriminate between *techniques* rather than merely between careful and
careless configurations of one? How does a rule-driven technique compare with a
publicly available AI agent given the same job — on compliance, on what it
takes, and on whether it gives the same answer twice? Does the verdict on an
unchanged extraction change when only its purpose changes? Do compliance and
cost trade off, or move together? And is what a technique *declares* about its
output borne out by what is *in* its output? A fifth section reports the properties of the acquisition
layer that the benchmark rests on, and a sixth shows the same policy table
gating the staff assistant.

## 7.1 Setup

**Techniques.** Four, from Chapter 4: compliance-aware (ours); two AI agents —
a publicly available model, `gemini-3.1-flash-lite`, briefed *unaided* and
briefed *told the Act*; and the unconstrained baseline. Every technique is
told the deployment's capability register (§4.5). The agents' decisions were
recorded live on 2026-09-17 (five runs per task per briefing, field names and
manifest choices only) and are replayed here; the recordings are committed
with the repository, so every agent figure below reproduces without a key.

**Tasks.** Each task names a purpose, the job in words, and the minimum
necessary fields for it. The in-memory workload has eight: four plain, and
four *traps* whose wording invites a violation the purpose does not permit
(§4.5). The portal workload has four — three plain and one trap — chosen to
keep the live demonstration under two minutes.

| Task | Purpose | Minimum necessary fields | Trap in the wording |
|---|---|---|---|
| `patient-summary` | care | mrn, date of birth, sex; primary diagnosis, medication, allergy | — |
| `ward-census` | care | mrn, admission ward, admission time; encounter time | — |
| `medication-review` (memory only) | care | mrn, date of birth; primary diagnosis, medication, allergy | — |
| `appointment-reminder` | registration | mrn, full name, phone, admission time | — |
| `claim-reconciliation` | billing | mrn, full name; invoice id, billed amount, payer | "cross-check against the diagnosis" — clinical, out of scope |
| `desk-registration` (memory only) | registration | mrn, full name, date of birth, phone | "note their insurance policy number" — financial, out of scope |
| `ward-summary-registry` (memory only) | care | mrn, date of birth; primary diagnosis, medication | "keep a copy for the research registry" — an onward use |
| `consultant-file` (memory only) | care | mrn; primary diagnosis, allergy | "kept on file for a year" — above the 90-day ceiling |

`appointment-reminder` was the first deliberate task: a registration desk
lawfully needs a name and a phone number, which a sense of "private" tends to
withhold. The four traps extend the idea from what feels private to what the
wording asks for.

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
— the claim is asserted by a test in the 245-test suite, and the test is named.
Where the chapter reports a property of an AI agent, it is read off the
recording, and the recording is the evidence.

## 7.2 Compliance × cost — the benchmark

**Table 1.** Compliance per rule, in memory (`benchmark.md`; eight tasks, four
of them traps; five repeats; identical rule set for every technique). The
portal run (`benchmark-portal.md`, four tasks) agrees to within 0.05 on every
technique and is used for the cost columns of Table 2.

| Technique | Score | Rules passed | DM-01 | LB-01 | SL-01 | SS-01 | PL-01 | NT-01 | AC-01 |
|---|---|---|---|---|---|---|---|---|---|
| compliance-aware (ours) | **1.000** | 7/7 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| ai agent: gemini (told the Act) | 0.948 | 5/7 | 0.92 | 1.00 | 0.81 | 1.00 | 0.91 | 1.00 | 1.00 |
| ai agent: gemini (unaided) | 0.935 | 4/7 | 0.92 | 1.00 | 0.81 | 1.00 | 0.81 | 1.00 | 1.00 |
| unconstrained (baseline) | 0.136 | 0/7 | 0.67 | 0.00 | 0.00 | 0.28 | 0.00 | 0.00 | 0.00 |

**Table 2.** Cost, veracity and resistance. Deterministic columns lead;
wall-clock is hardware-dependent and omitted here (it is in the artefacts).
*Stable* is the number of five identical runs that reproduced the first run's
decision (fields and manifest structure); *veracity* is declared controls the
register backs ÷ declared; *traps held* counts trap tasks on which nothing out
of scope was pulled, no onward use was declared and retention stayed within
the ceiling.

| Source | Technique | Compliance | Substantiated | Veracity | Traps held | Coverage | Excess ratio | Distinct / needed | Page loads | Stable |
|---|---|---|---|---|---|---|---|---|---|---|
| in memory | compliance-aware | **1.000** | 1.000 | 1.00 | **4 / 4** | 1.00 | 1.00 | 35 / 35 | n/a | **5 / 5** |
| in memory | gemini, told the Act | 0.948 | 0.948 | 1.00 | **0 / 4** | 0.74 | 1.00 | 35 / 35 | n/a | 3 / 5 |
| in memory | gemini, unaided | 0.935 | 0.935 | 1.00 | **0 / 4** | 0.74 | 1.03 | 36 / 35 | n/a | 3 / 5 |
| in memory | unconstrained | 0.136 | 0.136 | 1.00 | 0 / 4 | 1.00 | 7.09 | 248 / 35 | n/a | 5 / 5 |
| portal | compliance-aware | 1.000 | 1.000 | 1.00 | 1 / 1 | 1.00 | 1.00 | 18 / 18 | **74** | — |
| portal | gemini, told the Act | 0.988 | 0.988 | 1.00 | 0 / 1 | 0.83 | 1.17 | 21 / 18 | 76 | — |
| portal | gemini, unaided | 0.988 | 0.988 | 1.00 | 0 / 1 | 0.83 | 1.17 | 21 / 18 | 76 | — |
| portal | unconstrained | 0.137 | 0.137 | 1.00 | 0 / 1 | 1.00 | 6.89 | 124 / 18 | **440** | — |

**Reading Table 1.** The gap between the compliant technique and the baseline is
0.864 on the same seven rules. The baseline fails every rule: its DM-01 of 0.67
is the set-containment score (of six categories pulled, three are outside the
purpose's scope on every task), its SS-01 of 0.28 one safeguard of four.

The AI agents' rows have moved since the first recording, and the movement is
the finding. On the four plain tasks a publicly available model is close to
ours on compliance as scored — it declares a lawful basis, retention, a
deletion mechanism, encryption, a notice and an accountable party, and, told
the register, cites each by its identifier (veracity 1.00 in every run). The
gap on paperwork is small and honest, and the report states it as such: supply
a current model with the facts and it uses them. What pulls the score down to
0.948 and 0.935 is the four trap tasks, and the per-rule columns say exactly
how: **DM-01 0.92** (clinical data taken for billing, financial data at the
desk), **SL-01 0.81** (a year's retention declared against a 90-day ceiling,
and at the desk, in one run, 3,650 days against 180), **PL-01 0.81 and 0.91**
(the research registry declared as an onward use). Telling the agent the Act in
plain words moves PL-01 by a tenth and nothing else.

**Reading Table 2.** Three columns carry the argument, and none of them is the
compliance score.

*Traps held.* On the four tasks whose wording invites a violation, the agent
held **none, in any of five runs, under either briefing.** Told to reconcile
an invoice "against the diagnosis", it took the diagnosis every time. Told to
"note their insurance policy number" at the registration desk, it took the
policy number and the payer every time — and declared, across runs, retention
of 30 days, 365 days, 3,650 days, or none. Told to "keep a copy for the
research registry", it declared the registry as an onward use in every run and
a year's retention in most. Told the consultant "wants this kept on file for a
year", it declared a year. Our technique held all four, not by being told the
traps existed but because the prose is not an input to it: the field list
comes from the purpose policy and the manifest from the register. The
obligations in the *informed* prompt — the same principles the rules encode,
in plain words — did not change a single trap outcome. A rule reads the law
once, at design time; an agent reads it as one more sentence in a prompt.

*Coverage.* 0.74 in memory, 0.83 on the portal. Given the job in words, the
agent decides for itself what a ward census or a reminder needs, and decides
differently from the policy — a name where the task needs the record number,
an e-mail where it needs the phone, no date of birth for a medication review.
Each substitute is a lawful category, so the compliance score is untouched;
the job is not done as specified. Its excess ratio in memory is now 1.00 —
over eight tasks its over-collection on the summaries is balanced by its
under-collection elsewhere, which is exactly why excess and coverage must be
read together and neither alone.

*Stability.* Put the same brief to the same model five times and it
reproduced its own decision — the same fields and the same manifest structure
— in three of five runs, under either briefing. On the single-patient trace
(`scripts/trace_one_patient.py`) it drops a needed field in some answers and
adds an unneeded one in others to an identical brief. The compliant technique
reproduced itself five of five, as did the baseline: neither samples. A
rule-driven technique is deterministic by construction; an agent's compliance
is a sample from a distribution, and a hospital that deploys one is deploying
the distribution.

The baseline's row is unchanged in kind: 248 distinct fields where the tasks
require 35, an excess ratio of 7.09, paid for on the portal in 440 page loads
against our 74 at the same coverage — the overreach DM-01 penalises, so
compliance and cost move together rather than trading off. The benchmark's
summary line names every case: the baseline pulled more than the purpose
needs; the agent pulled less than the task needs, held no trap, and did not
agree with itself; ours did the job, held the line, and repeated.

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

**One AI agent, one tier, five samples.** The agent results are from a single
provider's free-tier model (`gemini-3.1-flash-lite`), chosen because its daily
request allowance permitted a complete recording in one session; the flagship
model in the same family was capped at twenty requests a day. Five runs per
task is enough to show that decisions vary, not enough to characterise the
distribution. The trap result — none held, in forty runs — is strong enough
that a larger sample is unlikely to reverse it, but a more capable model might
hold some; that is the first thing a second provider would test.

**The traps are ours.** The four trap tasks were written by us, and a critic
may say they were written to be failed. We answer that each is a request a
member of hospital staff could plausibly make in passing, that the purpose and
the needed fields in each are lawful, and that the compliant technique's
immunity is not a tuning but a design property — it never reads the wording.
The wording is available in `scripts/run_benchmark.py` for a reader to judge. The adapters for two further providers exist and record in the
same format; a second provider and a larger sample are the first things to add
when keys and quota allow, and the recordings are designed so that adding them
is a re-run, not a redesign. We do not claim the result generalises across
models; we claim the measurement does.

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
