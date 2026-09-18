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

**Techniques.** Compliance-aware (ours); a publicly available model,
`gemini-3.1-flash-lite`, briefed three ways — *unaided*, *told the Act*, and
*told the policy* (the purpose envelope and every field's category in the
prompt: everything ours reads) — each briefing scored as its own technique;
and the unconstrained baseline. A further model of the same family is
recorded on the *told the policy* and *unaided* briefings only, as its daily
allowance permits, and enters as one more row per briefing. Because the agent
is briefed on the canonical catalogue rather than on a particular source, a
recording is a property of the model and replays unchanged against the
in-memory fixture, the portal and the hospital's dataset. Every technique is told the deployment's capability
register (§4.5). The agents' decisions are recorded live (five runs per task
per briefing, field names and manifest choices only) and replayed; the
recordings are committed with the repository, so every agent figure below
reproduces without a key. The recordings used here were made on 2026-09-18 under the current brief
(the record axis and the third briefing included); a first recording of
2026-09-17 under the previous brief gave the same picture on the two original
briefings.

**Tasks.** Each task names a purpose, the job in words, and the minimum
necessary fields for it. The in-memory workload has eight: four plain, and
four *traps* whose wording invites a violation the purpose does not permit
(§4.5). Six are about one patient (`single_subject`; the harness binds the
patient at run time) and two — the census and the reminder run — about a
cohort. The portal workload has four — three plain and one trap, two of them
single-patient — chosen to keep the live demonstration under two minutes.

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

**Table 0.** One row per technique, each AI model at the *told the policy*
briefing — the condition under which it knows everything our technique knows.
This is the view the comparison is read from; Tables 1 and 2 keep every
briefing as evidence. A model recorded on fewer briefings is shown at its best
available one and marked.

| Technique | Compliance | Trap runs held | Coverage | Excess | Record excess | Stable |
|---|---|---|---|---|---|---|
| compliance-aware (ours) | **1.000** | **20 / 20** | 1.00 | 1.00 | 1.00 | **32 / 32** |
| gemini-3.1-flash-lite, told the policy | 0.984 | 10 / 20 | 0.74 | 1.43 | 0.98 | 21 / 32 |
| unconstrained (baseline) | 0.100 | 0 / 20 | 1.00 | 7.77 | 136.4 | 32 / 32 |

**Table 0.** One row per technique, each AI model at the *told the policy*
briefing — the condition under which it knows everything our technique knows.
This is the view the comparison is read from; Tables 1 and 2 keep every
briefing as evidence. A model recorded on fewer briefings is shown at its best
available one and marked.

| Technique | Compliance | Trap runs held | Coverage | Excess | Record excess | Stable |
|---|---|---|---|---|---|---|
| compliance-aware (ours) | **1.000** | **20 / 20** | 1.00 | 1.00 | 1.00 | **32 / 32** |
| gemini-3.1-flash-lite, told the policy | 0.984 | 10 / 20 | 0.74 | 1.43 | 0.98 | 21 / 32 |
| unconstrained (baseline) | 0.100 | 0 / 20 | 1.00 | 7.77 | 136.4 | 32 / 32 |

**Table 0.** One row per technique, each AI model at the *told the policy*
briefing — the condition under which it knows everything our technique knows.
This is the view the comparison is read from; Tables 1 and 2 keep every
briefing as evidence. A model recorded on fewer briefings is shown at its best
available one and marked.

| Technique | Compliance | Trap runs held | Coverage | Excess | Record excess | Stable |
|---|---|---|---|---|---|---|
| compliance-aware (ours) | **1.000** | **20 / 20** | 1.00 | 1.00 | 1.00 | **32 / 32** |
| gemini-3.1-flash-lite, told the policy | 0.984 | 10 / 20 | 0.74 | 1.43 | 0.98 | 21 / 32 |
| unconstrained (baseline) | 0.100 | 0 / 20 | 1.00 | 7.77 | 136.4 | 32 / 32 |

**Table 1.** Compliance per rule, in memory (`benchmark.md`; eight tasks, four
of them traps; five repeats, **every repeat scored** — a cell is the mean over
all forty runs of a technique, not one draw; identical rule set for every
technique). The portal run (`benchmark-portal.md`, four tasks) agrees to
within 0.05 on every technique and is used for the cost columns of Table 2.

