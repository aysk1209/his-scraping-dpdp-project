# Appendices

*Draft 1, 2026-09-23. Appendices A–D are generated from the code and the
provision map by `python tools/report_tables.py` (the blocks between
`<!-- table:… -->` markers are not edited by hand), so they cannot drift from
what the pipeline actually enforces. Appendix E is the reproducibility guide.*

---

## Appendix A — The DPDP section mapping

Each rule names a principle in code; the sections it relies on are pinned here,
verified against the Gazette text of the Digital Personal Data Protection Act,
2023 on 2026-09-17 (three corrections from the first draft are recorded in
Chapter 3). The Act has no free-standing data-minimisation article; DM-01 is
derived from s.6(1) read with s.4(1). Source: `docs/compliance/dpdp-provision-map.md`.

<!-- table:mapping -->
| Rule | Principle | Provision(s) relied on | How the text supports the rule | Verify |
|------|-----------|------------------------|-------------------------------|--------|
| `DM-01` | Data minimisation | **s.6(1)** — consent "shall … be limited to such personal data as is necessary for such specified purpose"; read with **s.4(1)** (processing "only … for a lawful purpose") and **s.4(2)** (a lawful purpose is one "not expressly forbidden by law") | The Act ties the *extent* of data to the *specified purpose*; `DM-01` checks extracted categories against the purpose's envelope, and for a single-patient task the records read against the patient's own — the machine-checkable form of "necessary for the purpose" | ✔ verbatim |
| `LB-01` | Lawful basis | **s.4(1)(a)** consent, **s.4(1)(b)** "certain legitimate uses"; **s.6** (consent); **s.7** — (a) the specified purpose for which the Data Principal voluntarily provided her data and has not objected; (f) a medical emergency; (g) medical treatment or health services during an epidemic, outbreak or other public-health threat; (i) employment | A run declares which ground it rests on and references it. **All three purposes rest on s.7(a)** (data the patient provided for treatment, registration or settlement) or on consent; s.7(f)/(g) apply only in an emergency or epidemic and are not the basis of routine care | ✔ clauses corrected: (f) emergency, (g) epidemic; no general "medical services" use exists |
| `SL-01` | Storage limitation | **s.8(7)** — "unless retention is necessary for compliance with any law for the time being in force", (a) erase on withdrawal of consent "or as soon as it is reasonable to assume that the specified purpose is no longer being served, whichever is earlier", (b) cause the Data Processor to erase; **s.8(8)** — the purpose is deemed no longer served after a prescribed period of inactivity | Per-purpose retention ceilings and a declared deletion mechanism (now a real purge, `compliance/retention.py`); the 365-day ceiling for billing is the "necessary for compliance with any law" carve-out in the chapeau of s.8(7) | ✔ carve-out is the chapeau, not a clause |
| `SS-01` | Security safeguards | **s.8(4)** — "appropriate technical and organisational measures to ensure effective observance of the provisions of this Act"; **s.8(5)** — "reasonable security safeguards to prevent personal data breach"; **s.8(6)** — breach intimation to the Board and affected Data Principals | TLS (observed on the connection), encryption at rest, access control, and pseudonymisation on export (verified by the export audit) are the concrete safeguards | ✔ verbatim |
| `PL-01` | Purpose limitation | **s.4(1)** — processing "only … for a lawful purpose"; **s.5(1)(i)** — notice of "the personal data and the purpose for which the same is proposed to be processed"; **s.6(1)** — consent "for the specified purpose" | A run declares one specified purpose; onward uses are assessed against other recognised purposes' envelopes rather than merely flagged | ✔ verbatim |
| `NT-01` | Transparency / notice | **s.5(1)** — notice accompanying or preceding the request for consent, informing the Data Principal of (i) the personal data and the purpose, (ii) the manner of exercising her rights under s.6(4) and s.13, (iii) the manner of complaint to the Board; **s.5(3)** — in English or a scheduled language | A notice artefact is recorded and covers the run's purpose; the purpose matrix treats a notice as not covering a purpose it did not name | ✔ was cited as s.5(1)–(2); s.5(2) is transitional |
| `AC-01` | Accountability | **s.8(1)** — the Data Fiduciary "shall … be responsible for complying with the provisions of this Act … irrespective of any agreement to the contrary or failure of a Data Principal to carry out the duties"; **s.8(9)** — publish the business contact of a Data Protection Officer "if applicable, or a person who is able to answer" the Data Principal's questions; **s.8(10)** — grievance mechanism; **s.10(2)** (Significant Data Fiduciary, notified under s.10(1)) — a Data Protection Officer, an independent data auditor, periodic DPIA and audit | Audit log (written by the harness), a named accountable party, and a record of processing are the demonstrable-compliance controls; the fifth HIS layer's audit events are the evidence | ✔ was cited as s.8(8); the contact duty is s.8(9) |
<!-- /table:mapping -->

