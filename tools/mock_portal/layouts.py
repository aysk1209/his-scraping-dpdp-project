"""How the fixture portal is laid out -- and how a vendor update re-lays it.

A layout is everything about the portal that a release could change without
changing the data: module names and paths, which columns the list shows and
which only the record page shows, how headers are labelled, and what the buttons
say. ``v1`` is the portal every benchmark has run against; it is byte-for-byte
the old fixture plus the buttons. ``v2`` is the same hospital after an update:

- every module renamed and moved (``/m/registration/`` -> ``/app/front-office/``);
- billing split into two modules (accounts, and insurance & payers);
- two fields moved off the list onto the record page;
- headers relabelled ("UHID" for the record number), one of them to a label the
  hospital's alias file does not yet know ("Unit");
- every button renamed, one of them ("Close episode") to words outside the
  assistant's vocabulary.

The two deliberate gaps are the point: they are what an update looks like when it
surprises you, and the assistant must withhold those steps rather than guess.

Buttons are inert. They post to a route that answers "read-only", and the
crawler never presses them -- it reads their labels, as a person scanning the
screen would.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from interop.layers import HISLayer

_PA = HISLayer.PATIENT_ADMINISTRATION
_EHR = HISLayer.CLINICAL_EHR
_ANC = HISLayer.ANCILLARY_DEPARTMENTAL
_FIN = HISLayer.ADMINISTRATIVE_FINANCIAL
_INT = HISLayer.INFRASTRUCTURE_INTEGRATION


@dataclass(frozen=True)
class ModuleLayout:
    slug: str
    title: str
    layer: HISLayer
    list_columns: tuple[str, ...]
    record_fields: tuple[str, ...] | None = None     # None: every field of the record
    list_actions: tuple[str, ...] = ()               # button labels on the list page
    record_actions: tuple[str, ...] = ()             # button labels on the record page


@dataclass(frozen=True)
class PortalLayout:
    name: str
    prefix: str                                      # "/m/" -> /m/<slug>/
    record_segment: str                              # "record" -> /m/<slug>/record/<id>
    modules: tuple[ModuleLayout, ...]
    labels: dict[str, str] = field(default_factory=dict)   # field -> header as displayed


V1 = PortalLayout(
    name="v1",
    prefix="/m/",
    record_segment="record",
    modules=(
        ModuleLayout(
            "registration", "Patient Registration", _PA,
            ("mrn", "full_name", "sex", "admission_ward"),
            list_actions=("New patient", "Log privacy request", "Ward census"),
            record_actions=("Edit details", "Mark arrived", "Book appointment", "Reschedule",
                            "Cancel appointment", "Allocate bed", "Transfer", "Discharge",
                            "Record consent withdrawal", "Log privacy request"),
        ),
        ModuleLayout(
            "clinical", "Clinical Records", _EHR,
            ("mrn", "encounter_datetime", "primary_diagnosis", "attending_clinician"),
            record_actions=("Record dose given", "Add allergy", "Ready for discharge"),
        ),
        ModuleLayout(
            "departments", "Departmental Orders", _ANC,
            ("mrn", "order_id", "specimen_type", "imaging_modality"),
            list_actions=("New lab request",),
            record_actions=("Record observation",),
        ),
        ModuleLayout(
            "billing", "Billing & Accounts", _FIN,
            ("mrn", "invoice_id", "billed_amount", "payer_name"),
            list_actions=("Open account", "Check eligibility"),
            record_actions=("Post charge", "Generate invoice", "Record settlement"),
        ),
        ModuleLayout(
            "integration", "Audit Log", _INT,
            ("audit_event_id", "event_timestamp", "actor_role", "action"),
        ),
    ),
)

V2 = PortalLayout(
    name="v2",
    prefix="/app/",
    record_segment="view",
    modules=(
        ModuleLayout(
            "front-office", "Front Office", _PA,
            ("mrn", "full_name", "sex"),                                   # ward moved to the record page
            list_actions=("Add registration", "Data protection request", "Occupancy report"),
            record_actions=("Update demographics", "Check-in", "New appointment", "Change appointment",
                            "Cancel booking", "Assign bed", "Transfer ward", "Close episode",
                            "Withdraw consent", "Data protection request"),
        ),
        ModuleLayout(
            "chart", "Patient Chart", _EHR,
            ("mrn", "encounter_datetime", "attending_clinician"),          # diagnosis moved to the record page
            record_actions=("Administer", "New allergy", "Mark fit for discharge"),
        ),
        ModuleLayout(
            "diagnostics", "Diagnostics", _ANC,
            ("mrn", "order_id", "specimen_type", "imaging_modality"),
            list_actions=("Order test",),
            record_actions=("Add vitals",),
        ),
        ModuleLayout(                                                      # billing, split in two
            "accounts", "Accounts", _FIN,
            ("mrn", "invoice_id", "billed_amount"),
            record_fields=("mrn", "invoice_id", "billed_amount"),
            list_actions=("New account",),
            record_actions=("Add charge", "Create bill", "Mark settled"),
        ),
        ModuleLayout(
            "payers", "Insurance & Payers", _FIN,
            ("mrn", "payer_name"),
            record_fields=("mrn", "payer_name", "insurance_policy_no"),
            list_actions=("Verify coverage",),
        ),
        ModuleLayout(
            "activity", "System Activity", _INT,
            ("audit_event_id", "event_timestamp", "actor_role", "action"),
        ),
    ),
    labels={
        "mrn": "UHID", "full_name": "Patient Name", "date_of_birth": "DOB",
        "admission_ward": "Unit", "attending_clinician": "Consultant",
        "billed_amount": "Amount (INR)", "payer_name": "Payer",
        "insurance_policy_no": "Policy No.",
    },
)

# The hospital's alias file as it stood after reading the release notes: every
# relabelled header but one. "Unit" was missed, which is what the update check
# has to catch.
V2_FIELD_ALIASES: dict[str, str] = {
    label: name for name, label in V2.labels.items() if label != "Unit"
}

LAYOUTS: dict[str, PortalLayout] = {"v1": V1, "v2": V2}

__all__ = ["ModuleLayout", "PortalLayout", "V1", "V2", "V2_FIELD_ALIASES", "LAYOUTS"]
