"""Tests for role-based access derived from purposes and interop artefacts."""

from __future__ import annotations

from itertools import combinations

from compliance.models import FieldCategory, Purpose
from compliance.policy import PURPOSE_POLICY, policy_for
from compliance.roles import (
    ARTEFACTS,
    ROLE_POLICY,
    StaffRole,
    authorise,
    describe,
    role_policy,
    unassigned_artefacts,
)
from interop.mapping import standards_for

CLINICAL = FieldCategory.CLINICAL
FINANCIAL = FieldCategory.FINANCIAL
CONTACT = FieldCategory.CONTACT


# --- the purpose table, now with three ---------------------------------------

def test_three_purposes_and_all_pairwise_non_nested():
    assert len(PURPOSE_POLICY) == 3
    for a, b in combinations(PURPOSE_POLICY, 2):
        sa, sb = policy_for(a).allowed_categories, policy_for(b).allowed_categories
        assert not sa.issubset(sb), f"{a.value} nests inside {b.value}"
        assert not sb.issubset(sa), f"{b.value} nests inside {a.value}"


# --- the artefact vocabulary is consistent with the interop mapping ----------

def test_every_artefact_standard_is_one_its_layer_carries():
    # The role file must not invent a layer/standard pairing that
    # interop.mapping does not recognise.
    for key, artefact in ARTEFACTS.items():
        assert artefact.standard in standards_for(artefact.layer), key


def test_every_role_artefact_exists_in_the_vocabulary():
    for role, policy in ROLE_POLICY.items():
        missing = policy.artefacts - set(ARTEFACTS)
        assert not missing, f"{role.value}: {missing}"


def test_claim_dicom_and_audit_are_deliberately_granted_to_nobody():
    assert unassigned_artefacts() == ["dicom:Study", "fhir:AuditEvent", "fhir:Claim"]


# --- derived scopes ----------------------------------------------------------

def test_reception_and_administrator_never_touch_clinical_data():
    for role in (StaffRole.RECEPTION, StaffRole.ADMINISTRATOR):
        assert CLINICAL not in role_policy(role).allowed_categories()


def test_nurse_never_touches_financial_or_contact_data():
    scope = role_policy(StaffRole.NURSE).allowed_categories()
    assert FINANCIAL not in scope
    assert CONTACT not in scope
    assert CLINICAL in scope


def test_effective_scope_is_the_intersection_not_either_source_alone():
    # The nurse handles fhir:Patient, which carries contact data; care
    # coordination does not make contact data necessary. Purpose alone would
    # over-grant nothing here, but artefact alone would grant contact -- and the
    # intersection must remove it.
    nurse = role_policy(StaffRole.NURSE)
    assert CONTACT in nurse.artefact_scope()
    assert CONTACT not in nurse.purpose_scope()
    assert CONTACT not in nurse.allowed_categories()


def test_purpose_alone_would_over_grant_reception_and_artefacts_stop_it():
    # Reception acts under billing (eligibility), so purpose scope includes
    # financial data. Its artefacts include Coverage but not Invoice or Account,
    # which is what keeps it away from raising bills.
    reception = role_policy(StaffRole.RECEPTION)
    assert FINANCIAL in reception.purpose_scope()
    assert "fhir:Coverage" in reception.artefacts
    assert not {"fhir:Invoice", "fhir:Account"} & reception.artefacts


# --- the gate, one denial per principle --------------------------------------

def test_out_of_purpose_request_is_declined_under_purpose_limitation():
    decision = authorise(StaffRole.RECEPTION, Purpose.CARE_COORDINATION, {"fhir:Condition"})
    assert not decision.allowed
    assert decision.rule_id == "PL-01"
    assert "no lawful purpose" in decision.reasons[0]


def test_unnecessary_category_is_declined_under_minimisation():
    # Claim is lawful-purpose for the administrator (billing) but carries coded
    # diagnosis, which billing settlement does not need: this is the claims
    # adjudication exclusion firing automatically.
    decision = authorise(StaffRole.ADMINISTRATOR, Purpose.BILLING_SETTLEMENT, {"fhir:Claim"})
    assert not decision.allowed
    assert decision.rule_id == "DM-01"
    assert decision.denied_categories == ["clinical"]


def test_unhandled_artefact_is_declined_under_access_control():
    decision = authorise(
        StaffRole.RECEPTION, Purpose.BILLING_SETTLEMENT, {"fhir:Invoice", "fhir:Account"}
    )
    assert not decision.allowed
    assert decision.rule_id == "SS-01"
    assert decision.denied_artefacts == ["fhir:Account", "fhir:Invoice"]


def test_unknown_artefact_cannot_be_assessed_and_is_declined():
    decision = authorise(StaffRole.NURSE, Purpose.CARE_COORDINATION, {"fhir:Nonsense"})
    assert not decision.allowed and decision.rule_id == "SS-01"


def test_permitted_action_is_permitted():
    decision = authorise(StaffRole.RECEPTION, Purpose.BILLING_SETTLEMENT, {"fhir:Coverage"})
    assert decision.allowed and decision.rule_id is None
    decision = authorise(
        StaffRole.NURSE, Purpose.CARE_COORDINATION, {"fhir:Observation", "ieee11073:PoCD"}
    )
    assert decision.allowed


def test_caller_can_narrow_categories_to_what_the_action_actually_reads():
    # Reading the whole Patient resource for care is over-collection (contact
    # data); reading only its identifiers to match the patient is fine.
    whole = authorise(StaffRole.NURSE, Purpose.CARE_COORDINATION, {"fhir:Patient"})
    assert not whole.allowed and whole.rule_id == "DM-01"
    narrowed = authorise(
        StaffRole.NURSE, Purpose.CARE_COORDINATION, {"fhir:Patient"},
        categories={FieldCategory.DIRECT_IDENTIFIER, FieldCategory.QUASI_IDENTIFIER},
    )
    assert narrowed.allowed


def test_same_request_three_roles_three_different_outcomes():
    # Raising an invoice: admin may; reception fails access control; nurse
    # fails purpose. Three roles, three distinct reasons -- this is the
    # differentiation the guidance agent is built on.
    request = (Purpose.BILLING_SETTLEMENT, {"fhir:Invoice"})
    outcomes = {
        role: authorise(role, *request) for role in StaffRole
    }
    assert outcomes[StaffRole.ADMINISTRATOR].allowed
    assert outcomes[StaffRole.RECEPTION].rule_id == "SS-01"
    assert outcomes[StaffRole.NURSE].rule_id == "PL-01"


def test_describe_is_readable_and_names_what_is_withheld():
    text = describe(StaffRole.RECEPTION)
    assert "never      : clinical" in text
    assert "fhir:Coverage" in text