## Appendix B — The field catalogue

Every field the pipeline knows, by HIS layer, with the DPDP category the rules
score. It is the single source read by the generator, the per-layer schemas, the
HL7 v2 and FHIR shapers, the crawler's layer inference and the dataset
adapter's classification (`src/data_synthetic/catalogue.py`). A field not in it
cannot be categorised, so it is dropped at the adapter and never reaches a rule.

<!-- table:catalogue -->
| Layer | Field | DPDP category |
|---|---|---|
| patient_administration | `mrn` | direct identifier |
|  | `full_name` | direct identifier |
|  | `phone` | direct identifier |
|  | `email` | contact |
|  | `street_address` | contact |
|  | `date_of_birth` | quasi identifier |
|  | `sex` | quasi identifier |
|  | `pincode` | quasi identifier |
|  | `admission_ward` | administrative |
|  | `admission_datetime` | administrative |
| clinical_ehr | `mrn` | direct identifier |
|  | `primary_diagnosis` | clinical |
|  | `medication` | clinical |
|  | `lab_result` | clinical |
|  | `allergy` | clinical |
|  | `encounter_datetime` | administrative |
|  | `attending_clinician` | administrative |
| ancillary_departmental | `mrn` | direct identifier |
|  | `order_id` | administrative |
|  | `specimen_type` | clinical |
|  | `result_value` | clinical |
|  | `imaging_modality` | clinical |
|  | `report_text` | clinical |
| administrative_financial | `mrn` | direct identifier |
|  | `invoice_id` | financial |
|  | `billed_amount` | financial |
|  | `insurance_policy_no` | financial |
|  | `payer_name` | financial |
| infrastructure_integration | `audit_event_id` | administrative |
|  | `event_timestamp` | administrative |
|  | `actor_role` | administrative |
|  | `action` | administrative |
|  | `source_system` | administrative |
|  | `subject_mrn` | direct identifier |
<!-- /table:catalogue -->

## Appendix C — The purpose, role and artefact policy

**C.1 Purposes** (`src/compliance/policy.py`). The three are pairwise
non-nested: no purpose's permitted categories contain another's
(`test_three_purposes_and_all_pairwise_non_nested`).

<!-- table:policy -->
| Purpose | Categories permitted | Retention ceiling | Pseudonymised identifiers required | Basis relied on |
|---|---|---|---|---|
| `care_coordination` | administrative, clinical, direct identifier, quasi identifier | 90 days | yes | legitimate use -- the purpose for which the patient provided her data: provision of medical services |
| `billing_settlement` | administrative, contact, direct identifier, financial | 365 days | no | legitimate use -- the purpose for which the patient provided her data: settlement of amounts due for services provided |
| `patient_registration` | administrative, contact, direct identifier, quasi identifier | 180 days | no | legitimate use -- the purpose for which the patient provided her data: registration and scheduling for provision of services |
<!-- /table:policy -->

**C.2 Roles** (`src/compliance/roles.py`). A role's scope is *derived* — the
categories lawful under its purposes intersected with the categories carried by
the interoperability artefacts it handles — not listed.

<!-- table:roles -->
| Role | Purposes | Artefacts handled | Derived scope (purposes ∩ artefacts) |
|---|---|---|---|
| reception | billing_settlement, patient_registration | `fhir:Appointment`, `fhir:Coverage`, `fhir:Patient`, `fhir:Schedule`, `hl7:ADT`, `hl7:SIU` | administrative, contact, direct identifier, financial, quasi identifier |
| nurse | care_coordination | `fhir:AllergyIntolerance`, `fhir:Condition`, `fhir:DiagnosticReport`, `fhir:Encounter`, `fhir:MedicationRequest`, `fhir:Observation`, `fhir:Patient`, `fhir:ServiceRequest`, `hl7:ORM`, `hl7:ORU`, `ieee11073:PoCD` | administrative, clinical, direct identifier, quasi identifier |
| administrator | billing_settlement, patient_registration | `fhir:Account`, `fhir:ClaimResponse`, `fhir:Coverage`, `fhir:Encounter`, `fhir:Invoice`, `fhir:Location`, `fhir:Patient`, `hl7:ADT`, `hl7:BAR`, `hl7:DFT` | administrative, contact, direct identifier, financial, quasi identifier |
<!-- /table:roles -->

