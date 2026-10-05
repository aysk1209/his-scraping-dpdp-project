"""The function registry: every HIS task the agent knows how to explain.

Each ``FunctionSpec`` declares four things and the agent derives everything else:

- the **purpose** it serves and the **interop artefacts** it touches -- handed to
  ``compliance.roles.authorise`` to decide whether a given role may be told how;
- the **inputs** it needs from the staff member, asked for one at a time (and
  picked out of the first message when they are there, and checked for shape);
- the **steps** to perform it, each grounded in a HIS layer, an artefact and
  catalogue field names, and -- where a button is pressed -- the *operation*
  the button performs (``agent.ui.ACTIONS``), never its label.

Who may perform a function is *not* stored here. It falls out of the role policy,
so there is exactly one place where access is decided and the registry cannot
drift from it.

**Steps never name a screen.** A step's text refers to ``{module}`` (the module
holding its fields), ``{button}`` (the button for its operation) and
``{label.<field>}`` (a column as headed on screen); ``agent.ui.ScreenMap`` fills
them from the portal as it was last crawled. That is what lets the same registry
survive a HIS update: rename the modules, move the fields, relabel the buttons,
and the next crawl re-words every instruction. A step that cannot be placed is
withheld, not guessed (see ``agent.ui``). Two flags shape placement:
``continues`` -- the step happens where the previous one left off (the form a
button opened); ``offscreen`` -- the step is not on a screen at all (talking to
the patient, a message the system sends by itself).

Grounding is checkable: every step names an artefact in ``compliance.roles``
and fields in ``data_synthetic.catalogue``, every button an operation in the
vocabulary, every ``{label.x}`` a field the step declares; tests assert all of it,
so an instruction that refers to something the HIS does not have cannot be
shipped.
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

_REG = Purpose.PATIENT_REGISTRATION
_CARE = Purpose.CARE_COORDINATION
_BILL = Purpose.BILLING_SETTLEMENT

_DI = FieldCategory.DIRECT_IDENTIFIER
_QI = FieldCategory.QUASI_IDENTIFIER
_CL = FieldCategory.CLINICAL
_FI = FieldCategory.FINANCIAL
_AD = FieldCategory.ADMINISTRATIVE


class InputSlot(BaseModel):
    """One detail the agent must ask for before it can give instructions."""

    name: str
    prompt: str                                 # the question asked
    example: str                                # shown so the format is clear
    category: FieldCategory | None = None       # what kind of data the answer is
    pattern: str | None = None                  # an answer must match this (whole, any case)
    find: str | None = None                     # pick the answer out of the first message


class Step(BaseModel):
    """One numbered instruction, grounded in where in the HIS it happens."""

    text: str                                   # {slot}, {module}, {button}, {label.<field>}
    layer: HISLayer
    artefact: str                               # key into compliance.roles.ARTEFACTS
    fields: list[str] = Field(default_factory=list)   # catalogue fields touched
    action: str | None = None                   # key into agent.ui.ACTIONS: the button pressed
    continues: bool = False                     # happens where the previous step left off
    offscreen: bool = False                     # not on a screen at all
    caution: str | None = None                  # a DPDP note attached to this step


class FunctionSpec(BaseModel):
    id: str
    label: str
    group: str                                  # how the menu groups it
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
# Shared slots and shapes
# --------------------------------------------------------------------------- #

_DATE = r"\d{4}-\d{2}-\d{2}|\d{1,2}[/.-]\d{1,2}[/.-]\d{4}"
_ISO_DATE = r"\b\d{4}-\d{2}-\d{2}\b"
_REF = r"[A-Za-z]{2,5}-?[\d-]{4,}"

_MRN = InputSlot(
    name="mrn", prompt="What is the patient's medical record number (MRN)?",
    example="MRN2867825", category=_DI,
    pattern=r"[A-Za-z]{0,6}[- ]?\d{4,12}", find=r"\b[A-Z]{2,6}\d{5,12}\b",
)
_WARD = InputSlot(
    name="ward", prompt="Which ward?", example="Ward 4B", category=_AD,
    find=r"\bward\s+\d+[a-z]?\b",
)
_NAME = InputSlot(name="full_name", prompt="What is the patient's full name?",
                  example="Priya Raman", category=_DI)
_DOB = InputSlot(name="date_of_birth", prompt="Date of birth?", example="1988-03-14",
                 category=_QI, pattern=_DATE)
_ENCOUNTER = InputSlot(name="encounter_id", prompt="Which encounter or admission?",
                       example="ENC-20260912-07", category=_AD,
                       pattern=_REF, find=r"\bENC-[\d-]{4,}\b")

# Steps that recur, word for word, across tasks.
_ASK_NOT_TELL = ("Asking, not telling, avoids disclosing identifiers to whoever is at the desk.")


def _open_record(layer: HISLayer, artefact: str) -> Step:
    return Step(text="Open {module}, search for {mrn} and open the record.",
                layer=layer, artefact=artefact, fields=["mrn"])


def _confirm_identity(caution: str = _ASK_NOT_TELL) -> Step:
    return Step(text="Confirm it is the patient: ask for their {label.full_name} and "
                     "{label.date_of_birth} -- do not read them out.",
                layer=_PA, artefact="fhir:Patient", fields=["full_name", "date_of_birth"],
                continues=True, caution=caution)


# --------------------------------------------------------------------------- #
# The registry
# --------------------------------------------------------------------------- #

FRONT_DESK = "Patients and appointments"
INSURANCE = "Insurance"
PRIVACY = "Privacy requests"
WARD = "Ward care"
ORDERS = "Orders and results"
BEDS = "Beds and wards"
BILLING = "Billing"

REGISTRY: list[FunctionSpec] = [
    # ======================================================== front desk
    FunctionSpec(
        id="register_patient",
        label="register a new patient",
        group=FRONT_DESK,
        synonyms=["new patient", "registration", "add a patient", "create patient record",
                  "walk-in", "first visit", "enrol", "sign up a patient"],
        purpose=_REG,
        artefacts={"hl7:ADT", "fhir:Patient", "fhir:Consent"},
        inputs=[
            _NAME, _DOB,
            InputSlot(name="phone", prompt="A contact phone number?", example="+91-9800000012",
                      category=_DI, pattern=r"\+?\d[\d\s-]{7,15}"),
        ],
        steps=[
            Step(text="Open {module} and search for {full_name}; check whether anyone listed "
                      "with that name was born on {date_of_birth}.",
                 layer=_PA, artefact="fhir:Patient", fields=["full_name", "date_of_birth"],
                 caution="Search before creating -- a duplicate record is two copies of the same personal data."),
            Step(text="If there is no match, press {button} and enter the {label.full_name}, "
                      "{label.date_of_birth} and {label.phone} ({phone}). Leave every field "
                      "you were not given blank.",
                 layer=_PA, artefact="hl7:ADT", fields=["full_name", "date_of_birth", "phone"],
                 action="create_patient",
                 caution="Collect only what registration needs; do not fill optional fields speculatively."),
            Step(text="Read the privacy notice to the patient and tick Notice Acknowledged before saving.",
                 layer=_PA, artefact="fhir:Consent", continues=True,
                 caution="DPDP transparency / notice -- the acknowledgement is what the compliance rule NT-01 later checks for."),
            Step(text="Save. The system assigns the {label.mrn}; read it back to the patient and "
                      "note it on their slip.",
                 layer=_PA, artefact="hl7:ADT", fields=["mrn"], continues=True),
        ],
    ),
    FunctionSpec(
        id="find_patient",
        label="find a patient's record",
        group=FRONT_DESK,
        synonyms=["find patient", "search for a patient", "what is the mrn", "forgot their mrn",
                  "existing patient", "patient lookup", "uhid", "find their record"],
        purpose=_REG,
        artefacts={"fhir:Patient"},
        categories={_DI, _QI},                  # who they are; not how to reach them
        inputs=[_NAME, _DOB],
        steps=[
            Step(text="Open {module} and search for {full_name}.",
                 layer=_PA, artefact="fhir:Patient", fields=["full_name"]),
            Step(text="Among the matches, open the record whose {label.date_of_birth} is "
                      "{date_of_birth}, and ask the patient to confirm it is them.",
                 layer=_PA, artefact="fhir:Patient", fields=["date_of_birth"], continues=True,
                 caution="Other people share names: do not read out the other matches or turn the screen to show them."),
            Step(text="Give the patient their {label.mrn} from the record, written on their slip.",
                 layer=_PA, artefact="fhir:Patient", fields=["mrn"], continues=True),
        ],
    ),
    FunctionSpec(
        id="update_details",
        label="update or correct a patient's details",
        group=FRONT_DESK,
        synonyms=["change phone number", "moved house", "update contact details", "correct details",
                  "correction request", "wrong date of birth", "edit patient details",
                  "change of address", "spelling of name"],
        purpose=_REG,
        artefacts={"hl7:ADT", "fhir:Patient", "fhir:Task"},
        inputs=[
            _MRN,
            InputSlot(name="change", prompt="What is changing, and to what?",
                      example="phone to +91-9800000013", category=_DI),
        ],
        steps=[
            _open_record(_PA, "fhir:Patient"),
            _confirm_identity("Only the patient, or someone lawfully acting for them, may change their record."),
            Step(text="Press {button} and make this change only: {change}. Save; the update goes "
                      "to the other systems as an ADT A08.",
                 layer=_PA, artefact="hl7:ADT", fields=["phone", "email", "street_address"],
                 action="edit_details",
                 caution="DPDP right to correction and updating: correct what the patient asked for, and nothing else."),
            Step(text="If they asked for it as a correction, press {button} and log it as a "
                      "correction request, completed today.",
                 layer=_PA, artefact="fhir:Task", fields=["mrn"], action="privacy_request"),
        ],
    ),
    FunctionSpec(
        id="book_appointment",
        label="book an appointment",
        group=FRONT_DESK,
        synonyms=["schedule", "appointment", "book a slot", "booking", "consultation slot",
                  "opd booking", "book"],
        purpose=_REG,
        artefacts={"fhir:Appointment", "fhir:Schedule", "hl7:SIU"},
        inputs=[
            _MRN,
            InputSlot(name="department", prompt="Which department or clinic?",
                      example="Cardiology OPD", category=_AD),
            InputSlot(name="preferred_date", prompt="Preferred date?", example="2026-09-20",
                      category=_AD, pattern=_DATE, find=_ISO_DATE),
        ],
        steps=[
            _open_record(_PA, "fhir:Appointment"),
            Step(text="Press {button}, choose {department}, and open the schedule for "
                      "{preferred_date}; pick a free slot.",
                 layer=_PA, artefact="fhir:Schedule", fields=["admission_datetime"],
                 action="book_appointment"),
            Step(text="Confirm. The booking goes to the department as an SIU message by itself.",
                 layer=_PA, artefact="hl7:SIU", fields=["mrn", "admission_datetime"], offscreen=True),
            Step(text="Tell the patient the date, time and where to report.",
                 layer=_PA, artefact="fhir:Appointment", offscreen=True),
        ],
    ),
    FunctionSpec(
        id="change_appointment",
        label="reschedule or cancel an appointment",
        group=FRONT_DESK,
        synonyms=["reschedule", "cancel appointment", "change appointment", "move appointment",
                  "postpone", "cancel booking", "cannot come", "change the date"],
        purpose=_REG,
        artefacts={"fhir:Appointment", "fhir:Schedule", "hl7:SIU"},
        inputs=[_MRN],
        steps=[
            _open_record(_PA, "fhir:Appointment"),
            Step(text="To move it, press {button} and pick the free slot the patient wants.",
                 layer=_PA, artefact="fhir:Schedule", fields=["admission_datetime"],
                 action="reschedule"),
            Step(text="To cancel it instead, press {button}.",
                 layer=_PA, artefact="fhir:Appointment", action="cancel_appointment",
                 caution="A reason is not needed to cancel; record one only if the patient offers it."),
            Step(text="Either way the change goes to the department as an SIU message; confirm "
                      "the outcome to the patient.",
                 layer=_PA, artefact="hl7:SIU", fields=["mrn"], offscreen=True),
        ],
    ),
    FunctionSpec(
        id="check_in_arrival",
        label="check in an arriving patient",
        group=FRONT_DESK,
        synonyms=["check in", "arrived", "patient is here", "mark arrival", "front desk arrival",
                  "has arrived"],
        purpose=_REG,
        artefacts={"fhir:Appointment", "hl7:ADT", "fhir:Patient"},
        inputs=[_MRN],
        steps=[
            _open_record(_PA, "fhir:Appointment"),
            _confirm_identity(),
            Step(text="Press {button}. The clinic queue updates; direct the patient to the waiting area.",
                 layer=_PA, artefact="hl7:ADT", fields=["mrn", "admission_datetime"],
                 action="mark_arrived"),
        ],
    ),
    # ========================================================= insurance
    FunctionSpec(
        id="verify_insurance",
        label="verify insurance eligibility",
        group=INSURANCE,
        synonyms=["insurance", "eligibility", "is the policy active", "coverage check",
                  "payer", "cashless", "tpa"],
        purpose=_BILL,
        artefacts={"fhir:Coverage"},
        inputs=[
            _MRN,
            InputSlot(name="insurance_policy_no", prompt="The policy number on the card?",
                      example="POL-44812-K", category=_FI),
        ],
        steps=[
            Step(text="Open {module} and press {button}.",
                 layer=_FIN, artefact="fhir:Coverage", action="check_eligibility"),
            Step(text="Enter the {label.mrn} {mrn} and policy {insurance_policy_no}, and run the check.",
                 layer=_FIN, artefact="fhir:Coverage", fields=["mrn", "insurance_policy_no"],
                 continues=True),
            Step(text="Read the status (active / inactive / needs pre-authorisation) to the patient. "
                      "Do not open the account or invoice screens -- that is the billing office's work.",
                 layer=_FIN, artefact="fhir:Coverage", fields=["payer_name"], continues=True,
                 caution="Eligibility is all this role needs; amounts owed are a different artefact and a different desk."),
        ],
    ),
    # ================================================== privacy requests
    # A patient asking about their own data is the Act's rights of the data
    # principal arriving at the desk. The desk logs and routes; it never
    # discloses, deletes or decides. Every one is a fhir:Task for the hospital's
    # data-protection contact.
    FunctionSpec(
        id="access_request",
        label="log a patient's request for a copy of their data",
        group=PRIVACY,
        synonyms=["copy of my data", "what data do you hold", "access request", "see my records",
                  "data access", "my personal data", "right to access", "copy of records"],
        purpose=_REG,
        artefacts={"fhir:Patient", "fhir:Task"},
        inputs=[_MRN],
        steps=[
            _open_record(_PA, "fhir:Patient"),
            _confirm_identity("A request from anyone but the patient, or a person lawfully acting "
                              "for them, is not an access request -- do not go on."),
            Step(text="Press {button} and log an access request: today's date, the channel "
                      "(in person) and the {label.mrn}. Nothing else.",
                 layer=_PA, artefact="fhir:Task", fields=["mrn"], action="privacy_request"),
            Step(text="Give the patient the request reference and the hospital's data-protection "
                      "contact. Do not print or hand over records at the desk.",
                 layer=_PA, artefact="fhir:Task", offscreen=True,
                 caution="DPDP right to access: the hospital answers through its data-protection contact; the desk logs the request, it does not disclose."),
        ],
    ),
    FunctionSpec(
        id="erasure_request",
        label="log a patient's request to erase their data",
        group=PRIVACY,
        synonyms=["delete my data", "erase my data", "erasure", "remove my records", "forget me",
                  "right to erasure", "delete my record"],
        purpose=_REG,
        artefacts={"fhir:Patient", "fhir:Task"},
        inputs=[_MRN],
        steps=[
            _open_record(_PA, "fhir:Patient"),
            _confirm_identity(),
            Step(text="Press {button} and log an erasure request: today's date, the channel and "
                      "the {label.mrn}.",
                 layer=_PA, artefact="fhir:Task", fields=["mrn"], action="privacy_request"),
            Step(text="Tell the patient the request will be reviewed: records the hospital must keep "
                      "by law are kept until that duty ends, and the rest is erased. Do not delete "
                      "or edit anything yourself.",
                 layer=_PA, artefact="fhir:Task", offscreen=True,
                 caution="DPDP right to erasure and storage limitation: the decision is the data-protection contact's, made against the hospital's retention duties -- never the desk's."),
        ],
    ),
    FunctionSpec(
        id="withdraw_consent",
        label="record a withdrawal of consent",
        group=PRIVACY,
        synonyms=["withdraw consent", "revoke consent", "no longer consent", "stop using my data",
                  "opt out", "consent withdrawal", "stop messages", "unsubscribe"],
        purpose=_REG,
        artefacts={"fhir:Patient", "fhir:Consent", "fhir:Task"},
        inputs=[
            _MRN,
            InputSlot(name="scope", prompt="What does the patient no longer agree to, in their words?",
                      example="reminder messages by SMS", category=_AD),
        ],
        steps=[
            _open_record(_PA, "fhir:Patient"),
            _confirm_identity(),
            Step(text="Press {button} and record the withdrawal as the patient put it: {scope}.",
                 layer=_PA, artefact="fhir:Consent", action="withdraw_consent",
                 caution="DPDP consent: withdrawing must be as easy as giving it -- record it now, without asking why."),
            Step(text="Press {button} and log it, so the data-protection contact can confirm what "
                      "stops. Tell the patient that care already given is not affected.",
                 layer=_PA, artefact="fhir:Task", fields=["mrn"], action="privacy_request"),
        ],
    ),
    FunctionSpec(
        id="privacy_grievance",
        label="log a complaint about how a patient's data was handled",
        group=PRIVACY,
        synonyms=["complaint", "grievance", "privacy complaint", "data was misused",
                  "unhappy with how my data", "data breach complaint", "complain"],
        purpose=_REG,
        artefacts={"fhir:Task"},
        inputs=[_MRN],
        steps=[
            Step(text="Open {module} and press {button}; log a grievance with today's date, the "
                      "channel and the {label.mrn}.",
                 layer=_PA, artefact="fhir:Task", fields=["mrn"], action="privacy_request"),
            Step(text="Write down what the patient says happened, in their words; add nothing from "
                      "their record.",
                 layer=_PA, artefact="fhir:Task", continues=True,
                 caution="A complaint is not a reason to open the patient's record."),
            Step(text="Give the patient the reference and the hospital's data-protection contact. "
                      "The hospital must answer; if the patient is not satisfied with the answer, "
                      "they may take it to the Data Protection Board.",
                 layer=_PA, artefact="fhir:Task", offscreen=True,
                 caution="DPDP grievance redressal: the hospital's own process comes first, then the Board."),
        ],
    ),
    # ========================================================= ward care
    FunctionSpec(
        id="confirm_identity",
        label="confirm a patient's identity before care",
        group=WARD,
        synonyms=["identify the patient", "positive identification", "check the wristband",
                  "confirm identity", "right patient", "id check", "wristband", "identity check"],
        purpose=_CARE,
        artefacts={"fhir:Patient"},
        categories={_DI, _QI},                  # who they are; never how to reach them
        inputs=[_MRN],
        steps=[
            Step(text="Ask the patient their full name and date of birth; do not say them first.",
                 layer=_PA, artefact="fhir:Patient", offscreen=True),
            Step(text="Open {module}, search for {mrn} and open the record; compare the "
                      "{label.full_name} and {label.date_of_birth} with the answers and with the wristband.",
                 layer=_PA, artefact="fhir:Patient", fields=["mrn", "full_name", "date_of_birth"],
                 caution="Read the two identifiers you need; the record also holds contact details this task does not."),
            Step(text="If anything differs, stop and escalate before any care is given.",
                 layer=_PA, artefact="fhir:Patient", offscreen=True),
        ],
    ),
    FunctionSpec(
        id="record_vitals",
        label="record a patient's vital signs",
        group=WARD,
        synonyms=["vitals", "observations", "bp", "blood pressure", "temperature", "pulse",
                  "chart obs", "record readings"],
        purpose=_CARE,
        artefacts={"fhir:Observation", "ieee11073:PoCD"},
        inputs=[
            _MRN,
            InputSlot(name="blood_pressure", prompt="Blood pressure?", example="128/82",
                      category=_CL, pattern=r"\d{2,3}\s*/\s*\d{2,3}"),
            InputSlot(name="pulse", prompt="Pulse (bpm)?", example="76",
                      category=_CL, pattern=r"\d{2,3}"),
            InputSlot(name="temperature", prompt="Temperature (C)?", example="37.1",
                      category=_CL, pattern=r"\d{2}(?:\.\d{1,2})?"),
        ],
        steps=[
            _open_record(_ANC, "fhir:Observation"),
            Step(text="Press {button}. If the bedside monitor is linked, accept its readings; "
                      "otherwise enter BP {blood_pressure}, pulse {pulse}, temperature {temperature}.",
                 layer=_ANC, artefact="ieee11073:PoCD", fields=["result_value"],
                 action="record_observation"),
            Step(text="Set the time taken and save. Flag any value outside the ward's early-warning range.",
                 layer=_ANC, artefact="fhir:Observation", fields=["result_value"], continues=True),
        ],
    ),
    FunctionSpec(
        id="view_medications",
        label="view the active medication list",
        group=WARD,
        synonyms=["medications", "meds", "drug chart", "what is the patient on", "prescriptions",
                  "allergies", "medication list"],
        purpose=_CARE,
        artefacts={"fhir:MedicationRequest", "fhir:AllergyIntolerance"},
        inputs=[_MRN],
        steps=[
            _open_record(_EHR, "fhir:MedicationRequest"),
            Step(text="Check the {label.allergy} entry first, before reading the list.",
                 layer=_EHR, artefact="fhir:AllergyIntolerance", fields=["allergy"], continues=True),
            Step(text="Read the {label.medication} entry -- active orders only; discontinued items "
                      "are in the history if you need them.",
                 layer=_EHR, artefact="fhir:MedicationRequest", fields=["medication"], continues=True,
                 caution="Open what the task needs. The chart holds more than the medication list."),
        ],
    ),
    FunctionSpec(
        id="record_medication_given",
        label="record a medication dose given",
        group=WARD,
        synonyms=["gave medication", "medication given", "administer", "dose given",
                  "medication administration", "chart a dose", "gave a dose"],
        purpose=_CARE,
        artefacts={"fhir:MedicationRequest", "fhir:AllergyIntolerance"},
        inputs=[
            _MRN,
            InputSlot(name="medication", prompt="Which medication?", example="Paracetamol 500 mg",
                      category=_CL),
            InputSlot(name="time_given", prompt="What time was it given?", example="14:30",
                      category=_AD, pattern=r"\d{1,2}[:.]\d{2}"),
        ],
        steps=[
            _open_record(_EHR, "fhir:MedicationRequest"),
            Step(text="Check the {label.allergy} entry against {medication} before you chart it.",
                 layer=_EHR, artefact="fhir:AllergyIntolerance", fields=["allergy"], continues=True),
            Step(text="Press {button}, select {medication} from the active orders and record it as "
                      "given at {time_given}.",
                 layer=_EHR, artefact="fhir:MedicationRequest", fields=["medication"],
                 action="record_dose",
                 caution="Chart only what was given, when it was given; a dose not given is charted as not given, with the reason."),
        ],
    ),
    FunctionSpec(
        id="view_diagnosis",
        label="look up a patient's diagnosis",
        group=WARD,
        synonyms=["diagnosis", "what is wrong with the patient", "condition", "problem list",
                  "why is the patient admitted"],
        purpose=_CARE,
        artefacts={"fhir:Condition"},
        inputs=[_MRN],
        steps=[
            _open_record(_EHR, "fhir:Condition"),
            Step(text="Read the {label.primary_diagnosis}; secondary conditions follow it.",
                 layer=_EHR, artefact="fhir:Condition", fields=["primary_diagnosis"],
                 caution="Clinical data: view it at the bedside or the station, never on a screen facing a corridor."),
        ],
    ),
    FunctionSpec(
        id="record_allergy",
        label="record an allergy",
        group=WARD,
        synonyms=["new allergy", "allergic", "add an allergy", "allergy found", "reaction to"],
        purpose=_CARE,
        artefacts={"fhir:AllergyIntolerance"},
        inputs=[
            _MRN,
            InputSlot(name="allergy", prompt="What is the patient allergic to, and what happened?",
                      example="Penicillin -- rash", category=_CL),
        ],
        steps=[
            _open_record(_EHR, "fhir:AllergyIntolerance"),
            Step(text="Press {button} and enter {allergy}: the substance and the reaction seen.",
                 layer=_EHR, artefact="fhir:AllergyIntolerance", fields=["allergy"],
                 action="add_allergy"),
            Step(text="Save. Tell the doctor and the pharmacy if a dose is due.",
                 layer=_EHR, artefact="fhir:AllergyIntolerance", offscreen=True),
        ],
    ),
    FunctionSpec(
        id="shift_handover",
        label="prepare a shift handover",
        group=WARD,
        synonyms=["handover", "handoff", "shift change", "who is on the ward", "end of shift",
                  "hand over"],
        purpose=_CARE,
        artefacts={"fhir:Encounter", "fhir:Condition"},
        inputs=[_WARD],
        steps=[
            Step(text="Open {module} and list the current encounters for {ward}.",
                 layer=_EHR, artefact="fhir:Encounter",
                 fields=["encounter_datetime", "attending_clinician"]),
            Step(text="For each patient, note the {label.primary_diagnosis} and anything outstanding "
                      "for the next shift -- nothing more.",
                 layer=_EHR, artefact="fhir:Condition", fields=["primary_diagnosis"],
                 caution="A handover sheet is clinical data on paper: hand it over in person and shred it when the shift ends."),
        ],
    ),
    FunctionSpec(
        id="discharge_checklist",
        label="prepare a discharge checklist",
        group=WARD,
        synonyms=["discharge", "going home", "send home", "discharge summary", "release patient",
                  "ready for discharge"],
        purpose=_CARE,
        artefacts={"fhir:Encounter", "fhir:MedicationRequest"},
        inputs=[
            _MRN,
            InputSlot(name="discharge_date", prompt="Planned discharge date?", example="2026-09-15",
                      category=_AD, pattern=_DATE, find=_ISO_DATE),
        ],
        steps=[
            Step(text="Open {module}, search for {mrn} and open the record; plan discharge for "
                      "{discharge_date}.",
                 layer=_EHR, artefact="fhir:Encounter", fields=["mrn", "encounter_datetime"]),
            Step(text="Reconcile the medication list: confirm what continues, what stops, and what is new.",
                 layer=_EHR, artefact="fhir:MedicationRequest", fields=["medication", "allergy"],
                 continues=True),
            Step(text="Complete the nursing items and press {button}. The bed release and billing "
                      "hand-offs happen from that flag -- you do not do them here.",
                 layer=_EHR, artefact="fhir:Encounter", action="ready_for_discharge",
                 caution="Nursing does not open the billing screens; the flag is the hand-off."),
        ],
    ),
    # ================================================ orders and results
    FunctionSpec(
        id="request_lab",
        label="request a laboratory test",
        group=ORDERS,
        synonyms=["lab", "order a test", "bloods", "send sample", "lab request", "pathology"],
        purpose=_CARE,
        artefacts={"fhir:ServiceRequest", "hl7:ORM"},
        inputs=[
            _MRN,
            InputSlot(name="test_name", prompt="Which test?", example="Full blood count", category=_CL),
            InputSlot(name="priority", prompt="Routine or urgent?", example="routine",
                      category=_AD, pattern=r"routine|urgent|stat"),
        ],
        steps=[
            Step(text="Open {module}, press {button} and enter the {label.mrn} {mrn}.",
                 layer=_ANC, artefact="fhir:ServiceRequest", fields=["mrn"], action="new_lab_request"),
            Step(text="Select {test_name}, set priority {priority}, and add the {label.specimen_type}.",
                 layer=_ANC, artefact="fhir:ServiceRequest", fields=["specimen_type"], continues=True),
            Step(text="Submit. The order goes to the laboratory as an ORM message; print the specimen "
                      "label from the confirmation.",
                 layer=_EHR, artefact="hl7:ORM", offscreen=True),
        ],
    ),
    FunctionSpec(
        id="view_lab_results",
        label="view a patient's lab results",
        group=ORDERS,
        synonyms=["lab results", "test results", "are the results back", "results", "bloods back",
                  "pathology report", "report back"],
        purpose=_CARE,
        artefacts={"fhir:DiagnosticReport", "hl7:ORU"},
        inputs=[_MRN],
        steps=[
            Step(text="Open {module} and search for {mrn}; each order is a row.",
                 layer=_ANC, artefact="fhir:DiagnosticReport", fields=["mrn", "order_id"]),
            Step(text="Open the order you need and read the {label.result_value} and the "
                      "{label.report_text}.",
                 layer=_ANC, artefact="fhir:DiagnosticReport", fields=["result_value", "report_text"]),
            Step(text="Results arrive from the laboratory as ORU messages; if one you expect is "
                      "missing, call the laboratory rather than ordering again.",
                 layer=_ANC, artefact="hl7:ORU", offscreen=True),
        ],
    ),
    # ==================================================== beds and wards
    FunctionSpec(
        id="allocate_bed",
        label="allocate a bed",
        group=BEDS,
        synonyms=["bed", "assign a bed", "bed management", "admit to ward", "admission", "admit"],
        purpose=_REG,
        artefacts={"fhir:Location", "hl7:ADT", "fhir:Encounter"},
        inputs=[_MRN, _WARD],
        steps=[
            _open_record(_PA, "hl7:ADT"),
            Step(text="Press {button} and choose a free bed in {ward}; the {label.admission_ward} and "
                      "{label.admission_datetime} are set from it.",
                 layer=_PA, artefact="fhir:Location", fields=["admission_ward", "admission_datetime"],
                 action="allocate_bed"),
            Step(text="Confirm. The admission goes out as an ADT A01 and the encounter's location "
                      "updates; check the ward board shows it.",
                 layer=_EHR, artefact="fhir:Encounter", fields=["encounter_datetime"], offscreen=True,
                 caution="You see where the patient is, not why -- the clinical content of the encounter stays closed."),
        ],
    ),
    FunctionSpec(
        id="transfer_patient",
        label="transfer a patient to another ward",
        group=BEDS,
        synonyms=["transfer", "move patient", "change ward", "move to another ward", "shift ward"],
        purpose=_REG,
        artefacts={"fhir:Location", "hl7:ADT", "fhir:Encounter"},
        inputs=[_MRN, _WARD],
        steps=[
            _open_record(_PA, "hl7:ADT"),
            Step(text="Press {button}, choose a free bed in {ward}, and confirm; the "
                      "{label.admission_ward} changes.",
                 layer=_PA, artefact="fhir:Location", fields=["admission_ward"], action="transfer"),
            Step(text="The transfer goes out as an ADT A02; the encounter's location updates by itself.",
                 layer=_EHR, artefact="fhir:Encounter", fields=["encounter_datetime"], offscreen=True),
        ],
    ),
    FunctionSpec(
        id="release_bed",
        label="discharge a patient and release the bed",
        group=BEDS,
        synonyms=["discharge", "release bed", "bed release", "close the admission", "free the bed"],
        purpose=_REG,
        artefacts={"fhir:Location", "hl7:ADT", "fhir:Encounter"},
        inputs=[_MRN],
        steps=[
            Step(text="Open {module}, search for {mrn} and open the record; go on only if the ward "
                      "has marked the patient ready for discharge.",
                 layer=_PA, artefact="hl7:ADT", fields=["mrn"]),
            Step(text="Press {button}. The discharge goes out as an ADT A03 and the bed shows free.",
                 layer=_PA, artefact="fhir:Location", fields=["admission_ward"], action="discharge"),
            Step(text="Billing picks up the encounter for the final invoice from here; you do not "
                      "open the clinical record.",
                 layer=_EHR, artefact="fhir:Encounter", fields=["encounter_datetime"], offscreen=True),
        ],
    ),
    FunctionSpec(
        id="ward_census",
        label="run a ward census",
        group=BEDS,
        synonyms=["census", "occupancy", "how many patients", "bed count", "ward report",
                  "midnight census"],
        purpose=_REG,
        artefacts={"fhir:Encounter", "fhir:Location", "hl7:ADT"},
        inputs=[
            _WARD,
            InputSlot(name="date", prompt="For which date?", example="2026-09-12",
                      category=_AD, pattern=_DATE, find=_ISO_DATE),
        ],
        steps=[
            Step(text="Open {module}, press {button} and choose {ward} and {date}.",
                 layer=_PA, artefact="fhir:Location", fields=["admission_ward"], action="ward_census"),
            Step(text="Run it. The report lists occupied beds and admission times, not diagnoses.",
                 layer=_EHR, artefact="fhir:Encounter", fields=["encounter_datetime"], offscreen=True,
                 caution="A census is a count of encounters; if the report offers clinical columns, leave them unticked."),
            Step(text="Export it to the dated shared-drive folder; the file carries {label.mrn}s, so it "
                      "stays inside the hospital network.",
                 layer=_PA, artefact="hl7:ADT", fields=["mrn"], continues=True,
                 caution="MRNs are direct identifiers -- storage limitation applies to the exported file too."),
        ],
    ),
    # =========================================================== billing
    FunctionSpec(
        id="open_billing_account",
        label="open a billing account",
        group=BILLING,
        synonyms=["new account", "billing account", "guarantor", "open an account", "create account"],
        purpose=_BILL,
        artefacts={"hl7:BAR", "fhir:Account"},
        inputs=[
            _MRN,
            InputSlot(name="payer", prompt="Who pays -- the patient, an insurer, or an employer?",
                      example="the patient", category=_FI),
        ],
        steps=[
            Step(text="Open {module}, press {button} and enter the {label.mrn} {mrn}.",
                 layer=_FIN, artefact="fhir:Account", fields=["mrn"], action="open_account"),
            Step(text="Record {payer} as the payer. Enter a guarantor's contact details only if the "
                      "payer is not the patient.",
                 layer=_FIN, artefact="hl7:BAR", fields=["payer_name"], continues=True,
                 caution="Contact details on an account are there to send the bill -- take them only for whoever receives it."),
        ],
    ),
    FunctionSpec(
        id="post_charges",
        label="post charges to an account",
        group=BILLING,
        synonyms=["post a charge", "add a charge", "charges", "missing charge", "charge entry"],
        purpose=_BILL,
        artefacts={"hl7:DFT", "fhir:Account"},
        inputs=[
            _MRN, _ENCOUNTER,
            InputSlot(name="charge", prompt="Which charge, and how much?",
                      example="Ward bed, 2 days -- 3000", category=_FI),
        ],
        steps=[
            Step(text="Open {module}, search for {mrn} and open the account for encounter {encounter_id}.",
                 layer=_FIN, artefact="fhir:Account", fields=["mrn", "invoice_id"]),
            Step(text="Press {button} and enter: {charge}.",
                 layer=_FIN, artefact="hl7:DFT", fields=["billed_amount"], action="post_charge"),
            Step(text="Save. The charge is posted as a DFT P03 and shows on the account at once.",
                 layer=_FIN, artefact="hl7:DFT", continues=True),
        ],
    ),
    FunctionSpec(
        id="generate_invoice",
        label="generate an invoice",
        group=BILLING,
        synonyms=["invoice", "bill", "raise the bill", "billing", "final bill", "generate bill"],
        purpose=_BILL,
        artefacts={"fhir:Account", "fhir:Invoice", "hl7:DFT"},
        inputs=[_MRN, _ENCOUNTER],
        steps=[
            Step(text="Open {module}, search for {mrn} and open the account for encounter {encounter_id}.",
                 layer=_FIN, artefact="fhir:Account", fields=["mrn", "invoice_id"]),
            Step(text="Review the posted charges; post any the departments have not yet sent.",
                 layer=_FIN, artefact="hl7:DFT", fields=["billed_amount"], continues=True),
            Step(text="Press {button}. Confirm the {label.payer_name} and where the invoice goes, then finalise.",
                 layer=_FIN, artefact="fhir:Invoice", fields=["invoice_id", "billed_amount", "payer_name"],
                 action="generate_invoice",
                 caution="The invoice names the payer and where it goes -- that is why billing may see contact data and nursing may not."),
        ],
    ),
    FunctionSpec(
        id="reconcile_payment",
        label="reconcile a payer settlement",
        group=BILLING,
        synonyms=["reconcile", "payment received", "settlement", "remittance", "claim paid",
                  "insurance paid", "match payment"],
        purpose=_BILL,
        artefacts={"fhir:ClaimResponse", "fhir:Coverage"},
        inputs=[
            InputSlot(name="invoice_id", prompt="Which invoice number?", example="INV-2026-01187",
                      category=_FI, pattern=_REF, find=r"\bINV-[\d-]{4,}\b"),
        ],
        steps=[
            Step(text="Open {module} and search for invoice {invoice_id}.",
                 layer=_FIN, artefact="fhir:ClaimResponse", fields=["invoice_id"]),
            Step(text="Open it, match the payer's remittance to the invoice lines, and note any shortfall.",
                 layer=_FIN, artefact="fhir:ClaimResponse", fields=["billed_amount", "payer_name"]),
            Step(text="Press {button}: settled or partly settled. Do not open the claim itself -- "
                      "adjudication detail carries diagnosis codes and is not part of reconciliation.",
                 layer=_FIN, artefact="fhir:Coverage", fields=["insurance_policy_no"],
                 action="record_settlement",
                 caution="fhir:Claim is deliberately outside every role here; the settlement response is enough."),
        ],
    ),
]

BY_ID: dict[str, FunctionSpec] = {spec.id: spec for spec in REGISTRY}

GROUPS: list[str] = list(dict.fromkeys(spec.group for spec in REGISTRY))


def capabilities(role: StaffRole) -> list[FunctionSpec]:
    """The functions this role may be guided through -- derived from the gate, not stored."""

    return [spec for spec in REGISTRY if spec.permitted_for(role)]


def capabilities_by_group(role: StaffRole) -> list[tuple[str, list[FunctionSpec]]]:
    able = capabilities(role)
    return [(g, [s for s in able if s.group == g]) for g in GROUPS if any(s.group == g for s in able)]
