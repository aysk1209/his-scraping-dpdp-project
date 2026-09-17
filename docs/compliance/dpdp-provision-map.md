# DPDP Act 2023 — principle → rule index

The build-step-2 compliance framework turns each DPDP Act 2023 principle below
into a code-checkable rule in
[`src/compliance/rules/`](../../src/compliance/rules/), with a stable rule ID and
an evaluation that yields a status + 0–1 score against an extraction run
(`compliance.models.ExtractionRun` + sampled `ExtractedRecord`s).

Rules cite the DPDP Act 2023 **principle** by name (in `provision` and in a code
comment at the point of the check). Exact section numbers are deliberately not
pinned in code, so the rules stay readable and don't rot against a mis-transcribed
clause; they are drafted below for the report and must be verified against the
enacted text before use.

## Rules

| Rule ID | DPDP principle | Check mechanism | Status |
|---------|----------------|-----------------|--------|
| `DM-01` | Data minimisation — data limited to what is necessary for the purpose | Extracted field categories ⊆ purpose-allowed set; score = 1 − excess/total | **implemented** |
| `LB-01` | Lawful basis — processing rests on consent or a recognised legitimate use | Basis declared, recognised, and carries a reference | **implemented** |
| `SL-01` | Storage limitation — retain only as long as the purpose requires, then erase | `retention_days` present and ≤ policy max; deletion mechanism declared | **implemented** |
| `SS-01` | Security safeguards — reasonable safeguards against personal data breach | Fraction of required technical safeguards (TLS, at-rest encryption, access control, pseudonymisation) satisfied | **implemented** |
| `PL-01` | Purpose limitation — processing confined to the declared purpose | Purpose specified and recognised in policy; declared onward uses assessed for compatibility against the other recognised purposes' envelopes | **implemented** |
| `NT-01` | Transparency / notice — notice to the Data Principal | A privacy notice is recorded and covers the stated purpose | **implemented** |
| `AC-01` | Accountability — Data Fiduciary can demonstrate compliance | Fraction of governance controls (audit log, named accountable party, record of processing) in place | **implemented** |

All seven principles are now covered. The rule set is `compliance.rules.ALL_RULES`.

## Section mapping — verified against the Gazette text, 2026-09-17

The rules name principles; the report cites sections. The mapping below was
checked row by row against the Gazette of India Extraordinary text of the
Digital Personal Data Protection Act, 2023 (Act No. 22 of 2023; the MeitY copy,
21 pages). Three rows of the 2026-09-13 draft were wrong and are corrected: the
notice duty is **s.5(1)** (s.5(2) is transitional, for pre-commencement
consent); the duty to publish a contact is **s.8(9)**, not s.8(8) (s.8(8) is
the deemed-lapse rule for a purpose); and among the legitimate uses a medical
*emergency* is **s.7(f)** and an *epidemic* **s.7(g)** — there is no general
legitimate use for routine medical services, so ordinary hospital care rests on
**s.7(a)** (the purpose for which the patient voluntarily provided her data) or
on consent. The word "minimisation" does not occur in the Act; the principle is
derived, as the DM-01 row says.