**C.3 Interoperability artefacts.** The standard-defined objects a role may
handle, with the categories each carries. `fhir:Claim` and `dicom:Study` are
granted to no role, by design (§3.4).

<!-- table:artefacts -->
| Artefact | Standard | Name | Layer | Categories carried | Granted to |
|---|---|---|---|---|---|
| `dicom:Study` | dicom | Study / Series metadata | ancillary_departmental | clinical, direct identifier | no role |
| `fhir:Account` | fhir | Account | administrative_financial | direct identifier, financial | administrator |
| `fhir:AllergyIntolerance` | fhir | AllergyIntolerance | clinical_ehr | clinical, direct identifier | nurse |
| `fhir:Appointment` | fhir | Appointment | patient_administration | administrative, direct identifier | reception |
| `fhir:AuditEvent` | fhir | AuditEvent | infrastructure_integration | administrative, direct identifier | no role |
| `fhir:Claim` | fhir | Claim | administrative_financial | clinical, direct identifier, financial | no role |
| `fhir:ClaimResponse` | fhir | ClaimResponse / PaymentReconciliation | administrative_financial | direct identifier, financial | administrator |
| `fhir:Condition` | fhir | Condition | clinical_ehr | clinical, direct identifier | nurse |
| `fhir:Coverage` | fhir | Coverage | administrative_financial | direct identifier, financial | reception, administrator |
| `fhir:DiagnosticReport` | fhir | DiagnosticReport | ancillary_departmental | clinical, direct identifier | nurse |
| `fhir:Encounter` | fhir | Encounter | clinical_ehr | administrative, direct identifier | nurse, administrator |
| `fhir:Invoice` | fhir | Invoice | administrative_financial | contact, direct identifier, financial | administrator |
| `fhir:Location` | fhir | Location (ward / bed) | patient_administration | administrative | administrator |
| `fhir:MedicationRequest` | fhir | MedicationRequest / MedicationAdministration | clinical_ehr | clinical, direct identifier | nurse |
| `fhir:Observation` | fhir | Observation | ancillary_departmental | clinical, direct identifier | nurse |
| `fhir:Patient` | fhir | Patient | patient_administration | contact, direct identifier, quasi identifier | reception, nurse, administrator |
| `fhir:Schedule` | fhir | Schedule / Slot | patient_administration | administrative | reception |
| `fhir:ServiceRequest` | fhir | ServiceRequest | ancillary_departmental | administrative, clinical, direct identifier | nurse |
| `hl7:ADT` | hl7_v2 | ADT (A01 admit / A04 register / A08 update) | patient_administration | administrative, contact, direct identifier, quasi identifier | reception, administrator |
| `hl7:BAR` | hl7_v2 | BAR (P01 add billing account) | administrative_financial | contact, direct identifier, financial | administrator |
| `hl7:DFT` | hl7_v2 | DFT (P03 detail financial transaction) | administrative_financial | direct identifier, financial | administrator |
| `hl7:ORM` | hl7_v2 | ORM (O01 general order) | clinical_ehr | administrative, clinical, direct identifier | nurse |
| `hl7:ORU` | hl7_v2 | ORU (R01 observation result) | ancillary_departmental | clinical, direct identifier | nurse |
| `hl7:SIU` | hl7_v2 | SIU (S12 new appointment / S13 reschedule) | patient_administration | administrative, direct identifier | reception |
| `ieee11073:PoCD` | iso_ieee_11073 | Point-of-care device observation | ancillary_departmental | clinical | nurse |
<!-- /table:artefacts -->

## Appendix D — The staff assistant's functions

The fixed registry the assistant recognises (`src/agent/functions.py`). Who may
use a function is not stored with it: it is derived from the role gate of
Appendix C, and the "may be used by" column is computed by that gate.

