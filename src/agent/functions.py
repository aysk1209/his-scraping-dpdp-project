"""The function registry: every HIS operation the agent knows how to explain.

Each ``FunctionSpec`` declares four things and the agent derives everything else:

- the **purpose** it serves and the **interop artefacts** it touches -- handed to
  ``compliance.roles.authorise`` to decide whether a given role may be told how;
- the **inputs** it needs from the staff member, asked for one at a time;
- the **steps** to perform it, as templates over those inputs, each grounded in a
  HIS layer, an artefact, and catalogue field names.

Who may perform a function is *not* stored here. It falls out of the role policy,
so there is exactly one place where access is decided and the registry cannot
drift from it.

Grounding is checkable: every step names an artefact in ``compliance.roles``
and fields in ``data_synthetic.catalogue``, and tests assert both, so an
instruction that refers to something the HIS does not have cannot be shipped.
The optional ``page`` on a step is the seam for the Tier 2 navigation map --
today it is empty; when a portal exists it carries the page the step happens on.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from compliance.models import FieldCategory, Purpose
from compliance.roles import StaffRole, authorise
from interop.layers import HISLayer

_PA = HISLayer.PATIENT_ADMINISTRATION
_EHR = HISLayer.CLINICAL_EHR
_ANC = HISLayer.ANCILLARY_DEPARTMENTAL
_FIN = HISLayer.ADMINISTRATIVE_FINANCIAL


class InputSlot(BaseModel):
    """One detail the agent must ask for before it can give instructions."""

    name: str
    prompt: str                                 # the question asked
    example: str                                # shown so the format is clear
    category: FieldCategory | None = None       # what kind of data the answer is


class Step(BaseModel):
    """One numbered instruction, grounded in where in the HIS it happens."""

    text: str                                   # may reference {slot_name}
    layer: HISLayer
    artefact: str                               # key into compliance.roles.ARTEFACTS
    fields: list[str] = Field(default_factory=list)   # catalogue fields touched
    caution: str | None = None                  # a DPDP note attached to this step
    page: str | None = None                     # navigation-map seam; unset until W2


class FunctionSpec(BaseModel):
    id: str
    label: str
    synonyms: list[str]                         # phrases staff actually say
    purpose: Purpose
    artefacts: set[str]
    # Narrow when the function reads only part of an artefact. None = derive.
    categories: set[FieldCategory] | None = None
    inputs: list[InputSlot]
    steps: list[Step]

    def permitted_for(self, role: StaffRole) -> bool:
        return authorise(role, self.purpose, self.artefacts, self.categories).allowed


# --------------------------------------------------------------------------- #
# Shared slots
# --------------------------------------------------------------------------- #

_MRN = InputSlot(
    name="mrn", prompt="What is the patient's medical record number (MRN)?",
    example="MRN2867825", category=FieldCategory.DIRECT_IDENTIFIER,
)
_WARD = InputSlot(
    name="ward", prompt="Which ward?", example="Ward 4B",
    category=FieldCategory.ADMINISTRATIVE,
)


# --------------------------------------------------------------------------- #
# The registry
# --------------------------------------------------------------------------- #

REGISTRY: list[FunctionSpec] = [
    # ---------------------------------------------------------------- reception
    FunctionSpec(
        id="register_patient",
        label="register a new patient",
        synonyms=["new patient", "registration", "add a patient", "create patient record",
                  "walk-in", "first visit", "enrol", "sign up a patient"],
        purpose=Purpose.PATIENT_REGISTRATION,
        artefacts={"hl7:ADT", "fhir:Patient"},
        inputs=[
            InputSlot(name="full_name", prompt="What is the patient's full name?",
                      example="Priya Raman", category=FieldCategory.DIRECT_IDENTIFIER),
            InputSlot(name="date_of_birth", prompt="Date of birth?",
                      example="1988-03-14", category=FieldCategory.QUASI_IDENTIFIER),
            InputSlot(name="phone", prompt="A contact phone number?",
                      example="+91-98xxxxxx12", category=FieldCategory.DIRECT_IDENTIFIER),
        ],
        steps=[
            Step(text="In Patient Administration, open Registration and search for "
                      "{full_name} born {date_of_birth} to check whether a record already exists.",
                 layer=_PA, artefact="fhir:Patient", fields=["full_name", "date_of_birth"],
                 caution="Search before creating -- a duplicate record is two copies of the same personal data."),
            Step(text="If there is no match, choose New Patient and enter the name, date of birth "
                      "and phone {phone}. Leave every field you were not given blank.",
                 layer=_PA, artefact="hl7:ADT", fields=["full_name", "date_of_birth", "phone"],
                 caution="Collect only what registration needs; do not fill optional fields speculatively."),
            Step(text="Read the privacy notice to the patient and tick Notice Acknowledged before saving.",
                 layer=_PA, artefact="fhir:Patient",
                 caution="DPDP transparency / notice -- the acknowledgement is what the compliance rule NT-01 later checks for."),
            Step(text="Save. The system assigns an MRN; read it back to the patient and note it on their slip.",
                 layer=_PA, artefact="hl7:ADT", fields=["mrn"]),
        ],
    ),
    FunctionSpec(
        id="book_appointment",
        label="book an appointment",
        synonyms=["schedule", "appointment", "book a slot", "reschedule", "booking",
                  "consultation slot", "opd booking"],
        purpose=Purpose.PATIENT_REGISTRATION,
        artefacts={"fhir:Appointment", "fhir:Schedule", "hl7:SIU"},
        inputs=[
            _MRN,
            InputSlot(name="department", prompt="Which department or clinic?",
                      example="Cardiology OPD", category=FieldCategory.ADMINISTRATIVE),
            InputSlot(name="preferred_date", prompt="Preferred date?",
                      example="2026-09-20", category=FieldCategory.ADMINISTRATIVE),
        ],
        steps=[
            Step(text="In Patient Administration, open Scheduling and look up {mrn}.",
                 layer=_PA, artefact="fhir:Appointment", fields=["mrn"]),
            Step(text="Select {department} and open the schedule for {preferred_date}; pick a free slot.",
                 layer=_PA, artefact="fhir:Schedule", fields=["admission_datetime"]),
            Step(text="Confirm the booking. The appointment message is sent to the department automatically.",
                 layer=_PA, artefact="hl7:SIU", fields=["mrn", "admission_datetime"]),
            Step(text="Tell the patient the date, time and where to report.",
                 layer=_PA, artefact="fhir:Appointment"),
        ],
    ),
    FunctionSpec(
        id="check_in_arrival",
        label="check in an arriving patient",
        synonyms=["check in", "arrived", "patient is here", "mark arrival", "front desk arrival"],
        purpose=Purpose.PATIENT_REGISTRATION,
        artefacts={"fhir:Appointment", "hl7:ADT", "fhir:Patient"},
        inputs=[_MRN],
        steps=[
            Step(text="In Patient Administration, open Today's Appointments and find {mrn}.",
                 layer=_PA, artefact="fhir:Appointment", fields=["mrn"]),
            Step(text="Confirm identity by asking the patient their name and date of birth -- "
                      "do not read them out yourself.",
                 layer=_PA, artefact="fhir:Patient", fields=["full_name", "date_of_birth"],
                 caution="Asking, not telling, avoids disclosing identifiers to whoever is at the desk."),
            Step(text="Mark Arrived. The clinic queue updates; direct the patient to the waiting area.",
                 layer=_PA, artefact="hl7:ADT", fields=["mrn", "admission_datetime"]),
        ],
    ),
    FunctionSpec(
        id="verify_insurance",
        label="verify insurance eligibility",
        synonyms=["insurance", "eligibility", "is the policy active", "coverage check",
                  "payer", "cashless", "tpa"],
        purpose=Purpose.BILLING_SETTLEMENT,
        artefacts={"fhir:Coverage"},
        inputs=[
            _MRN,
            InputSlot(name="insurance_policy_no", prompt="The policy number on the card?",
                      example="POL-44812-K", category=FieldCategory.FINANCIAL),
        ],
        steps=[
            Step(text="Open Insurance / Coverage for {mrn}.",
                 layer=_FIN, artefact="fhir:Coverage"),
            Step(text="Enter policy {insurance_policy_no} and run Eligibility Check.",
                 layer=_FIN, artefact="fhir:Coverage", fields=["insurance_policy_no", "payer_name"]),
            Step(text="Read the status (active / inactive / needs pre-authorisation) to the patient. "
                      "Do not open the account or invoice screens -- that is the billing office's work.",
                 layer=_FIN, artefact="fhir:Coverage",
                 caution="Eligibility is all this role needs; amounts owed are a different artefact and a different desk."),
        ],
    ),
    # -------------------------------------------------------------------- nurse
    FunctionSpec(
        id="record_vitals",
        label="record a patient's vital signs",
        synonyms=["vitals", "observations", "bp", "blood pressure", "temperature", "pulse",
                  "chart obs", "record readings"],
        purpose=Purpose.CARE_COORDINATION,
        artefacts={"fhir:Observation", "ieee11073:PoCD"},
        inputs=[
            _MRN,
            InputSlot(name="blood_pressure", prompt="Blood pressure?", example="128/82",
                      category=FieldCategory.CLINICAL),
            InputSlot(name="pulse", prompt="Pulse (bpm)?", example="76",
                      category=FieldCategory.CLINICAL),
            InputSlot(name="temperature", prompt="Temperature (C)?", example="37.1",
                      category=FieldCategory.CLINICAL),
        ],
        steps=[
            Step(text="Open the patient's chart for {mrn} and go to Observations.",
                 layer=_ANC, artefact="fhir:Observation"),
            Step(text="If the bedside monitor is linked, accept its readings; otherwise enter "
                      "BP {blood_pressure}, pulse {pulse}, temperature {temperature}.",
                 layer=_ANC, artefact="ieee11073:PoCD", fields=["result_value"]),
            Step(text="Set the time taken and save. Flag any value outside the ward's early-warning range.",
                 layer=_ANC, artefact="fhir:Observation", fields=["result_value"]),
        ],
    ),
    FunctionSpec(
        id="view_medications",
        label="view the active medication list",
        synonyms=["medications", "meds", "drug chart", "what is the patient on", "prescriptions",
                  "allergies", "medication list"],
        purpose=Purpose.CARE_COORDINATION,
        artefacts={"fhir:MedicationRequest", "fhir:AllergyIntolerance"},
        inputs=[_MRN],
        steps=[
            Step(text="Open the chart for {mrn} and select Medications.",
                 layer=_EHR, artefact="fhir:MedicationRequest", fields=["medication"]),
            Step(text="Check the Allergies banner at the top before reading the list.",
                 layer=_EHR, artefact="fhir:AllergyIntolerance", fields=["allergy"]),
            Step(text="Read only the active orders; discontinued items are under History if you need them.",
                 layer=_EHR, artefact="fhir:MedicationRequest", fields=["medication"],
                 caution="Open what the task needs. The chart holds more than the medication list."),
        ],
    ),
    FunctionSpec(
        id="view_diagnosis",
        label="look up a patient's diagnosis",
        synonyms=["diagnosis", "what is wrong with the patient", "condition", "problem list",
                  "why is the patient admitted"],
        purpose=Purpose.CARE_COORDINATION,
        artefacts={"fhir:Condition"},
        inputs=[_MRN],
        steps=[
            Step(text="Open the chart for {mrn} and select Problems / Diagnoses.",
                 layer=_EHR, artefact="fhir:Condition", fields=["primary_diagnosis"]),
            Step(text="The primary diagnosis is listed first; secondary conditions follow.",
                 layer=_EHR, artefact="fhir:Condition", fields=["primary_diagnosis"],
                 caution="Clinical data: view it at the bedside or the station, never on a screen facing a corridor."),
        ],
    ),
    FunctionSpec(
        id="request_lab",
        label="request a laboratory test",
        synonyms=["lab", "order a test", "bloods", "send sample", "lab request", "pathology"],
        purpose=Purpose.CARE_COORDINATION,
        artefacts={"fhir:ServiceRequest", "hl7:ORM"},
        inputs=[
            _MRN,
            InputSlot(name="test_name", prompt="Which test?", example="Full blood count",
                      category=FieldCategory.CLINICAL),
            InputSlot(name="priority", prompt="Routine or urgent?", example="routine",
                      category=FieldCategory.ADMINISTRATIVE),
        ],
        steps=[
            Step(text="Open Orders for {mrn} and choose New Laboratory Request.",
                 layer=_ANC, artefact="fhir:ServiceRequest", fields=["order_id"]),
            Step(text="Select {test_name}, set priority {priority}, and add the specimen type.",
                 layer=_ANC, artefact="fhir:ServiceRequest", fields=["specimen_type"]),
            Step(text="Submit. The order goes to the laboratory system; print the specimen label from the confirmation.",
                 layer=_EHR, artefact="hl7:ORM"),
        ],
    ),
    FunctionSpec(
        id="discharge_checklist",
        label="prepare a discharge checklist",
        synonyms=["discharge", "going home", "send home", "discharge summary", "release patient"],
        purpose=Purpose.CARE_COORDINATION,
        artefacts={"fhir:Encounter", "fhir:MedicationRequest"},
        inputs=[
            _MRN,
            InputSlot(name="discharge_date", prompt="Planned discharge date?", example="2026-09-15",
                      category=FieldCategory.ADMINISTRATIVE),
        ],
        steps=[
            Step(text="Open the encounter for {mrn} and start Discharge Planning for {discharge_date}.",
                 layer=_EHR, artefact="fhir:Encounter", fields=["encounter_datetime"]),
            Step(text="Reconcile the medication list: confirm what continues, what stops, and what is new.",
                 layer=_EHR, artefact="fhir:MedicationRequest", fields=["medication", "allergy"]),
            Step(text="Complete the nursing items on the checklist and mark Ready for Discharge. "
                      "The bed release and billing hand-offs happen from that flag -- you do not do them here.",
                 layer=_EHR, artefact="fhir:Encounter",
                 caution="Nursing does not open the billing screens; the flag is the hand-off."),
        ],
    ),
    # ------------------------------------------------------------ administrator
    FunctionSpec(
        id="allocate_bed",
        label="allocate a bed",
        synonyms=["bed", "assign a bed", "bed management", "admit to ward", "transfer", "move patient"],
        purpose=Purpose.PATIENT_REGISTRATION,
        artefacts={"fhir:Location", "hl7:ADT", "fhir:Encounter"},
        inputs=[_MRN, _WARD],
        steps=[
            Step(text="Open Bed Management and select {ward}; free beds are shown green.",
                 layer=_PA, artefact="fhir:Location", fields=["admission_ward"]),
            Step(text="Assign a free bed to {mrn} and confirm the admission or transfer.",
                 layer=_PA, artefact="hl7:ADT", fields=["mrn", "admission_ward", "admission_datetime"]),
            Step(text="The encounter's location updates automatically; check the ward board reflects it.",
                 layer=_EHR, artefact="fhir:Encounter", fields=["encounter_datetime"],
                 caution="You see where the patient is, not why -- the clinical content of the encounter stays closed."),
        ],
    ),
    FunctionSpec(
        id="generate_invoice",
        label="generate an invoice",
        synonyms=["invoice", "bill", "raise the bill", "billing", "charges", "final bill", "generate bill"],
        purpose=Purpose.BILLING_SETTLEMENT,
        artefacts={"fhir:Account", "fhir:Invoice", "hl7:DFT"},
        inputs=[
            _MRN,
            InputSlot(name="encounter_id", prompt="Which encounter or admission?", example="ENC-20260912-07",
                      category=FieldCategory.ADMINISTRATIVE),
        ],
        steps=[
            Step(text="Open Billing, find the account for {mrn} and select encounter {encounter_id}.",
                 layer=_FIN, artefact="fhir:Account", fields=["invoice_id"]),
            Step(text="Review the posted charges; add any that the departments have not yet sent.",
                 layer=_FIN, artefact="hl7:DFT", fields=["billed_amount"]),
            Step(text="Generate Invoice. Confirm the payer and the delivery address, then finalise.",
                 layer=_FIN, artefact="fhir:Invoice", fields=["invoice_id", "billed_amount", "payer_name"],
                 caution="The invoice names the payer and where it goes -- that is why billing may see contact data and nursing may not."),
        ],
    ),
    FunctionSpec(
        id="reconcile_payment",
        label="reconcile a payer settlement",
        synonyms=["reconcile", "payment received", "settlement", "remittance", "claim paid",
                  "insurance paid", "match payment"],
        purpose=Purpose.BILLING_SETTLEMENT,
        artefacts={"fhir:ClaimResponse", "fhir:Coverage"},
        inputs=[
            InputSlot(name="invoice_id", prompt="Which invoice number?", example="INV-2026-01187",
                      category=FieldCategory.FINANCIAL),
        ],
        steps=[
            Step(text="Open Receivables and find invoice {invoice_id}.",
                 layer=_FIN, artefact="fhir:ClaimResponse", fields=["invoice_id"]),
            Step(text="Match the payer's remittance to the invoice lines and record any shortfall.",
                 layer=_FIN, artefact="fhir:ClaimResponse", fields=["billed_amount", "payer_name"]),
            Step(text="Mark Settled or Partially Settled. Do not open the claim itself -- adjudication "
                      "detail carries diagnosis codes and is not part of reconciliation.",
                 layer=_FIN, artefact="fhir:Coverage", fields=["insurance_policy_no"],
                 caution="fhir:Claim is deliberately outside every role here; the settlement response is enough."),
        ],
    ),
    FunctionSpec(
        id="ward_census",
        label="run a ward census",
        synonyms=["census", "occupancy", "how many patients", "bed count", "ward report", "midnight census"],
        purpose=Purpose.PATIENT_REGISTRATION,
        artefacts={"fhir:Encounter", "fhir:Location", "hl7:ADT"},
        inputs=[
            _WARD,
            InputSlot(name="date", prompt="For which date?", example="2026-09-12",
                      category=FieldCategory.ADMINISTRATIVE),
        ],
        steps=[
            Step(text="Open Reports and choose Ward Census; select {ward} and {date}.",
                 layer=_PA, artefact="fhir:Location", fields=["admission_ward"]),
            Step(text="Run it. The report lists occupied beds and admission times, not diagnoses.",
                 layer=_EHR, artefact="fhir:Encounter", fields=["encounter_datetime"],
                 caution="A census is a count of encounters; if the report offers clinical columns, leave them unticked."),
            Step(text="Export to the shared drive folder for the date; the file carries MRNs, so it stays inside the hospital network.",
                 layer=_PA, artefact="hl7:ADT", fields=["mrn"],
                 caution="MRNs are direct identifiers -- storage limitation applies to the exported file too."),
        ],
    ),
]

BY_ID: dict[str, FunctionSpec] = {spec.id: spec for spec in REGISTRY}


def capabilities(role: StaffRole) -> list[FunctionSpec]:
    """The functions this role may be guided through -- derived from the gate, not stored."""

    return [spec for spec in REGISTRY if spec.permitted_for(role)]
