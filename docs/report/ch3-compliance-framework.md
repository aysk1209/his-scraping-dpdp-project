# Chapter 3 — The compliance framework

*Draft 1, 2026-09-15. Target ~2500 words; this draft runs ~3300 and should lose
about a quarter at the second pass — the rule subsections (§3.3) can each drop
their *Findings* line, and §3.4's justification of each policy entry can move to
a table footnote. Every DPDP section reference below was verified on
2026-09-17 against the Gazette text of Act No. 22 of 2023 (the MeitY copy of
the Gazette of India Extraordinary, Part II, s.1); three references in the
first draft were wrong and are corrected here — the notice provision is s.5(1)
alone (s.5(2) is transitional), the contact-publication duty is s.8(9) not
s.8(8), and the medical legitimate uses are s.7(f) (emergency) and s.7(g)
(epidemic), with routine care resting on s.7(a). The mapping is in
`docs/compliance/dpdp-provision-map.md`.*

---

This chapter presents the core contribution: a way of treating compliance with
the Digital Personal Data Protection Act, 2023 as a *measurable property of an
extraction technique* rather than as a property asserted about a system after the
fact. We show that seven principles of the Act can each be written as an
executable rule over a structured declaration of an extraction run, that a small
policy table makes the Act's central phrase — "necessary for the specified
purpose" — machine-checkable, and that the result is a number which the same
harness produces for any technique, ours or a baseline, on equal terms.

The framework has five parts, presented in the order in which data flows through
them: the manifest a run must declare about itself (§3.1); the valueless form in
which what it extracted is represented (§3.2); the seven rules (§3.3); the purpose
policy that three of those rules read from (§3.4); and the aggregation that turns
seven rule results into one report (§3.5).

## 3.1 The extraction manifest

A compliance rule cannot inspect "a scrape" in the abstract. It has to inspect
something structured: what was extracted, for what purpose, on what basis, under
what safeguards, and for how long it will be kept. We therefore require every
extraction run to produce a **manifest** — a declaration of itself — and it is
the manifest, together with a sample of what came out, that the rules score.

The manifest is the `ExtractionRun` model (`src/compliance/models.py`). It
declares:

| Field | What it states | Principle it serves |
|---|---|---|
| `purpose`, `purpose_specified` | The one processing purpose this run is for, and that one was in fact specified | purpose limitation |
| `secondary_uses` | Any onward uses beyond that purpose (normally empty) | purpose limitation |
| `lawful_basis` | Consent or a legitimate use, with a reference to the consent artefact or the specific use relied on | lawful basis |
| `retention_days`, `deletion_mechanism` | How long the extracted data is kept, and the route by which it is erased | storage limitation |
| `security` | A `SecurityPosture`: transport encryption, encryption at rest, access control on the extracted store, pseudonymisation of direct identifiers on export | security safeguards |
| `notice` | A reference to the privacy notice given to the Data Principal, whether it covers this purpose, and whether a machine-readable form exists | transparency / notice |
| `governance` | Whether the run is audit-logged, who is accountable, whether a record of processing is kept | accountability |

Two design decisions deserve justification.

**We score the declaration, not the intention.** A technique that pulls the right
fields for the right reason but declares nothing about retention or notice scores
poorly under our rules, and that is deliberate. The Act's obligations on a Data
Fiduciary are obligations to *do and be able to show* certain things — give
notice, keep data no longer than needed, be able to demonstrate compliance
s.8(1). An extraction pipeline that cannot state its own retention
period has no way to honour a storage-limitation obligation, whatever its author
intended. Scoring the manifest therefore scores the thing that the law actually
constrains. It also has a practical consequence for benchmarking: every technique
under test must produce a manifest, so "compliance-aware" becomes a property of a
technique's *design* — what it declares and how it constrains itself — rather than
a label we attach to it.

**The manifest is the same shape for every technique.** Our compliant technique,
the AI agents of Chapter 4, and the unconstrained baseline all emit an
`ExtractionRun`; an agent fills it in as it sees fit, the baseline leaves most
of it empty. This is what allows
a single rule set to compare them without special cases, and it is the property
that makes the benchmark of Chapter 7 a fair one — no rule knows which technique
it is scoring.

## 3.2 Valueless records: scoring categories, never values