<!-- table:functions -->
| Function | Purpose | Artefacts | Inputs asked for | May be used by |
|---|---|---|---|---|
| register a new patient | patient_registration | `fhir:Patient`, `hl7:ADT` | full_name, date_of_birth, phone | reception, administrator |
| book an appointment | patient_registration | `fhir:Appointment`, `fhir:Schedule`, `hl7:SIU` | mrn, department, preferred_date | reception |
| check in an arriving patient | patient_registration | `fhir:Appointment`, `fhir:Patient`, `hl7:ADT` | mrn | reception |
| verify insurance eligibility | billing_settlement | `fhir:Coverage` | mrn, insurance_policy_no | reception, administrator |
| record a patient's vital signs | care_coordination | `fhir:Observation`, `ieee11073:PoCD` | mrn, blood_pressure, pulse, temperature | nurse |
| view the active medication list | care_coordination | `fhir:AllergyIntolerance`, `fhir:MedicationRequest` | mrn | nurse |
| look up a patient's diagnosis | care_coordination | `fhir:Condition` | mrn | nurse |
| request a laboratory test | care_coordination | `fhir:ServiceRequest`, `hl7:ORM` | mrn, test_name, priority | nurse |
| prepare a discharge checklist | care_coordination | `fhir:Encounter`, `fhir:MedicationRequest` | mrn, discharge_date | nurse |
| allocate a bed | patient_registration | `fhir:Encounter`, `fhir:Location`, `hl7:ADT` | mrn, ward | administrator |
| generate an invoice | billing_settlement | `fhir:Account`, `fhir:Invoice`, `hl7:DFT` | mrn, encounter_id | administrator |
| reconcile a payer settlement | billing_settlement | `fhir:ClaimResponse`, `fhir:Coverage` | invoice_id | administrator |
| run a ward census | patient_registration | `fhir:Encounter`, `fhir:Location`, `hl7:ADT` | ward, date | administrator |
<!-- /table:functions -->

## Appendix E — Reproducibility

Every number in the report is produced by a command in the repository, from
committed inputs, on any machine with Python 3.10 or later.

**Environment.**

```
pip install -r requirements.txt
python -m playwright install chromium        # the Tier 2 browser, once per machine
```

**Fixed inputs.** The synthetic generator is seeded (seed 42; 50 records per
layer in memory, 20 per module on the portal, ten per page). The AI-model
decisions are committed recordings under
`src/extraction/techniques/recordings/`, replayed by default
(`AI_AGENT_MODE=replay`), so no command below reaches the network or needs a
key. The public export is fetched once:

```
python scripts/fetch_public_dataset.py       # Synthea sample into data/public_synthea/, with provenance and column map
```

**Every result, by table.**

| Result | Command | Artefact |
|---|---|---|
| Tables 0–2, in memory (eight tasks, every repeat scored) | `python scripts/run_benchmark.py` | `docs/benchmark_results/benchmark.{json,md}` |
| Table 2, portal rows; Tables 4–5; the whole chain | `python scripts/run_pipeline.py` | `benchmark-portal.{json,md}`, `navigation-map.{json,md}` |
| Table 3, the purpose matrix | `python scripts/compare_purposes.py` | `*--purpose-matrix.md` |
| Table 6, the role gate | `python scripts/show_role_access.py` | printed |
| Table 7, the public export | `python scripts/run_pipeline.py --dataset data/public_synthea --column-map data/public_synthea/column_map.json --artefact benchmark-public` | `benchmark-public.{json,md}` |
| The weight sweep (§7.2) | `python tools/weight_sweep.py` | `weight-sweep.md` |
| The day-one rehearsal and its leak audit (§7.7) | `python scripts/rehearse_day_one.py` | printed; `identifier leaks: 0` |
| Every table in this report | `python tools/report_tables.py` (`--check` to verify) | the chapters, in place |

**Checks that hold on every push.** The continuous-integration workflow
(`.github/workflows/ci.yml`) runs the test suite and regenerates `benchmark.json`
from a clean checkout, failing if any number differs from the committed one
(timestamps and wall-clock excepted). `python tools/report_tables.py --check`
does the same for the report's tables against the artefacts.

**Recording the AI models again** (needs a key or a subscription; spends the
provider's allowance, which is why the recordings are committed):

```
python scripts/record_ai_agents.py --provider gemini --repeats 5                       # GEMINI_API_KEY set
python scripts/record_ai_agents.py --provider claude-code --model claude-haiku-4-5 \
    --briefing policy --repeats 2                                                     # a Claude subscription sign-in
```

**What does not reproduce exactly.** Wall-clock times, which are hardware-
dependent and reported but not relied upon; and a *fresh* recording of an AI
model, whose decisions are samples — which is the point of the stability column,
and why the recordings used for the report are committed.