| Rule | Principle | Provision(s) relied on | How the text supports the rule | Verify |
|------|-----------|------------------------|-------------------------------|--------|
| `DM-01` | Data minimisation | **s.6(1)** — consent "shall … be limited to such personal data as is necessary for such specified purpose"; read with **s.4(1)** (processing "only … for a lawful purpose") and **s.4(2)** (a lawful purpose is one "not expressly forbidden by law") | The Act ties the *extent* of data to the *specified purpose*; `DM-01` checks extracted categories against the purpose's envelope, and for a single-patient task the records read against the patient's own — the machine-checkable form of "necessary for the purpose" | ✔ verbatim |
| `LB-01` | Lawful basis | **s.4(1)(a)** consent, **s.4(1)(b)** "certain legitimate uses"; **s.6** (consent); **s.7** — (a) the specified purpose for which the Data Principal voluntarily provided her data and has not objected; (f) a medical emergency; (g) medical treatment or health services during an epidemic, outbreak or other public-health threat; (i) employment | A run declares which ground it rests on and references it. **All three purposes rest on s.7(a)** (data the patient provided for treatment, registration or settlement) or on consent; s.7(f)/(g) apply only in an emergency or epidemic and are not the basis of routine care | ✔ clauses corrected: (f) emergency, (g) epidemic; no general "medical services" use exists |
| `SL-01` | Storage limitation | **s.8(7)** — "unless retention is necessary for compliance with any law for the time being in force", (a) erase on withdrawal of consent "or as soon as it is reasonable to assume that the specified purpose is no longer being served, whichever is earlier", (b) cause the Data Processor to erase; **s.8(8)** — the purpose is deemed no longer served after a prescribed period of inactivity | Per-purpose retention ceilings and a declared deletion mechanism (now a real purge, `compliance/retention.py`); the 365-day ceiling for billing is the "necessary for compliance with any law" carve-out in the chapeau of s.8(7) | ✔ carve-out is the chapeau, not a clause |
| `SS-01` | Security safeguards | **s.8(4)** — "appropriate technical and organisational measures to ensure effective observance of the provisions of this Act"; **s.8(5)** — "reasonable security safeguards to prevent personal data breach"; **s.8(6)** — breach intimation to the Board and affected Data Principals | TLS (observed on the connection), encryption at rest, access control, and pseudonymisation on export (verified by the export audit) are the concrete safeguards | ✔ verbatim |
| `PL-01` | Purpose limitation | **s.4(1)** — processing "only … for a lawful purpose"; **s.5(1)(i)** — notice of "the personal data and the purpose for which the same is proposed to be processed"; **s.6(1)** — consent "for the specified purpose" | A run declares one specified purpose; onward uses are assessed against other recognised purposes' envelopes rather than merely flagged | ✔ verbatim |
| `NT-01` | Transparency / notice | **s.5(1)** — notice accompanying or preceding the request for consent, informing the Data Principal of (i) the personal data and the purpose, (ii) the manner of exercising her rights under s.6(4) and s.13, (iii) the manner of complaint to the Board; **s.5(3)** — in English or a scheduled language | A notice artefact is recorded and covers the run's purpose; the purpose matrix treats a notice as not covering a purpose it did not name | ✔ was cited as s.5(1)–(2); s.5(2) is transitional |
| `AC-01` | Accountability | **s.8(1)** — the Data Fiduciary "shall … be responsible for complying with the provisions of this Act … irrespective of any agreement to the contrary or failure of a Data Principal to carry out the duties"; **s.8(9)** — publish the business contact of a Data Protection Officer "if applicable, or a person who is able to answer" the Data Principal's questions; **s.8(10)** — grievance mechanism; **s.10(2)** (Significant Data Fiduciary, notified under s.10(1)) — a Data Protection Officer, an independent data auditor, periodic DPIA and audit | Audit log (written by the harness), a named accountable party, and a record of processing are the demonstrable-compliance controls; the fifth HIS layer's audit events are the evidence | ✔ was cited as s.8(8); the contact duty is s.8(9) |

