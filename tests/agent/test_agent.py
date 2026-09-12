"""Tests for the rule-based staff-guidance agent.

Two families. *Groundedness*: every instruction refers to things the HIS model
actually has, checked against the artefact vocabulary and the field catalogue.
*Behaviour*: recognition, disambiguation, the gate running before any input is
collected, slot filling, and role-differentiated outcomes.
"""

from __future__ import annotations

from agent import REGISTRY, ReplyKind, Session, StaffRole, capabilities
from agent.functions import BY_ID
from agent.session import recognise
from compliance.models import FieldCategory
from compliance.policy import policy_for
from compliance.roles import ARTEFACTS
from data_synthetic.catalogue import FIELD_CATALOGUE, categories_for_fields


# --- groundedness -----------------------------------------------------------

def test_every_step_artefact_exists_and_matches_its_layer():
    for spec in REGISTRY:
        for step in spec.steps:
            assert step.artefact in ARTEFACTS, f"{spec.id}: {step.artefact}"
            assert ARTEFACTS[step.artefact].layer == step.layer, (
                f"{spec.id}: {step.artefact} is a {ARTEFACTS[step.artefact].layer.value} "
                f"artefact but the step says {step.layer.value}"
            )


def test_every_step_field_exists_in_the_catalogue_for_that_layer():
    for spec in REGISTRY:
        for step in spec.steps:
            known = FIELD_CATALOGUE.get(step.layer, {})
            missing = [f for f in step.fields if f not in known]
            assert not missing, f"{spec.id}: {missing} not in {step.layer.value}"


def test_every_step_artefact_is_one_the_function_declared():
    # The gate authorises the declared artefacts; a step that touched an
    # undeclared one would slip past it.
    for spec in REGISTRY:
        for step in spec.steps:
            assert step.artefact in spec.artefacts, f"{spec.id}: {step.artefact} undeclared"


def test_no_step_touches_data_its_own_purpose_forbids():
    for spec in REGISTRY:
        allowed = policy_for(spec.purpose).allowed_categories
        for step in spec.steps:
            touched = categories_for_fields(step.layer, step.fields)
            assert touched <= allowed, f"{spec.id}: {touched - allowed} outside {spec.purpose.value}"


def test_every_step_template_only_references_declared_inputs():
    for spec in REGISTRY:
        names = {slot.name: "x" for slot in spec.inputs}
        for step in spec.steps:
            step.text.format(**names)          # KeyError if a placeholder is undeclared


def test_every_function_is_permitted_for_at_least_one_role():
    for spec in REGISTRY:
        assert any(spec.permitted_for(r) for r in StaffRole), f"{spec.id} is dead"


def test_function_ids_are_unique():
    ids = [spec.id for spec in REGISTRY]
    assert len(ids) == len(set(ids))


# --- role differentiation ---------------------------------------------------

def test_reception_and_administrator_have_no_clinical_functions():
    for role in (StaffRole.RECEPTION, StaffRole.ADMINISTRATOR):
        for spec in capabilities(role):
            for step in spec.steps:
                assert FieldCategory.CLINICAL not in categories_for_fields(step.layer, step.fields)


def test_nurse_has_no_financial_functions():
    for spec in capabilities(StaffRole.NURSE):
        for step in spec.steps:
            assert FieldCategory.FINANCIAL not in categories_for_fields(step.layer, step.fields)


def test_each_role_has_a_distinct_capability_set():
    sets = {role: {s.id for s in capabilities(role)} for role in StaffRole}
    assert sets[StaffRole.NURSE].isdisjoint(sets[StaffRole.RECEPTION])
    assert sets[StaffRole.NURSE].isdisjoint(sets[StaffRole.ADMINISTRATOR])
    assert sets[StaffRole.RECEPTION] != sets[StaffRole.ADMINISTRATOR]


# --- recognition ------------------------------------------------------------

def test_recognition_finds_the_obvious_function():
    assert [s.id for s in recognise("I need to register a new patient")] == ["register_patient"]
    assert [s.id for s in recognise("record obs for a patient")] == ["record_vitals"]


def test_recognition_returns_nothing_for_nonsense():
    assert recognise("make me a coffee") == []
    assert recognise("") == []


def test_recognition_returns_all_tied_candidates():
    ids = {s.id for s in recognise("insurance")}
    assert ids == {"verify_insurance", "reconcile_payment"}


# --- conversation -----------------------------------------------------------

def _run(role: StaffRole, lines: list[str]):
    session = Session(role)
    return [session.respond(line) for line in lines]