The second input to the rules is a sample of what the run produced. Here we made a
choice that shapes everything downstream: **the rules never see a value.** An
`ExtractedRecord` carries only the HIS layer it came from and the *set of
categories* of the fields it contains. A registration row with a medical record
number, a name, a date of birth and a ward becomes
`{direct_identifier, quasi_identifier, administrative}` and nothing more.

Six categories are enough for the checks the Act requires:

| Category | Examples in the field catalogue |
|---|---|
| `direct_identifier` | medical record number, full name, phone number |
| `quasi_identifier` | date of birth, sex, postal code |
| `clinical` | diagnosis, medication, laboratory result, allergy, specimen, imaging modality |
| `financial` | invoice number, billed amount, insurance policy number, payer |
| `administrative` | ward, admission and encounter times, attending clinician, order and audit-event identifiers |
| `contact` | postal address, e-mail address |

The mapping from a field name to its category is a single catalogue
(`data_synthetic/catalogue.py`), keyed by HIS layer; the same catalogue drives the
synthetic generator, the per-layer schemas, the interoperability shaping, and —
as Chapter 5 shows — the crawler's inference of which layer a portal module
belongs to. There is one place to change if a real hospital's structure differs.

Three things follow from scoring categories rather than values.

First, **benchmark artefacts carry no personal data.** Every report, JSON file
and table in `docs/benchmark_results/` can be committed, shared and printed
without a handling question arising, because nothing in them is a value. For a
project whose contribution is data-protection compliance this is not a
convenience; it is the minimum consistency we owe the subject. (The handling gate
for a real hospital export, described in Chapter 5, is the complement: the values
that *do* exist are kept out of the repository by construction.)

Second, **the framework is HIS-agnostic.** The rules do not know what a diagnosis
looks like, what format a medical record number takes, or which vendor's schema
produced a row. They know that a category is or is not necessary for a purpose.
A different hospital, a different system, or a different country's field
vocabulary changes the catalogue and nothing else.

Third, the choice fixes what the rules *can* check. Minimisation, purpose scope
and the conditional pseudonymisation requirement are category questions and are
checked directly. Whether pseudonymisation was *actually applied* to the output is
a value question, and it is checked elsewhere — by the export audit of Chapter 6,
which inspects the shaped HL7 v2 and FHIR artefacts for raw identifiers. The rule
scores the declaration; the audit verifies the behaviour. We return to this
division in §3.3.4.

## 3.3 The seven rules

Each rule is a class with a stable identifier, a title, a `provision` string
naming the principle it enforces, and one method, `evaluate(run, records)`, which
returns a status (`pass`, `fail`, or `not_applicable`), a score in [0, 1], and a
list of plain-language findings. The findings are not decoration: they are what a
reviewer reads to learn *why* a run scored as it did, and every failure names its
cause.

The seven rules were chosen so that each exercises a **distinct check mechanism**.
Set containment, declaration validation, a numeric bound, a fraction of required
controls, a compatibility assessment, a coverage test and a governance checklist
are different kinds of check, and together they cover the shapes an obligation in
the Act can take. We present each as principle → provision → check → scoring →
findings.

### 3.3.1 DM-01 — Data minimisation

*Principle.* Personal data is limited to what is necessary for the specified
purpose.

*Provision.* The Act has no free-standing minimisation article. The principle is
derived from the requirement that consent be "limited to such personal data as is
necessary for such specified purpose" s.6(1), read with the
requirement that processing be for a lawful purpose s.4(1). The
report should say "derived from", not "named in".

*Check.* Minimisation has two axes, and the rule checks both. On the **field
axis**, take the union of categories across all extracted records and test it
for containment in the purpose's allowed set from the policy (§3.4) — the
machine-checkable form of "necessary for the purpose". On the **record axis**,
for a task about a single patient, compare the records read with the records
that are the patient's own: a summary of one patient does not need every
patient's diagnosis, whatever the fields. The record counts are written into
the manifest by the benchmark harness from its meter (`ExtractionRun.scope`),
not by the technique — the technique cannot vouch for its own restraint.

