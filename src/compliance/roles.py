"""Role-based access, expressed in the vocabulary of the interoperability standards.

This is the second application of the compliance policy. ``policy.py`` says what
data each *purpose* may touch; this file says what each *staff role* may be
instructed to do, and it derives that from two independent sources rather than
listing it by hand:

1. **The purposes a role acts under.** A nurse acts for care coordination; the
   accounts office acts for billing settlement; the front desk acts for
   registration (and eligibility checks, which are the billing purpose). A role
   gets no access at all to data outside its purposes' envelopes -- so the gate
   *is* purpose limitation, applied to a person instead of to an extraction.

2. **The interoperability artefacts a role handles.** HL7 v2 message types, FHIR
   resource types, DICOM studies, ISO/IEEE 11073 device observations. Access is
   assumed to follow the standards: a role may touch a data category only where
   some artefact it legitimately handles under HL7 / FHIR / DICOM / 11073 carries
   it. This is what stops purpose alone from over-granting -- billing settlement
   permits financial data, but reception handles ``Coverage`` (eligibility) and
   not ``Invoice`` or ``Account``, so it cannot be walked through raising a bill.

A role's effective scope is the **intersection** of the two: lawful under a
purpose it acts for, *and* present in an artefact it handles per the standards.
Neither alone is sufficient, and the tests hold both.

Three checks, three principles, in the order a data-protection officer would ask:

    Is there a lawful purpose?         -> PL-01  purpose limitation
    Is the data necessary for it?      -> DM-01  data minimisation
    Is this role permitted to touch it? -> SS-01  security safeguards (access control)

# DPDP Act 2023 -- purpose limitation, data minimisation and security safeguards
# principles, applied to who may be told to do what. Section citations are a
# report-time task, as elsewhere in this package.

Deliberately NOT granted to any role: ``fhir:Claim`` (carries coded diagnosis --
adjudication is an unmodelled purpose, see ``policy.py``) and ``dicom:Study`` (no
imaging role is modelled). Both are kept in the vocabulary so the gate can be
seen refusing them for the right reason rather than because they are unknown.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from compliance.models import FieldCategory, Purpose
from compliance.policy import PURPOSE_POLICY, policy_for
from interop.layers import HISLayer
from interop.mapping import InteropStandard


class StaffRole(str, Enum):
    """Staff roles the guidance agent serves. Three is enough to show differentiation."""

    RECEPTION = "reception"
    NURSE = "nurse"
    ADMINISTRATOR = "administrator"


# --------------------------------------------------------------------------- #
# Interoperability artefact vocabulary
# --------------------------------------------------------------------------- #

class InteropArtefact(BaseModel, frozen=True):
    """One standard-defined object a role might handle, and what it carries.

    ``categories`` is the coarse DPDP content of the artefact as the standard
    defines it -- a FHIR ``Patient`` carries identifiers, demographics and
    contact details whether or not a given deployment fills every element. It is
    a ceiling on what handling the artefact can expose, not a field inventory.
    """

    standard: InteropStandard
    name: str
    layer: HISLayer
    categories: frozenset[FieldCategory]
    note: str = ""


_DI = FieldCategory.DIRECT_IDENTIFIER
_QI = FieldCategory.QUASI_IDENTIFIER
_CL = FieldCategory.CLINICAL
_FI = FieldCategory.FINANCIAL
_AD = FieldCategory.ADMINISTRATIVE
_CO = FieldCategory.CONTACT

ARTEFACTS: dict[str, InteropArtefact] = {
    # --- HL7 v2 message types -------------------------------------------------
    "hl7:ADT": InteropArtefact(
        standard=InteropStandard.HL7_V2, name="ADT (A01 admit / A04 register / A08 update)",
        layer=HISLayer.PATIENT_ADMINISTRATION, categories=frozenset({_DI, _QI, _CO, _AD}),
        note="admit / discharge / transfer -- registration and bed movement",
    ),
    "hl7:SIU": InteropArtefact(
        standard=InteropStandard.HL7_V2, name="SIU (S12 new appointment / S13 reschedule)",
        layer=HISLayer.PATIENT_ADMINISTRATION, categories=frozenset({_DI, _AD}),
        note="scheduling information unsolicited",
    ),
    "hl7:ORM": InteropArtefact(
        standard=InteropStandard.HL7_V2, name="ORM (O01 general order)",
        layer=HISLayer.CLINICAL_EHR, categories=frozenset({_DI, _CL, _AD}),
        note="clinical orders, e.g. a laboratory request",
    ),
    "hl7:ORU": InteropArtefact(
        standard=InteropStandard.HL7_V2, name="ORU (R01 observation result)",
        layer=HISLayer.ANCILLARY_DEPARTMENTAL, categories=frozenset({_DI, _CL}),
        note="results returning from a department",
    ),
    "hl7:DFT": InteropArtefact(
        standard=InteropStandard.HL7_V2, name="DFT (P03 detail financial transaction)",
        layer=HISLayer.ADMINISTRATIVE_FINANCIAL, categories=frozenset({_DI, _FI}),
        note="charges posted against an account",
    ),
    "hl7:BAR": InteropArtefact(
        standard=InteropStandard.HL7_V2, name="BAR (P01 add billing account)",
        layer=HISLayer.ADMINISTRATIVE_FINANCIAL, categories=frozenset({_DI, _FI, _CO}),
        note="billing account with guarantor details",
    ),
    # --- FHIR R4 resource types -----------------------------------------------
    "fhir:Patient": InteropArtefact(
        standard=InteropStandard.FHIR, name="Patient",
        layer=HISLayer.PATIENT_ADMINISTRATION, categories=frozenset({_DI, _QI, _CO}),
    ),
    "fhir:Appointment": InteropArtefact(
        standard=InteropStandard.FHIR, name="Appointment",
        layer=HISLayer.PATIENT_ADMINISTRATION, categories=frozenset({_DI, _AD}),
    ),
    "fhir:Schedule": InteropArtefact(
        standard=InteropStandard.FHIR, name="Schedule / Slot",
        layer=HISLayer.PATIENT_ADMINISTRATION, categories=frozenset({_AD}),
    ),
    "fhir:Location": InteropArtefact(
        standard=InteropStandard.FHIR, name="Location (ward / bed)",
        layer=HISLayer.PATIENT_ADMINISTRATION, categories=frozenset({_AD}),
    ),
    "fhir:Encounter": InteropArtefact(
        standard=InteropStandard.FHIR, name="Encounter",
        layer=HISLayer.CLINICAL_EHR, categories=frozenset({_DI, _AD}),
        note="class, period, location -- the administrative shell of a visit",
    ),
    "fhir:Condition": InteropArtefact(
        standard=InteropStandard.FHIR, name="Condition",
        layer=HISLayer.CLINICAL_EHR, categories=frozenset({_DI, _CL}),
    ),
    "fhir:MedicationRequest": InteropArtefact(
        standard=InteropStandard.FHIR, name="MedicationRequest / MedicationAdministration",
        layer=HISLayer.CLINICAL_EHR, categories=frozenset({_DI, _CL}),
    ),
    "fhir:AllergyIntolerance": InteropArtefact(
        standard=InteropStandard.FHIR, name="AllergyIntolerance",
        layer=HISLayer.CLINICAL_EHR, categories=frozenset({_DI, _CL}),
    ),
    "fhir:ServiceRequest": InteropArtefact(
        standard=InteropStandard.FHIR, name="ServiceRequest",
        layer=HISLayer.ANCILLARY_DEPARTMENTAL, categories=frozenset({_DI, _CL, _AD}),
        note="a lab or imaging order",
    ),
    "fhir:Observation": InteropArtefact(
        standard=InteropStandard.FHIR, name="Observation",
        layer=HISLayer.ANCILLARY_DEPARTMENTAL, categories=frozenset({_DI, _CL}),
        note="vitals and results",
    ),
    "fhir:DiagnosticReport": InteropArtefact(
        standard=InteropStandard.FHIR, name="DiagnosticReport",
        layer=HISLayer.ANCILLARY_DEPARTMENTAL, categories=frozenset({_DI, _CL}),
    ),
    "fhir:Coverage": InteropArtefact(
        standard=InteropStandard.FHIR, name="Coverage",
        layer=HISLayer.ADMINISTRATIVE_FINANCIAL, categories=frozenset({_DI, _FI}),
        note="insurance eligibility -- who pays, not what is owed",
    ),
    "fhir:Account": InteropArtefact(
        standard=InteropStandard.FHIR, name="Account",
        layer=HISLayer.ADMINISTRATIVE_FINANCIAL, categories=frozenset({_DI, _FI}),
    ),
    "fhir:Invoice": InteropArtefact(
        standard=InteropStandard.FHIR, name="Invoice",
        layer=HISLayer.ADMINISTRATIVE_FINANCIAL, categories=frozenset({_DI, _FI, _CO}),
        note="an invoice must name and reach the payer",
    ),
    "fhir:ClaimResponse": InteropArtefact(
        standard=InteropStandard.FHIR, name="ClaimResponse / PaymentReconciliation",
        layer=HISLayer.ADMINISTRATIVE_FINANCIAL, categories=frozenset({_DI, _FI}),
        note="what the payer settled -- reconciliation, not adjudication",
    ),
    "fhir:Claim": InteropArtefact(
        standard=InteropStandard.FHIR, name="Claim",
        layer=HISLayer.ADMINISTRATIVE_FINANCIAL, categories=frozenset({_DI, _FI, _CL}),
        note="carries coded diagnosis; adjudication is an unmodelled purpose -- granted to no role",
    ),
    # --- DICOM and ISO/IEEE 11073 ---------------------------------------------
    "dicom:Study": InteropArtefact(
        standard=InteropStandard.DICOM, name="Study / Series metadata",
        layer=HISLayer.ANCILLARY_DEPARTMENTAL, categories=frozenset({_DI, _CL}),
        note="imaging; no radiology role is modelled -- granted to no role",
    ),
    "ieee11073:PoCD": InteropArtefact(
        standard=InteropStandard.ISO_IEEE_11073, name="Point-of-care device observation",
        layer=HISLayer.ANCILLARY_DEPARTMENTAL, categories=frozenset({_CL}),
        note="monitor-sourced vitals",
    ),
}


# --------------------------------------------------------------------------- #
# Role policy
# --------------------------------------------------------------------------- #

class RolePolicy(BaseModel):
    """What one staff role acts for, and what it handles per the standards."""

    description: str
    purposes: set[Purpose]
    artefacts: set[str]                 # keys into ARTEFACTS

    def purpose_scope(self) -> set[FieldCategory]:
        """Categories lawful under at least one of the role's purposes."""

        scope: set[FieldCategory] = set()
        for purpose in self.purposes:
            scope |= policy_for(purpose).allowed_categories
        return scope

    def artefact_scope(self) -> set[FieldCategory]:
        """Categories carried by at least one artefact the role handles."""

        scope: set[FieldCategory] = set()
        for key in self.artefacts:
            scope |= ARTEFACTS[key].categories
        return scope

    def allowed_categories(self) -> set[FieldCategory]:
        """The role's effective scope: lawful for a purpose AND handled per a standard."""

        return self.purpose_scope() & self.artefact_scope()

    def layers(self) -> set[HISLayer]:
        return {ARTEFACTS[key].layer for key in self.artefacts}