def test_full_conversation_yields_grounded_guidance():
    replies = _run(StaffRole.RECEPTION,
                   ["new patient", "Priya Raman", "1988-03-14", "+91-9800000012"])
    kinds = [r.kind for r in replies]
    assert kinds == [ReplyKind.ASK_INPUT, ReplyKind.ASK_INPUT, ReplyKind.ASK_INPUT, ReplyKind.GUIDANCE]
    guidance = replies[-1].guidance
    assert guidance is not None
    assert guidance.function_id == "register_patient"
    assert "Priya Raman" in guidance.steps[0].text
    assert guidance.inputs["date_of_birth"] == "1988-03-14"
    assert len(guidance.steps) == len(BY_ID["register_patient"].steps)


def test_gate_runs_before_any_input_is_requested():
    # Reception asking for a diagnosis is declined immediately -- the first
    # reply is the refusal, and no slot prompt was ever issued.
    replies = _run(StaffRole.RECEPTION, ["what is the patient's diagnosis"])
    assert len(replies) == 1
    assert replies[0].kind == ReplyKind.DECLINED
    assert replies[0].decision is not None and replies[0].decision.rule_id == "PL-01"
    assert "nurse" in replies[0].text                 # redirected to who can


def test_decline_cites_a_different_rule_for_access_control():
    replies = _run(StaffRole.RECEPTION, ["allocate a bed"])
    assert replies[0].kind == ReplyKind.DECLINED
    assert replies[0].decision.rule_id == "SS-01"


def test_ambiguous_request_asks_then_proceeds_on_a_number():
    replies = _run(StaffRole.ADMINISTRATOR, ["insurance", "2", "INV-2026-01187"])
    assert replies[0].kind == ReplyKind.ASK_CHOOSE
    assert set(replies[0].options) == {"verify_insurance", "reconcile_payment"}
    assert replies[1].kind == ReplyKind.ASK_INPUT
    assert replies[2].kind == ReplyKind.GUIDANCE
    assert replies[2].guidance.function_id == "reconcile_payment"


def test_ambiguous_request_can_also_be_resolved_by_words():
    replies = _run(StaffRole.ADMINISTRATOR, ["insurance", "the eligibility one", "MRN1", "POL-1"])
    assert replies[1].kind == ReplyKind.ASK_INPUT
    assert replies[-1].kind == ReplyKind.GUIDANCE
    assert replies[-1].guidance.function_id == "verify_insurance"


def test_choosing_a_function_the_role_may_not_use_is_still_declined():
    # Reception gets the same ambiguity, picks reconciliation, and is refused --
    # the gate runs on the chosen function, not on the vague request.
    replies = _run(StaffRole.RECEPTION, ["insurance", "2"])
    assert replies[0].kind == ReplyKind.ASK_CHOOSE
    assert replies[1].kind == ReplyKind.DECLINED
    assert replies[1].decision.rule_id == "SS-01"


def test_unrecognised_request_lists_only_what_this_role_may_do():
    reply = _run(StaffRole.NURSE, ["make me a coffee"])[0]
    assert reply.kind == ReplyKind.UNRECOGNISED
    assert "record a patient's vital signs" in reply.text
    assert "generate an invoice" not in reply.text


def test_session_resets_after_guidance_and_after_decline():
    session = Session(StaffRole.NURSE)
    for line in ["record vitals", "MRN1", "120/80", "70", "36.9"]:
        session.respond(line)
    assert session.state == "idle"
    session.respond("raise the bill")
    assert session.state == "idle"


def test_navigation_map_fills_step_pages_when_provided():
    # The seam for the Tier 2 navigation map: pass artefact -> page and the
    # steps carry it. Absent a map, pages stay unset -- nothing else changes.
    session = Session(StaffRole.NURSE, navigation={"fhir:Condition": "/chart/problems"})
    reply = session.respond("diagnosis")
    reply = session.respond("MRN2867825")
    assert reply.kind == ReplyKind.GUIDANCE
    assert all(step.page == "/chart/problems" for step in reply.guidance.steps)
    assert "/chart/problems" in reply.text


def test_guidance_renders_its_own_compliance_footer():
    replies = _run(StaffRole.ADMINISTRATOR, ["generate an invoice", "MRN2867825", "ENC-1"])
    text = replies[-1].text
    assert "purpose      : billing_settlement" in text
    assert "retain       : no longer than 365 days" in text
    md = replies[-1].guidance.render_markdown()
    assert md.startswith("**How to generate an invoice**")