*Scoring.* Field axis: `1 − |excess| / |extracted|`, where excess is the set of
categories outside the envelope; a run that pulls six categories of which two
are out of scope scores 0.67, a run entirely within scope 1.0. Record axis,
when the task is about one patient: `necessary / pulled`, capped at 1.0. The
rule's score is the field score alone for a cohort task and the mean of the
two for a single-patient task, so a baseline that reads every patient's record
to answer for one is halved on that task even where its categories are lawful.
With no records the rule is `not_applicable`, so an empty extraction cannot
score well by extracting nothing — the coverage guard rail of Chapter 4 closes
the same door from the cost side.

*Findings.* One line per out-of-scope category, a summary count, and for a
single-patient task the records read against the records necessary — "50
records read where 2 were necessary: 48 other patients' records taken".

### 3.3.2 LB-01 — Lawful basis for processing

*Principle.* Personal data is processed only on a recognised ground: the Data
Principal's consent, or a legitimate use.

*Provision.* s.4(1)(a)–(b), with consent at s.6 and the "certain legitimate
uses" at s.7. The Act lists no general legitimate use for the provision of
medical services: s.7(f) covers a medical emergency and s.7(g) treatment during
an epidemic or other public-health threat, and neither describes routine care.
In the hospital setting, therefore, care coordination, registration and billing
all rest on s.7(a) — processing for the specified purpose for which the Data
Principal voluntarily provided her personal data — or on consent under s.6.
The register's `LU-CARE`, `LU-REG` and `LU-BILL` entries are worded
accordingly, and the informed briefing given to the AI agent was corrected in
the same pass (§4.2.2).

*Check.* A basis is declared; it is of a recognised type; and it carries a
reference — the consent artefact for consent, the specific legitimate use for a
legitimate use.

*Scoring.* 0.0 with no basis; 0.5 with a basis but no reference (the run knows its
ground but cannot point to it); 1.0 otherwise. A basis that cannot be referenced
is, for accountability purposes, half a basis.

### 3.3.3 SL-01 — Storage limitation

*Principle.* Personal data is retained only as long as the purpose requires, then
erased; a route to erasure exists.

*Provision.* s.8(7)(a): erase personal data "upon the Data Principal
withdrawing her consent or as soon as it is reasonable to assume that the
specified purpose is no longer being served, whichever is earlier", and
s.8(7)(b): cause any Data Processor to do the same; the whole sub-section is
subject to the opening words "unless retention is necessary for compliance with
any law for the time being in force". That carve-out — in the chapeau of
s.8(7), not a clause of its own — is what supports the longer ceiling for
billing in §3.4. s.8(8) adds that the purpose is deemed no longer served after
a prescribed period of inactivity by the Data Principal.

*Check.* Two independent halves: a retention period is declared and does not
exceed the purpose's ceiling; and a deletion mechanism is declared.

*Scoring.* Each half is worth 0.5. Missing or excessive retention loses one
half; a missing deletion mechanism loses the other. The baseline, which declares
neither, scores 0.0; a run that declares a period within limit but no way to
erase scores 0.5.

*Findings.* The declared period against the ceiling, and the mechanism or its
absence.

### 3.3.4 SS-01 — Security safeguards

*Principle.* Reasonable technical and organisational safeguards protect personal
data against breach.

*Provision.* "Appropriate technical and organisational measures"
s.8(4) and "reasonable security safeguards to prevent personal
data breach" s.8(5).

*Check.* A checklist of concrete safeguards: transport encryption, encryption at
rest, and access control on the extracted store are always required. A fourth —
**direct identifiers pseudonymised on export** — is required *only when* the
purpose policy calls for it *and* direct identifiers were actually extracted. This
conditional is the point at which the manifest, the records and the policy meet
in a single rule, and it matters for fairness: a billing run, whose purpose
forbids pseudonymisation because an unattributable invoice cannot be settled, is
scored against three safeguards, not four, and is not marked down for a
safeguard that would defeat its purpose.

*Scoring.* The fraction of required safeguards in place. Our compliant technique
declares all four; the baseline declares transport encryption only and scores
0.25 under care coordination.

*The declaration–behaviour division.* SS-01 scores whether pseudonymisation is
*declared*. Whether it *happened* is verified by the export audit of Chapter 6:
after the run's rows are shaped into HL7 v2 and FHIR, the audit searches the
artefacts for every raw direct-identifier value the run extracted. For the
compliant technique it finds none; for the baseline it finds all of them. The rule
and the audit together turn a manifest claim into a verified property of the
output, which is stronger than either alone.

### 3.3.5 PL-01 — Purpose limitation