ROLE_POLICY: dict[StaffRole, RolePolicy] = {
    StaffRole.RECEPTION: RolePolicy(
        description=(
            "Front desk: registers and identifies patients, books and reschedules, "
            "checks in arrivals, verifies who will pay. Never sees clinical data; "
            "sees insurance eligibility but not accounts, invoices or claims."
        ),
        # Eligibility checking is the billing purpose, so reception acts under it --
        # but the artefact set below stops that purpose from over-granting.
        purposes={Purpose.PATIENT_REGISTRATION, Purpose.BILLING_SETTLEMENT},
        artefacts={
            "hl7:ADT", "hl7:SIU",
            "fhir:Patient", "fhir:Appointment", "fhir:Schedule", "fhir:Coverage",
        },
    ),
    StaffRole.NURSE: RolePolicy(
        description=(
            "Ward nursing: records vitals, reads the active medication list and "
            "allergies, raises lab requests, reads results, prepares discharge. "
            "Identifies the patient but has no need of contact or financial data."
        ),
        purposes={Purpose.CARE_COORDINATION},
        artefacts={
            "hl7:ORM", "hl7:ORU",
            "fhir:Patient", "fhir:Encounter", "fhir:Condition",
            "fhir:MedicationRequest", "fhir:AllergyIntolerance",
            "fhir:ServiceRequest", "fhir:Observation", "fhir:DiagnosticReport",
            "ieee11073:PoCD",
        },
    ),
    StaffRole.ADMINISTRATOR: RolePolicy(
        description=(
            "Hospital administration: bed and ward allocation, census, billing "
            "accounts, invoices, payer reconciliation. Sees the administrative "
            "shell of a visit but never its clinical content."
        ),
        purposes={Purpose.BILLING_SETTLEMENT, Purpose.PATIENT_REGISTRATION},
        artefacts={
            "hl7:ADT", "hl7:DFT", "hl7:BAR",
            "fhir:Patient", "fhir:Encounter", "fhir:Location",
            "fhir:Coverage", "fhir:Account", "fhir:Invoice", "fhir:ClaimResponse",
        },
    ),
}


