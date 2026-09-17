# Chapter 2 — Background and related work

*Draft 1, 2026-09-15. Target ~1800 words; this draft runs ~2400. Reference
numbers are those of the deck's IEEE list (`tools/build_review_deck.py`,
`REFERENCES`): [1]–[12] from the Review-I survey pool, [13] the Act, [14]–[16]
added 2026-09-15 with DOIs verified. The inherited entries [7], [10], [11] were
completed with full author lists via Crossref on 2026-09-15; [9], which existed
only as an unverifiable repository upload, was replaced by Vorisek et al. 2022
(JMIR Medical Informatics), a systematic review serving the same role. Section
references to the Act were verified against the Gazette text on 2026-09-17, as
in Chapter 3.*

---

Three literatures meet in this work and none of them measures what we set out
to measure. The hospital-informatics literature describes what a hospital
information system *is* and how its parts exchange data (§2.1). The
web-extraction literature describes how to get data out of a web interface and
how to evaluate a technique for doing so (§2.2). The data-protection literature
— and, since 2023, the Act itself — describes what an organisation processing
personal data in India *must* do (§2.3). Between the second and the third there
is a gap: extraction techniques are evaluated on executability, coverage and
cost; obligations are analysed doctrinally or reduced to checklists; and nothing
scores a *technique* on whether it meets them (§2.4). This chapter establishes
each of the three and then states the gap precisely.

## 2.1 Hospital Information Systems

**The five-layer model.** A hospital information system is not one system but
a federation, and the enterprise-architecture literature models it as layers of
function. Purnawan and Surendro [8] apply enterprise-architecture modelling to
HIS structure and give the functional decomposition we adopt, in the form the
codebase treats as canonical:

| Layer | Scope | Representative records |
|---|---|---|
| Patient Administration | front-office patient lifecycle | registration, admit/discharge/transfer, demographics, scheduling |
| Clinical / EHR | care documentation and ordering | encounters, diagnoses, orders, medication, allergies |
| Ancillary / Departmental | result-producing departments | laboratory, imaging, pharmacy |
| Administrative / Financial | business operations | billing, insurance, claims |
| Infrastructure / Integration | cross-cutting | interface engine, master patient index, audit logging |

The fifth layer is structural: it carries no patient-record schema of its own,
and it is where interoperability translation and — in our model — compliance
instrumentation live. We model it as a record set of audit events precisely
because the accountability obligation of §2.3 needs an artefact to point to.
Our decomposition is a working reconstruction rather than a standard; if a real
system's structure differs, the field catalogue of Chapter 5 is the one place
that changes.

**Heterogeneity as the standing obstacle.** The enterprise-architecture view
[8] and the FHIR-in-research literature [9] agree on the practical problem: no
two hospitals' systems are alike, vendors' data models differ, and integration
projects spend most of their effort on mapping — across the 49 studies Vorisek
et al. [9] review, the limitations reported include extra mapping effort where
data come from multiple sources, changes in resource content between FHIR
versions, and platforms implementing only a subset of the resources. It was the objection put to us
at our first review — that a method built against one system would not
transfer — and it shapes Chapter 5's answer: discover structure rather than
declare it, and classify by content rather than by label.

**Interoperability standards.** Four standards carry HIS data between systems,
and each carries different layers. HL7 version 2 is the message standard of
the hospital interior: `ADT` messages for admissions and registrations, `ORM`
and `ORU` for orders and results, `SIU` for scheduling, `DFT` and `BAR` for
charges and accounts. FHIR, the resource-and-REST standard reviewed in [9],
carries the same content as typed resources — `Patient`, `Encounter`,
`Condition`, `MedicationRequest`, `Observation`, `Invoice`, `Coverage`, `Claim`
— and additionally defines `AuditEvent` for the record of who did what, which
has no HL7 v2 counterpart. DICOM carries imaging studies and their metadata;
ISO/IEEE 11073 carries point-of-care device observations. The standards, and
the literature that studies their adoption [9], address *exchange*, not
*lawfulness*: they say how a diagnosis is encoded and transported, and nothing
about whether the party receiving it should have it — the same review notes
that safety and legal matters were major concerns in the studies it covers,
and that a de-identification protocol was needed where patient data were used,
without either being part of what the standard specifies. We use the standards twice — once as the shape of
our exports (Chapter 6), and once, less conventionally, as the vocabulary in
which staff access is expressed: a role may touch a data category only where a
standard-defined artefact it legitimately handles carries it.