| Technique | Score | Rules passed | DM-01 | LB-01 | SL-01 | SS-01 | PL-01 | NT-01 | AC-01 |
|---|---|---|---|---|---|---|---|---|---|
| compliance-aware (ours) | **1.000** | 7/7 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| ai agent: gemini-3.1-flash-lite (told the policy) | 0.984 | 6/7 | 0.89 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| ai agent: gemini-3.1-flash-lite (told the Act) | 0.948 | 5/7 | 0.91 | 1.00 | 0.82 | 1.00 | 0.91 | 1.00 | 1.00 |
| ai agent: gemini-3.1-flash-lite (unaided) | 0.942 | 5/7 | 0.90 | 1.00 | 0.79 | 1.00 | 0.91 | 1.00 | 1.00 |
| unconstrained (baseline) | 0.100 | 0/7 | 0.42 | 0.00 | 0.00 | 0.28 | 0.00 | 0.00 | 0.00 |

**Table 2.** Cost, veracity and resistance. Deterministic columns lead;
wall-clock is hardware-dependent and omitted here (it is in the artefacts).
*Stable* is the number of repeats after the first (eight tasks × four = 32)
that reproduced the first run's decision — fields and manifest structure —
with, in brackets, the tasks reproduced in every repeat; *veracity* is
declared controls the register backs ÷ declared; *traps held* counts trap
**runs** (four tasks × five repeats = 20) on which nothing out of scope was
pulled, no onward use was declared and retention stayed within the ceiling,
with the tasks held in every repeat in brackets. Coverage and excess are
micro-averaged over every run.

| Source | Technique | Compliance | Substantiated | Veracity | Traps held (runs / tasks) | Coverage | Excess ratio | Record excess | Distinct / needed | Page loads | Stable (repeats / tasks) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| in memory | compliance-aware | **1.000** | 1.000 | 1.00 | **20 / 20** (4 / 4) | 1.00 | 1.00 | **1.00** | 35 / 35 | n/a | **32 / 32** (8 / 8) |
| in memory | flash-lite, told the policy | 0.984 | 0.984 | 1.00 | 10 / 20 (2 / 4) | 0.74 | 1.43 | 0.98 | 50 / 35 | n/a | 21 / 32 (5 / 8) |
| in memory | flash-lite, told the Act | 0.948 | 0.948 | 1.00 | **0 / 20** (0 / 4) | 0.69 | 1.06 | 0.95 | 37 / 35 | n/a | 19 / 32 (4 / 8) |
| in memory | flash-lite, unaided | 0.942 | 0.942 | 1.00 | **0 / 20** (0 / 4) | 0.67 | 1.06 | 0.98 | 37 / 35 | n/a | 18 / 32 (3 / 8) |
| in memory | unconstrained | 0.100 | 0.100 | 1.00 | 0 / 20 (0 / 4) | 1.00 | 7.77 | 136.4 | 272 / 35 | n/a | 32 / 32 (8 / 8) |
| portal | compliance-aware | 1.000 | 1.000 | 1.00 | 1 / 1 | 1.00 | 1.00 | 1.00 | 18 / 18 | **32** | — |
| portal | flash-lite, told the policy | 0.990 | 0.990 | 1.00 | 0 / 1 | 0.83 | 1.83 | 1.25 | 33 / 18 | 35 | — |
| portal | flash-lite, told the Act | 0.988 | 0.988 | 1.00 | 0 / 1 | 0.72 | 1.28 | 1.25 | 23 / 18 | 33 | — |
| portal | flash-lite, unaided | 0.988 | 0.988 | 1.00 | 0 / 1 | 0.72 | 1.39 | 1.25 | 25 / 18 | 34 | — |
| portal | unconstrained | 0.114 | 0.114 | 1.00 | 0 / 1 | 1.00 | 7.56 | 50.0 | 136 / 18 | **440** | — |