def role_policy(role: StaffRole) -> RolePolicy:
    return ROLE_POLICY[role]


# --------------------------------------------------------------------------- #
# The gate
# --------------------------------------------------------------------------- #

class AccessDecision(BaseModel):
    """Whether a role may be instructed to perform an action, and why."""

    role: StaffRole
    purpose: Purpose
    allowed: bool
    rule_id: str | None = None          # the rule that denied, when denied
    provision: str | None = None
    reasons: list[str] = Field(default_factory=list)
    denied_artefacts: list[str] = Field(default_factory=list)
    denied_categories: list[str] = Field(default_factory=list)

    def one_line(self) -> str:
        if self.allowed:
            return f"permitted: {self.role.value} may act for {self.purpose.value}"
        return f"declined [{self.rule_id}]: {self.reasons[0]}"


def authorise(
    role: StaffRole,
    purpose: Purpose,
    artefacts: set[str],
    categories: set[FieldCategory] | None = None,
) -> AccessDecision:
    """Decide whether ``role`` may be guided through an action.

    ``artefacts`` are the standard-defined objects the action touches;
    ``categories`` defaults to the union of what those artefacts carry and may be
    narrowed by the caller when an action reads only part of an artefact.
    """

    policy = role_policy(role)

    # An artefact the vocabulary does not describe cannot be assessed at all, so
    # it is refused before anything else is derived from it.
    # DPDP Act 2023 -- security safeguards: unassessable access is not safe access.
    unknown = sorted(k for k in artefacts if k not in ARTEFACTS)
    if unknown:
        return AccessDecision(
            role=role, purpose=purpose, allowed=False,
            rule_id="SS-01", provision="DPDP Act 2023 - security safeguards",
            reasons=[f"Unrecognised artefact(s): {', '.join(unknown)}; access cannot be assessed."],
            denied_artefacts=unknown,
        )

    if categories is None:
        categories = set()
        for key in artefacts:
            categories |= ARTEFACTS[key].categories

    # 1. Lawful purpose.
    # DPDP Act 2023 -- purpose limitation: a role may only be guided through
    # processing for a purpose it lawfully acts under.
    if purpose not in policy.purposes:
        return AccessDecision(
            role=role, purpose=purpose, allowed=False,
            rule_id="PL-01", provision="DPDP Act 2023 - purpose limitation",
            reasons=[
                f"{role.value} has no lawful purpose to act under "
                f"'{purpose.value}'; its purposes are "
                + ", ".join(sorted(p.value for p in policy.purposes)) + ".",
            ],
        )

    # 2. Necessity for that purpose.
    # DPDP Act 2023 -- data minimisation: even a lawful purpose does not make
    # every category necessary.
    excess = categories - policy_for(purpose).allowed_categories
    if excess:
        listed = sorted(c.value for c in excess)
        return AccessDecision(
            role=role, purpose=purpose, allowed=False,
            rule_id="DM-01", provision="DPDP Act 2023 - data minimisation",
            reasons=[
                f"The action would touch {', '.join(listed)} data, which is not "
                f"necessary for '{purpose.value}'.",
            ],
            denied_categories=listed,
        )

    # 3. Access control per the standards.
    # DPDP Act 2023 -- security safeguards: role-based access control over the
    # artefacts a role handles is a reasonable safeguard, and this is it.
    outside = sorted(artefacts - policy.artefacts)
    if outside:
        described = ", ".join(f"{k} ({ARTEFACTS[k].name})" for k in outside)
        return AccessDecision(
            role=role, purpose=purpose, allowed=False,
            rule_id="SS-01", provision="DPDP Act 2023 - security safeguards",
            reasons=[
                f"{role.value} does not handle {described} under the "
                f"interoperability standards; access control declines it.",
            ],
            denied_artefacts=outside,
        )

    return AccessDecision(
        role=role, purpose=purpose, allowed=True,
        reasons=[
            f"'{purpose.value}' is a lawful purpose for {role.value}; the categories "
            f"touched are necessary for it; every artefact is one {role.value} handles.",
        ],
    )