## 2.2 Web data extraction

Extraction from web interfaces is a mature field with a recent turn toward
language-model agents, and its evaluation criteria are consistent across the
turn.

**Surveys and taxonomies.** Ruchitaa et al. [1] survey scraping tools and
techniques and provide the taxonomy — static parsing, headless browsers,
API-based, agentic — against which the rest can be placed. The survey has no
domain-specific treatment of hospital systems and no compliance axis; it
evaluates tools on capability.

**Wrapper induction and scraper generation.** AutoScraper [2] is the
representative state of the art: a two-stage language-model agent that uses
the HTML hierarchy and cross-page similarity to generate a reusable scraper,
evaluated on an *executability* metric — whether the generated program runs and
returns the target — and on coverage. Co-Scraper [5] extends the approach with
query-aware DOM pruning and reusable scraper synthesis, reporting F1 of 94.78%
on the standard SWDE benchmark and roughly 90% scraper reuse; its optimisation
target is efficiency. Both are evaluated entirely on what they recover and what
it costs to recover it.

**Agentic and low-cost extraction.** AXE [3] performs zero-shot structured
extraction with DOM-tree pruning and grounded XPath resolution feeding a small
(0.6B-parameter) language model, reaching F1 of 88.1% on SWDE at low cost.
WebLists [4] benchmarks executable language-model agents on 200 tasks over
complex interactive sites, converting agent execution into replayable programs
and lifting recall from 31% to 66%. Neither is applied to credentialed domains
and neither models what the extraction is *for*. AXE was, for a time, the
model for a fourth technique in our benchmark — an agentic extractor — and was
cut on the ground that the contribution lies in the compliance layer, not in
the extraction method; it remains related work.

**Headless browser automation** is the mechanism underneath most of the above
and the one we use: a real browser, driven programmatically, that logs in,
navigates and reads rendered pages as a user would. Gundelach et al. [6]
systematically review bot detection at the major security and web venues over
2020–2025 and map the detection landscape; the review notes that scraping of
*authenticated* portals — the setting here — is under-studied relative to the
open web. The large-scale measurement study of `robots.txt` compliance [7]
finds that scrapers respect the directives selectively and after the fact,
which is the pattern we contrast with: compliance *observed* in scrapers'
behaviour, never *designed into* the technique.

**What the literature evaluates on.** Across [1]–[7] the reported metrics are
executability, precision and recall or F1, coverage, reuse, and cost in tokens
or time. No paper in this pool reports whether the technique took only what its
purpose required, whether the subject was told, or whether the data would be
erased. That is not a criticism of the papers, which set out to solve
extraction; it is the observation that the evaluation vocabulary of the field
has no term for it.

## 2.3 The Digital Personal Data Protection Act, 2023

The Act [13] is India's first comprehensive data-protection statute. It applies
to the processing of digital personal data within India s.3,
places obligations on the *Data Fiduciary* — the party that determines the
purpose and means of processing — in respect of the *Data Principal*, the
person the data is about, and is enforced by a Data Protection Board. A
hospital extracting its own patients' data through a portal is a Data
Fiduciary processing personal data in the Act's sense.

**The obligations as principles.** The Act's core sits in a short run of
sections ss.4–8, and we read seven principles from them, in the
form Chapter 3 turns into rules:

| Principle | Substance | Provision relied on |
|---|---|---|
| Lawful basis | processing rests on consent or a recognised legitimate use | s.4, s.6, s.7 |
| Purpose limitation | processing only for the specified purpose | s.4(1), s.5(1), s.6(1) |
| Data minimisation | data limited to what the purpose requires | derived from s.6(1), s.4(1) |
| Transparency / notice | the Data Principal is told what is processed and why | s.5(1) |
| Storage limitation | erase when the purpose is no longer served | s.8(7) |
| Security safeguards | reasonable safeguards against breach | s.8(4)–(5) |
| Accountability | the Fiduciary can demonstrate compliance | s.8(1), s.8(4), s.8(9), s.10(2) |