*Principle.* Personal data is processed only for the specified purpose; onward
uses require their own basis.

*Provision.* Processing "only for a lawful purpose" s.4(1);
notice of "the personal data and the purpose" s.5(1)(i); consent
"for the specified purpose" s.6(1).

*Check.* Three questions. Was a specific purpose declared at all? Is it one the
policy recognises? And if onward uses were declared, are they *compatible*?

*The compatibility assessment.* This is the part of the rule that could not be
built while only one purpose was modelled, and it is the reason the framework
needed at least two. An onward use that names a recognised purpose can be
assessed rather than merely flagged: if the categories already extracted sit
inside that purpose's envelope too, the further processing is compatible and the
failure is a paperwork gap — it still needs its own basis and notice. If they do
not, the onward use would carry data outside its own purpose's scope, which is
the harder failure. An onward use the policy does not recognise cannot be
assessed at all and is treated as the harder failure by default: an unassessable
use is not a safe one.

*Scoring.* 0.0 with no specified or unrecognised purpose; 1.0 for a single
purpose with no onward uses; 0.5 when every onward use is compatible; 0.25 when
any is incompatible or unassessable. Onward uses never pass — each needs its own
declared basis — but the score distinguishes a gap from a breach.

### 3.3.6 NT-01 — Transparency / notice

*Principle.* The Data Principal is told what personal data is processed and for
what purpose.

*Provision.* s.5(1): a notice accompanying or preceding the request for
consent, informing the Data Principal of (i) the personal data and the purpose,
(ii) the manner of exercising her rights under s.6(4) and s.13, and (iii) the
manner of complaint to the Board; s.5(3): available in English or a scheduled
language. (s.5(2), which the first draft cited, is the transitional provision
for consent given before commencement.)

*Check.* A notice artefact is recorded, and it covers the run's purpose. A
machine-readable form is noted but not required.

*Scoring.* 0.0 with no notice; 0.5 with a notice that does not cover this
purpose; 1.0 otherwise.

*A consequence used deliberately.* When the purpose matrix of Chapter 7 re-judges
one extraction under every purpose, the notice is treated as *not covering* any
purpose other than the one it named. That is not an adjustment made to produce a
result; it is what a notice is. A notice that told the patient their data would
be used for care does not cover billing, and NT-01 says so under every purpose
but the declared one.

### 3.3.7 AC-01 — Accountability

*Principle.* The Data Fiduciary can demonstrate compliance.

*Provision.* Responsibility for compliance "irrespective of any agreement to the
contrary" s.8(1); "appropriate technical and organisational measures to ensure
effective observance" s.8(4); publication of the business contact of a Data
Protection Officer, "if applicable, or a person who is able to answer" the Data
Principal's questions s.8(9); a grievance mechanism s.8(10); and, for a
Significant Data Fiduciary, a Data Protection Officer, an independent data
auditor and periodic Data Protection Impact Assessment and audit s.10(2) —
a status the Central Government notifies under s.10(1), so whether a hospital
is one is a fact about the deployment, not the Act.

*Check.* Three governance controls: the run is audit-logged; a named accountable
party is recorded; a record of processing is kept.

*Scoring.* The fraction in place. The compliant technique names the hospital's
Data Protection Officer and satisfies all three; the baseline none.

*The fifth HIS layer as evidence.* Chapter 5 models the Infrastructure /
Integration layer as a set of audit events — who did what, when, to which
record. That layer exists in the model for this rule: an audit log is the
artefact by which a fiduciary demonstrates compliance. It is also personal data,
because it names the record it concerns, which is why it is in the catalogue and
not treated as exempt.

## 3.4 The purpose policy

Three rules — DM-01, SL-01 and SS-01 — do not carry their thresholds in code.
They read them from a declarative table, `PURPOSE_POLICY`
(`src/compliance/policy.py`), keyed by processing purpose. For each purpose the
table states the categories that are necessary for it, the maximum retention, and
whether pseudonymisation of identifiers is a required safeguard. Tuning the
compliance envelope is a policy edit, not a rule-code change, and the "what is
allowed" is inspectable in one place — which is itself a legibility property a
reviewer can check.

Three purposes are modelled:

| Purpose | Necessary categories | Retention ceiling | Pseudonymise? | Legitimate use relied on |
|---|---|---|---|---|
| `care_coordination` | direct identifier, quasi-identifier, clinical, administrative | 90 days | yes | provision of medical services |
| `billing_settlement` | direct identifier, contact, financial, administrative | 365 days | no | settlement of amounts due for services provided |
| `patient_registration` | direct identifier, quasi-identifier, contact, administrative | 180 days | no | registration and scheduling for provision of services |

Each entry is justified by necessity, not sensitivity. Billing may see contact
data because a bill has to be delivered somewhere; care may not, because
coordinating treatment does not require an address. Billing keeps data for a
year because financial records are retained against audit obligations — a longer
retention is a different necessity, not laxity. Billing does *not* pseudonymise,
because an invoice that cannot be attributed to a payer cannot be settled;
registration does not, because identifying the person at the desk is the
purpose. The policy therefore makes billing look *weaker* on SS-01's inputs while
being no less compliant, and that is correct: the rule scores what the purpose
requires.

**Non-nesting is the load-bearing property.** No purpose's scope contains
another's. Care has clinical data that billing and registration lack; billing has
financial data that the other two lack; registration has contact data that care
lacks and quasi-identifiers that billing lacks. Every pair differs in *both*
directions. The consequence is that purposes are not ranked from strict to lax,
and "out of scope" carries its proper meaning — *not necessary for this purpose*
rather than *more sensitive in general*. An extraction lawful under care
coordination is unlawful under billing (clinical data is out of scope) and an
extraction lawful under billing is unlawful under care (financial and contact
data are out of scope). Purpose limitation, as the Act states it, is exactly this
relativity: lawfulness is a property of data *and* purpose together. A nested
policy — where each purpose merely permits a superset of the last — could only
ever demonstrate "less is more compliant", which is data minimisation restated,
not purpose limitation. The property is asserted by a test for every pair of
purposes, so a fourth purpose cannot quietly break it.

**Claims adjudication is deliberately unmodelled.** Real insurance adjudication
needs coded diagnosis data. Folding it into `billing_settlement` would re-admit
the clinical category to billing's envelope and collapse the distinction above.
If it is modelled, it is modelled as its own purpose with its own envelope. The
same reasoning is why the FHIR `Claim` resource, which carries diagnosis codes, is
in the interoperability vocabulary but granted to no role (Chapter 6).

## 3.5 Aggregation: the compliance report

`checkers.run_all(run, records)` evaluates all seven rules and returns a
`ComplianceReport`. Its overall **compliance score** is the weighted mean of the
applicable rules' scores; every rule currently carries weight 1.0, so in practice
it is the arithmetic mean, and rules that return `not_applicable` are excluded
from both numerator and denominator rather than counted as passes. Alongside the
score the report carries the number of rules passed, a pass rate, the per-rule
results with their findings, a summary of what was extracted (records, layers,
how many records carried each category, and which categories fell outside the
policy), and — so that a report file can be read on its own — the manifest facts
it was scored under: purpose, lawful basis, retention.

The report renders three ways: a console table for demonstrations, JSON for
downstream analysis, and Markdown for direct inclusion in this document. The
tables in Chapter 7 are those files.

Two properties of the aggregation matter for the benchmark. First, the score is
**bounded and comparable**: two runs against different purposes, different
techniques or different data still score on the same [0, 1] scale over the same
seven rules, so a table of techniques is a like-for-like comparison. Second, the
score is **decomposable**: a run's 0.976 is not an opaque number but a row of
seven, each with findings, and the per-rule columns in Chapter 7 are where the
behaviour of each technique is actually visible — an AI agent's perfect LB-01,
SS-01 and NT-01 beside its 0.81 on SL-01 and 0.92 on DM-01 says precisely
where it was talked past the purpose, in one row.

We do not claim that the weights are the right ones. We claim that they are
explicit, that changing them is a one-line edit to a rule, and that every number
we report can be recomputed by anyone with the repository. For a compliance
metric, that reproducibility is the property that matters most; the weighting is
a parameter of the study, stated rather than hidden.

---

*Cross-references to fill in at assembly: Chapter 4 (techniques and the cost
axis; the coverage guard rail), Chapter 5 (the field catalogue and layer
inference; the handling gate), Chapter 6 (the export audit; roles and the
`Claim` decision), Chapter 7 (benchmark and purpose-matrix tables).*