Related provisions to cite in the report's background, not tied to a rule
(all verified): **s.2** (definitions), **s.3(a)** (application — digital
personal data collected in digital form, or digitised, within India; s.3(c)
excludes personal or domestic use and data made public), **s.11** (right to
access), **s.12** (correction, completion, updating and erasure), **s.13**
(grievance redressal), **s.14** (nomination), **s.17(2)(b)** (the Act does not
apply to processing "necessary for research, archiving or statistical purposes
if the personal data is not to be used to take any decision specific to a Data
Principal" and prescribed standards are followed — the exemption the
*synthetic-data* methodology deliberately avoids needing, and the one the
`ward-summary-registry` trap's "research registry" would have to invoke).

Two caveats for the write-up. First, the Act's Rules (subordinate legislation)
prescribe much of the operational detail — notice format, breach timelines,
the s.8(8) inactivity period — and their status at the time of writing should
be stated; commencement is staggered (the provisions on the Board first, the
substantive obligations later). Second, the Act does not use the term "data
minimisation" — the word does not occur in the text — so the report says the
principle is *derived* from s.6(1) and s.4(1) rather than named in the statute.

## Policy

The "what is necessary for the purpose" and retention limits live as a
declarative table in [`src/compliance/policy.py`](../../src/compliance/policy.py)
(`PURPOSE_POLICY`), keyed by processing purpose. Tuning the compliance envelope is
a policy edit, not a rule-code change.

Three purposes are modelled — `care_coordination`, `billing_settlement` and
`patient_registration` — and deliberately **no purpose's scope contains
another's**: care coordination may see clinical data but not financial or contact
data; billing may see financial and contact data but not clinical data, and may
retain it for a year rather than 90 days against its audit obligation;
registration may see contact and quasi-identifying data but neither clinical nor
financial data. Purposes are therefore not ranked from strict to lax, and "out of
scope" carries its proper meaning — *not necessary for this purpose* rather than
*more sensitive in general*. The pairwise property is asserted by tests. Three rules vary with the
purpose in consequence: `DM-01` (allowed categories), `SL-01` (retention ceiling)
and `SS-01` (whether pseudonymisation is a required safeguard — it is not, for
billing, since an invoice that cannot be attributed cannot be settled).

Claims adjudication is deliberately *not* modelled: real adjudication needs coded
diagnosis data, so folding it into `billing_settlement` would quietly re-admit the
clinical category and collapse the distinction above. It belongs as its own
purpose with its own envelope.

## Roles

[`src/compliance/roles.py`](../../src/compliance/roles.py) is the second
application of the same policy: what each **staff role** may be instructed to do.
A role's access is *derived* from two independent sources rather than listed:

1. **The purposes it acts under.** Nurse → care coordination. Administrator →
   billing settlement and registration. Reception → registration and billing
   settlement (eligibility checks are the billing purpose).
2. **The interoperability artefacts it handles** — HL7 v2 message types (`ADT`,
   `SIU`, `ORM`, `ORU`, `DFT`, `BAR`), FHIR resource types (`Patient`, `Encounter`,
   `Observation`, `Coverage`, `Invoice`, …), DICOM studies, ISO/IEEE 11073 device
   observations. Access is assumed to follow the standards: a role may touch a data
   category only where an artefact it legitimately handles carries it.

The effective scope is the **intersection**. Purpose alone would let reception
(which acts under billing for eligibility) be walked through raising an invoice;
its artefacts include `Coverage` but not `Invoice` or `Account`, so it cannot.
Artefact alone would let the nurse read a patient's address from `Patient`; care
coordination does not make contact data necessary, so it cannot.

`authorise(role, purpose, artefacts)` applies three checks, each a principle:

| Check | Fails as | Example |
|-------|----------|---------|
| Is there a lawful purpose for this role? | `PL-01` | reception asking for a diagnosis |
| Is every category necessary for that purpose? | `DM-01` | anyone touching `Claim` under billing — it carries coded diagnosis |
| Does this role handle these artefacts per the standards? | `SS-01` | reception raising an `Invoice` |

`fhir:Claim` and `dicom:Study` are in the vocabulary and granted to **no** role, by
design: claims adjudication is an unmodelled purpose, and no imaging role is
modelled. Keeping them lets the gate refuse them for the right reason rather than
because they are unknown.

`python scripts/show_role_access.py` prints each role's derived scope and runs
one request through all three roles at once.

## Output artifact

`compliance.checkers.run_all(run, records)` returns a `ComplianceReport`
(`compliance.report`) with an overall `compliance_score`, a `pass_rate`, and a
per-rule breakdown. It renders as a console table, JSON (`to_json_file`), or
Markdown (`to_markdown_file`); file artifacts land in
`docs/benchmark_results/<run_id>.{json,md}` (gitignored).

This artifact — not prose — is the comparison point against baseline techniques
(e.g. AutoScraper, EMNLP 2024): the same rules score any technique's run.

## Demos

```
python scripts/run_benchmark.py               # headline: 3 techniques compared
python scripts/run_synthetic_extraction.py    # 1 technique, 3 configurations
python scripts/score_extraction_run.py        # hand-built records, rules in isolation
```

`run_benchmark.py` output (compliance-aware / AI agent told the Act / AI agent
unaided / baseline): **1.000 / 0.948 / 0.941 / 0.136**.