**Where the Act differs from the GDPR.** Two differences matter for this work.
First, the Act has no free-standing data-minimisation article; the principle is
*derived* from the limitation of consent to data "necessary for such specified
purpose" read with the lawful-purpose requirement, and the report says so rather
than citing a provision that does not exist. Second, the Act's list of
*legitimate uses* s.7 — grounds on which processing may proceed without
consent: the purpose for which the Data Principal voluntarily provided her data
(s.7(a)), a medical emergency (s.7(f)), and treatment during an epidemic or
other public-health threat (s.7(g)), among others — is the basis on which a
hospital's care and registration purposes
rest, and it is narrower and more enumerated than the GDPR's legitimate-interest
balancing test. The subordinate Rules, which prescribe operational detail —
notice format, breach timelines, retention for specified classes of fiduciary —
were at the time of writing [status to be confirmed], and the report states
their status where it matters.

**The Act in the healthcare literature.** Two recent analyses read the Act for
the healthcare sector. The *Discover Public Health* analysis [10] is a doctrinal
treatment of the obligations as they fall on healthcare entities; the *npj
Digital Medicine* synthesis [11] sets out the challenges of digital data
protection in Indian medical research and healthcare and makes recommendations.
Both are legal and organisational analyses; neither translates an obligation
into a control that a data-collection pipeline could be checked against, and
neither concerns extraction.

## 2.4 Compliance evaluation in the literature, and the gap

Three further strands describe mechanisms we build on, and each stops short of
using the mechanism to evaluate a technique.

**Pseudonymisation.** Cook [14] sets out the tokenisation techniques used to
pseudonymise health identifiers — deterministic tokenisation, which yields the
same token for the same input and so preserves linkage, against referential
tokenisation with keyed, salted, non-reversible hashing, which the author argues
better meets pseudonymisation standards while keeping linkage precise. That is
the mechanism of our export (Chapter 6): keyed tokens, stable within an export,
unlinkable across. The paper describes the mechanism; it does not check that a
given export actually carries tokens rather than raw values, which is what our
audit adds.

**Role-based access control.** de Carvalho Junior and Bandiera-Paiva [15]
review RBAC as used in health information systems and find it inadequate to the
setting: clinical environments need context-sensitive, fine-grained decisions
that static role hierarchies cannot express, so that a permission model based
on role assignment alone both grants too much in some situations and too little
in others. Our role gate (Chapter 6) responds to exactly that finding by not
listing permissions at all — a role's scope is *derived* as the intersection of
the purposes it acts under and the artefacts it handles, and either source alone
is shown to over-grant.

**Audit logs.** Rule, Chiang and Hribar [16] systematically review 85 studies
that use EHR audit logs — the record of who did what in the system — and find
them used to study EHR use, care-team dynamics and clinical workflow. The logs
are treated as research data. None of the reviewed studies uses them for the
purpose the Act's accountability obligation implies: to *demonstrate* that
processing was lawful. Our fifth layer models audit events for that use and
maps them to FHIR `AuditEvent`.

**Checklists and frameworks.** Brown et al. [12] give the most complete
treatment of compliance in web scraping for research: a multi-dimensional
framework covering contract, computer-misuse law, intellectual property,
privacy, institutional review and scientific validity. It is a qualitative
framework — a set of questions a researcher should ask — and it is not, and
does not claim to be, a scored evaluation of a technique.

**The gap, stated.** Extraction techniques [1]–[7] are evaluated on
executability, coverage, reuse and cost. The Act [13] and its healthcare
readings [10]–[11] state obligations doctrinally. The mechanisms by which
obligations are met — tokenisation [14], access control [15], audit logging
[16] — are described individually and never composed into an evaluation. The
one compliance framework for scraping [12] is a checklist. **Nothing in the
literature scores an extraction technique on data-protection compliance, sets
that score beside the technique's cost, or verifies a technique's compliance
claims against its output.** That is the gap this report fills, and Chapter 3
begins by making the obligations executable.

---

*Cross-references to fill in at assembly: Chapter 3 (the rules and the
provision map), Chapter 4 (the cut agentic technique; evaluation metrics as
cost), Chapter 5 (the catalogue; discovery), Chapter 6 (export, roles, audit
layer), Chapter 7 (§7.8).*