def describe(role: StaffRole) -> str:
    """Human-readable summary of one role's derived scope, for docs and demos."""

    policy = role_policy(role)
    lines = [
        f"{role.value}: {policy.description}",
        "  purposes   : " + ", ".join(sorted(p.value for p in policy.purposes)),
        "  artefacts  : " + ", ".join(sorted(policy.artefacts)),
        "  layers     : " + ", ".join(sorted(l.value for l in policy.layers())),
        "  may touch  : " + ", ".join(sorted(c.value for c in policy.allowed_categories())),
    ]
    withheld = set(FieldCategory) - policy.allowed_categories()
    lines.append("  never      : " + (", ".join(sorted(c.value for c in withheld)) or "-"))
    return "\n".join(lines)


def unassigned_artefacts() -> list[str]:
    """Artefacts in the vocabulary that no role may handle -- by design."""

    granted: set[str] = set()
    for policy in ROLE_POLICY.values():
        granted |= policy.artefacts
    return sorted(set(ARTEFACTS) - granted)


__all__ = [
    "StaffRole", "InteropArtefact", "ARTEFACTS", "RolePolicy", "ROLE_POLICY",
    "role_policy", "AccessDecision", "authorise", "describe", "unassigned_artefacts",
    "PURPOSE_POLICY",
]