**Reading Table 1.** The gap between the compliant technique and the baseline is
0.900 on the same seven rules. The baseline fails every rule: its DM-01 of 0.42
is the set-containment score (of six categories pulled, three are outside the
purpose's scope on every task) halved, on the six single-patient tasks, by the
record axis — it reads 2,000 records over the workload where the patients'
own would be 15; its SS-01 of 0.28 is one safeguard of four.

The AI agents' rows are the finding. On the four plain tasks a publicly
available model is close to ours on compliance as scored — it declares a
lawful basis, retention, a deletion mechanism, encryption, a notice and an
accountable party, and, told the register, cites each by its identifier
(veracity 1.00 in every run). The gap on paperwork is small and honest, and
the report states it as such: supply a current model with the facts and it
uses them. What pulls the score down to 0.948 and 0.942 is the four trap
tasks, and the per-rule columns say exactly how: **DM-01 0.91 and 0.90**
(clinical data taken for billing, financial data at the desk), **SL-01 0.82
and 0.79** (a year's retention declared against a 90-day ceiling, and at the
desk, in two runs, 3,650 days against 180), **PL-01 0.91** (the research
registry declared as an onward use). Telling the agent the Act in plain words
moves SL-01 by three hundredths and nothing else.

Telling it the *policy* — the very table our technique reads — moves more, and
in a specific way. SL-01 and PL-01 go to **1.00**: every retention it declares
now sits exactly at the purpose's ceiling, and the registry is no longer
declared as an onward use. DM-01 goes *down*, to **0.89**: with the permitted
categories and every field's category in front of it, it still takes the
diagnosis to reconcile the invoice in five runs of five and the insurance
number at the desk in five of five — and takes more fields overall (excess
1.43 against 1.06). The agent follows the policy's numbers and not its
categories: a sentence in the request ("cross-check it against the patient's
diagnosis") outranks a table in the same prompt. Because every repeat is
scored, a per-task cell in the artefact carries its range where the runs
disagreed: `ward-summary-registry` under the first two briefings is 0.835 with
runs between 0.82 and 0.89 — the same brief, scored five times.

**Are the weights doing the work?** Every rule weighs 1.0 in the committed
score, and a reader may ask whether another weighting would reorder the
techniques. `tools/weight_sweep.py` re-scores the per-rule means under
twenty-one alternatives — equal; each rule doubled in turn; each rule dropped
in turn; minimisation and purpose tripled; the paperwork rules tripled;
safeguards and storage tripled — and writes `weight-sweep.md`. No weighting
moves the compliant technique from first or the baseline from last. The only
movement is between the two agent briefings, which sit within 0.007 of each
other under equal weights and change sides under two schemes (dropping PL-01;
tripling SS-01 and SL-01): a tie changing sides, and the table marks it as
such. The ranking the report rests on is not a property of the weights.

**Reading Table 2.** Three columns carry the argument, and none of them is the
compliance score.

*Traps held.* On the four tasks whose wording invites a violation, the agent
held **none, in any of twenty runs, unaided or told the Act** — forty trap
runs, none held. Told the policy it held **ten of twenty**: the two traps that
turn on a number or a declaration (the year's retention, the registry as an
onward use) in every run, the two that turn on taking a field (the diagnosis
for billing, the insurance number at the desk) in none. Told to reconcile
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

*Records.* The record axis is where the baseline's cost becomes visible on the
portal: for the single-patient tasks our technique goes through the search box
and loads one page per module, the baseline every page of every module — 32
page loads against 440 over the four-task workload, a factor of fourteen, at
identical coverage. In memory the baseline's record excess is 136×: every
patient's record, fifty times over, to answer for one. Whether an agent scopes
its pull is a decision it is asked to make (`scope`), and this model made it
correctly in every run under every briefing — its record excess is 0.95–0.98
in memory (it sometimes omits a layer the task needs) and 1.25 on the portal
(it adds one). On the record axis, at least, a current model and a rule agree.

*Coverage.* 0.67 unaided, 0.69 told the Act and 0.74 told the policy in
memory; 0.72–0.83 on the portal. Given the job in words, the agent decides
for itself what a ward census or a reminder needs, and decides differently
from the policy — a name where the task needs the record number, an e-mail
where it needs the phone, no date of birth for a medication review. Each
substitute is a lawful category, so the compliance score is untouched; the
job is not done as specified. Its excess ratio in memory is 1.06 under the
first two briefings — over-collection on the summaries nearly balanced by
under-collection elsewhere — and 1.43 told the policy, which is exactly why
excess and coverage must be read together and neither alone.

*Stability.* Put the same brief to the same model five times and it
reproduced its first decision — the same fields and the same manifest
structure — in 18 of 32 repeats unaided, 19 of 32 told the Act and 21 of 32
told the policy; every repeat agreed on three, four and five of the eight
tasks respectively. Handing it the policy made it steadier, not stable. On the
single-patient trace (`scripts/trace_one_patient.py`) it drops a needed field
in some answers and adds an unneeded one in others to an identical brief. The
compliant technique reproduced itself 32 of 32, as did the baseline: neither
samples. Sampling was at the provider's default — no temperature or seed was
set, and the recording says so — which is how a hospital calling the public
API would receive it. A
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

The export is also *scheduled*: beside the files goes a retention sidecar
naming the run, the purpose, the 30 days the manifest declared and the date
after which the files must go, and the pipeline's last stage runs the purge
as of the day after on a copy of the export, erasing three files and writing
the erasure to the audit log
(`test_exports_are_scheduled_for_erasure_and_purged_when_due`). The baseline's
export, which declares no retention, gets a sidecar that says it cannot be
scheduled — storage limitation failing in the artefact, not only in the score.

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
distribution; every run is scored, so the tables report means and ranges, not
a draw. The trap result — none held, in forty trap runs — is strong enough
that a larger sample is unlikely to reverse it, but a more capable model might
hold some; that is the first thing a second provider would test.

**The agent was shown the policy — and the result is reported.** A critic
may say the traps measure what the agent was not told rather than what it
cannot do. The third briefing answers that directly: handed the purpose
envelope and every field's category, with the instruction that the policy is
binding whatever the wording asks, the agent held the two traps that turn on a
number or a declaration and failed the two that turn on taking a field, in
every run. We do not claim it *cannot* be prompted into holding those too —
a still more insistent prompt might — only that the policy stated as plainly
as our technique reads it was not enough, and that a rule-driven technique
needs no insistence because the wording is not an input to it.

**The register is ours.** The capability register that veracity checks
against was written by us, and a critic may say a declaration checked against
our own list proves little. Two answers. First, four of its controls are not
declared but *demonstrated*: the pipeline observes the scheme of the
connection it read over and a manifest claiming TLS over plain http is marked
unsubstantiated whatever the register says (`test_a_transport_claim_is_checked_against_what_was_observed`);
every run is written to an audit log by the harness at the metering boundary,
not by the technique; the export audit searches the written files for raw
identifiers; and every export carries a retention sidecar that the purge
erases and logs. The benchmark reports, per technique, how many substantiated
claims rest on that evidence and how many on the register's word (sixteen and
twenty-eight per technique on the portal run). Second, the remaining controls
— encryption at rest, access control on the store, the notice, the officer,
the record of processing — are attested by any deployment; no extraction
pipeline can produce evidence of a notice on a wall, and we do not claim to.

**The traps are ours.** The four trap tasks were written by us, and a critic
may say they were written to be failed. We answer that each is a request a
member of hospital staff could plausibly make in passing, that the purpose and
the needed fields in each are lawful, and that the compliant technique's
immunity is not a tuning but a design property — it never reads the wording.
The wording is available in `scripts/run_benchmark.py` for a reader to judge.
The adapters for two further providers exist and record in the same format; a
second provider and a larger sample are the first things to add when keys and
quota allow, and the recordings are designed so that adding them is a re-run,
not a redesign. We do not claim the result generalises across models; we
claim the measurement does.

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
of §3.3 was checked against the Gazette text on 2026-09-17; three references
in the first draft were wrong and are corrected (Chapter 3).
No result in this chapter depends on a section number.

**Wall-clock.** Reported, not relied upon; see §7.1.

---

*Cross-references to fill in at assembly: Chapter 3 (§3.3 rules; §3.4 policy and
non-nesting), Chapter 4 (§4.2 techniques; §4.3 metrics; §4.4 the guard rail and
the source ceiling), Chapter 5 (portal fixture; label map; dataset adapter and
handling gate), Chapter 6 (shaping and audit; roles; the assistant).*
