"""The task library, the conversation around it, and surviving a HIS update.

Three families.

*The library*: every role has its common tasks, each grounded in the vocabulary
(buttons, labels, slot shapes), and the privacy requests sit with the desk roles.

*The conversation*: details picked out of the first message only after the gate,
shapes checked, ``cancel`` drops everything, ``help`` is grouped, a tie resolves
to the one function the role may use.

*Updates*: the fixture portal's two layouts are turned into the map the crawler
would build (``crawled``) -- one test checks that against a real crawl -- and the
same registry is placed on both. Every task re-words itself; the two changes no
one predicted are withheld with a proposal each; confirming them restores
everything; the gate never moves.
"""

from __future__ import annotations

import re
import string

import pytest

from agent import ACTIONS, REGISTRY, ReplyKind, ScreenMap, Session, StaffRole, capabilities, compare
from agent.functions import BY_ID, GROUPS
from agent.guidance import build_guidance
from agent.session import HELP_WORDS, fits, found_in
from agent.ui import match_control, normalise
from data_synthetic.catalogue import FIELD_CATALOGUE
from extraction.tier2.navigation import ModuleMap, NavigationMap
from tools.mock_portal.layouts import V1, V2, V2_FIELD_ALIASES, PortalLayout

_RESERVED = {"module", "button", "label"}


def crawled(layout: PortalLayout, field_aliases: dict[str, str] | None = None) -> NavigationMap:
    """The map the crawler builds from ``layout``, without starting a browser."""

    aliases = field_aliases or {}
    modules = []
    for m in layout.modules:
        def seen(name: str) -> tuple[str, str]:
            shown = layout.labels.get(name, name)
            return shown, aliases.get(shown, shown)

        record = [f for f in FIELD_CATALOGUE[m.layer] if m.record_fields is None or f in m.record_fields]
        columns = [seen(f) for f in m.list_columns]
        detail = [seen(f) for f in record]
        labels = {n: s for s, n in [*columns, *detail] if s != n}
        from data_synthetic.catalogue import infer_layer
        names = list(dict.fromkeys([n for _, n in columns] + [n for _, n in detail]))
        layer, confidence = infer_layer(names)
        modules.append(ModuleMap(
            title=m.title, list_url=f"https://his{layout.prefix}{m.slug}/",
            list_path=f"{layout.prefix}{m.slug}/",
            columns=[n for _, n in columns], detail_fields=[n for _, n in detail],
            inferred_layer=layer, layer_confidence=confidence, labels=labels,
            list_controls=list(m.list_actions), record_controls=list(m.record_actions),
        ))
    return NavigationMap(base_url="https://his", modules=modules)


BEFORE = ScreenMap.from_navigation(crawled(V1))
AFTER = ScreenMap.from_navigation(crawled(V2, V2_FIELD_ALIASES))


def _placeholders(text: str) -> set[str]:
    return {f for _, f, _, _ in string.Formatter().parse(text) if f}


def _guide(spec_id: str, screens: ScreenMap):
    spec = BY_ID[spec_id]
    role = next(r for r in StaffRole if spec.permitted_for(r))
    return build_guidance(role, spec, {s.name: s.example for s in spec.inputs}, screens)


# --- the library -------------------------------------------------------------

def test_every_role_has_its_common_tasks():
    counts = {role: len(capabilities(role)) for role in StaffRole}
    assert counts[StaffRole.RECEPTION] >= 10
    assert counts[StaffRole.NURSE] >= 10
    assert counts[StaffRole.ADMINISTRATOR] >= 14
    assert len(REGISTRY) >= 29


def test_every_group_is_reachable_and_every_function_has_one():
    assert set(GROUPS) == {spec.group for spec in REGISTRY}
    for role in StaffRole:
        assert Session(role).menu()                         # nobody gets an empty menu


def test_privacy_requests_belong_to_the_desk_roles_and_never_to_the_ward():
    privacy = [spec for spec in REGISTRY if spec.group == "Privacy requests"]
    assert {s.id for s in privacy} == {"access_request", "erasure_request", "withdraw_consent",
                                       "privacy_grievance"}
    for spec in privacy:
        assert spec.permitted_for(StaffRole.RECEPTION) and spec.permitted_for(StaffRole.ADMINISTRATOR)
        assert not spec.permitted_for(StaffRole.NURSE)
        assert "fhir:Task" in spec.artefacts                # logged and routed, never decided at the desk


def test_every_button_is_an_operation_in_the_vocabulary_and_every_operation_is_used():
    used = {step.action for spec in REGISTRY for step in spec.steps if step.action}
    assert used <= set(ACTIONS)
    assert used == set(ACTIONS)


def test_screen_placeholders_are_declared_where_used():
    for spec in REGISTRY:
        assert not {s.name for s in spec.inputs} & _RESERVED, spec.id
        for step in spec.steps:
            fields = _placeholders(step.text)
            assert ("button" in fields) == (step.action is not None), f"{spec.id}: {step.text}"
            labels = {f.split(".", 1)[1] for f in fields if f.startswith("label.")}
            assert labels <= set(step.fields), f"{spec.id}: {labels - set(step.fields)} undeclared"
            if step.offscreen:
                assert not fields & {"module", "button"} and not labels, f"{spec.id}: off-screen step names a screen"


def test_every_slot_example_has_the_shape_it_asks_for_and_is_found_in_a_sentence():
    for spec in REGISTRY:
        for slot in spec.inputs:
            assert fits(slot, slot.example), f"{spec.id}.{slot.name}: {slot.example}"
            if slot.find:
                assert found_in(slot, f"please do it for {slot.example} today") == slot.example


def test_the_fixture_buttons_are_all_understood_except_the_one_the_update_slips_in():
    for module in V1.modules:
        for label in (*module.list_actions, *module.record_actions):
            assert match_control(label), label
    unknown = {label for m in V2.modules for label in (*m.list_actions, *m.record_actions)
               if match_control(label) is None}
    assert unknown == {"Close episode"}


def test_button_matching_is_whole_names_only():
    assert match_control("Check-in") == "mark_arrived"
    assert match_control("  DISCHARGE ") == "discharge"
    assert match_control("Ready for discharge") == "ready_for_discharge"
    assert match_control("Discharge summary") is None
    assert match_control("Close episode", {"close  EPISODE": "discharge"}) == "discharge"


# --- the conversation ---------------------------------------------------------

def test_details_in_the_first_message_are_used_after_the_gate():
    session = Session(StaffRole.RECEPTION)
    reply = session.respond("check in MRN2867825")
    assert reply.kind == ReplyKind.GUIDANCE                 # the only detail it needed was given
    assert "MRN2867825" in reply.guidance.steps[0].text


def test_details_in_a_declined_request_are_never_kept():
    session = Session(StaffRole.RECEPTION)
    reply = session.respond("what is the diagnosis for MRN2867825")
    assert reply.kind == ReplyKind.DECLINED
    assert "MRN2867825" not in reply.text
    assert session.inputs == {}


def test_partly_given_details_are_acknowledged_and_the_rest_asked():
    reply = Session(StaffRole.ADMINISTRATOR).respond("raise the bill for ENC-20260912-07")
    assert reply.kind == ReplyKind.ASK_INPUT
    assert "From your message: encounter_id ENC-20260912-07" in reply.text
    assert "MRN" in reply.text.split("\n")[-1]


def test_a_badly_shaped_answer_is_asked_again():
    session = Session(StaffRole.NURSE)
    session.respond("record vitals for MRN2867825")
    reply = session.respond("one twenty over eighty")
    assert reply.kind == ReplyKind.ASK_INPUT
    assert reply.text.startswith("That doesn't look like what I need here.")
    assert session.respond("120/80").kind == ReplyKind.ASK_INPUT       # on to the pulse


def test_cancel_drops_the_request_and_what_was_typed():
    session = Session(StaffRole.RECEPTION)
    session.respond("register a new patient")
    session.respond("Priya Raman")
    reply = session.respond("never mind")
    assert reply.kind == ReplyKind.CANCELLED
    assert session.state == "idle" and session.inputs == {}
    assert Session(StaffRole.RECEPTION).respond("cancel").kind == ReplyKind.CANCELLED


def test_help_lists_this_roles_tasks_in_groups():
    for words in HELP_WORDS:
        reply = Session(StaffRole.NURSE).respond(words)
        assert reply.kind == ReplyKind.HELP
    text = Session(StaffRole.NURSE).respond("help").text
    assert "  Ward care:" in text and "  - record an allergy" in text
    assert "Billing" not in text and "Privacy requests" not in text


def test_help_mid_request_repeats_the_question():
    session = Session(StaffRole.NURSE)
    session.respond("record vitals")
    reply = session.respond("help")
    assert reply.kind == ReplyKind.ASK_INPUT
    assert reply.text.endswith("(e.g. MRN2867825)")
    assert session.state == "collecting"


@pytest.mark.parametrize("role,expected", [
    (StaffRole.NURSE, "discharge_checklist"),
    (StaffRole.ADMINISTRATOR, "release_bed"),
])
def test_the_same_word_means_each_roles_own_task(role, expected):
    reply = Session(role).respond("discharge MRN2867825")
    if reply.kind == ReplyKind.GUIDANCE:
        assert reply.guidance.function_id == expected
    else:
        assert reply.kind == ReplyKind.ASK_INPUT and BY_ID[expected].label in reply.text


# --- surviving an update ------------------------------------------------------

def test_without_a_map_steps_use_the_models_own_words():
    guidance = _guide("verify_insurance", ScreenMap())
    assert guidance.steps[0].text == 'Open Billing and press "Check eligibility".'
    assert all(step.where is None and step.page is None for step in guidance.steps)


def test_every_task_places_on_the_portal_as_benchmarked():
    for spec in REGISTRY:
        guidance = _guide(spec.id, BEFORE)
        assert not guidance.withheld(), spec.id


def test_a_split_module_is_followed_by_content():
    before, after = _guide("verify_insurance", BEFORE), _guide("verify_insurance", AFTER)
    assert before.steps[0].text == 'Open Billing & Accounts and press "Check eligibility".'
    assert after.steps[0].text == 'Open Insurance & Payers and press "Verify coverage".'
    assert after.steps[1].page == "/app/payers/"


def test_a_relabelled_header_is_used_in_the_words():
    assert "Enter the UHID MRN2867825" in _guide("verify_insurance", AFTER).steps[1].text


def test_a_field_moved_onto_the_record_page_is_found_there():
    assert _guide("view_diagnosis", BEFORE).steps[1].where.endswith("list page")
    assert _guide("view_diagnosis", AFTER).steps[1].where == "Patient Chart, /app/chart/, record page"


def test_a_field_in_the_other_half_of_a_split_is_pointed_to():
    step = _guide("generate_invoice", AFTER).steps[2]
    assert step.text.startswith('Press "Create bill".')
    assert "Payer is on Insurance & Payers, list page" in step.text


def test_what_nobody_predicted_is_withheld_with_a_proposal():
    changes = compare(BEFORE, AFTER)
    withheld = {t.function_id for t in changes.impact if t.status == "withheld"}
    assert withheld == {"allocate_bed", "transfer_patient", "release_bed", "ward_census"}
    assert changes.field_proposals == {"Unit": "admission_ward"}
    assert changes.control_proposals == {"Close episode": "discharge"}
    release = _guide("release_bed", AFTER)
    assert release.steps[1].text.startswith("(withheld) I can't place this step")
    assert 'no button for "Discharge"' in release.steps[1].withheld
    assert release.steps[1].caution is None                 # no advice on a step it cannot place
    assert not release.steps[0].withheld                    # the rest is still given


def test_every_other_task_rewords_itself():
    statuses = {t.function_id: t.status for t in compare(BEFORE, AFTER).impact}
    assert set(statuses.values()) == {"re-worded", "withheld"}
    assert sum(s == "re-worded" for s in statuses.values()) == len(REGISTRY) - 4


def test_confirming_the_proposals_restores_every_task():
    changes = compare(BEFORE, AFTER)
    fixed = ScreenMap.from_navigation(
        crawled(V2, {**V2_FIELD_ALIASES, **changes.field_proposals}), changes.control_proposals)
    after = compare(BEFORE, fixed)
    assert not after.by_status()["withheld"]
    assert _guide("release_bed", fixed).steps[1].text.startswith('Press "Close episode".')


def test_an_update_changes_the_words_and_never_the_gate():
    for nav in (BEFORE, AFTER):
        nurse = Session(StaffRole.NURSE, navigation=nav).respond("raise the bill")
        assert nurse.kind == ReplyKind.DECLINED and nurse.decision.rule_id == "PL-01"
        desk = Session(StaffRole.RECEPTION, navigation=nav).respond("allocate a bed")
        assert desk.kind == ReplyKind.DECLINED and desk.decision.rule_id == "SS-01"


def test_what_changed_is_told_per_role():
    changes = compare(BEFORE, AFTER)
    nurse = Session(StaffRole.NURSE, navigation=AFTER, changes=changes).respond("what changed")
    admin = Session(StaffRole.ADMINISTRATOR, navigation=AFTER, changes=changes).respond("what's new?")
    assert nurse.kind == admin.kind == ReplyKind.CHANGES
    assert '"Ready for discharge" is now "Mark fit for discharge"' in nurse.text
    assert "Create bill" not in nurse.text and "Close episode" not in nurse.text
    assert '"Generate invoice" is now "Create bill"' in admin.text
    assert "4 with a step withheld" in admin.text
    assert "no record of a change" in Session(StaffRole.NURSE).respond("what changed").text


def test_the_report_names_modules_by_content_not_by_title():
    text = compare(BEFORE, AFTER).render()
    assert "Patient Registration is now Front Office (/m/registration/ -> /app/front-office/)." in text
    assert "Billing & Accounts is now split: Accounts (/app/accounts/) and Insurance & Payers (/app/payers/)." in text
    assert re.search(r"Primary diagnosis is now on the record page of Patient Chart", text)
    assert "nothing here is adopted by itself" in text


def test_compare_needs_two_crawls():
    with pytest.raises(ValueError):
        compare(ScreenMap(), AFTER)


# --- against the real crawler -------------------------------------------------

@pytest.mark.usefixtures("browser_available")
@pytest.mark.parametrize("layout,aliases", [(V1, {}), (V2, V2_FIELD_ALIASES)])
def test_the_crawler_sees_what_the_unit_tests_assume(layout, aliases):
    from extraction.adapters.mock_his import MockHISDataSource
    from extraction.tier2.browser import PortalBrowser
    from extraction.tier2.navigation import discover
    from tools.mock_portal.serve import BackgroundPortal

    with BackgroundPortal(MockHISDataSource(records_per_layer=4, seed=5), page_size=2,
                          layout=layout.name) as portal:
        with PortalBrowser(portal.url, portal.username, portal.password, field_aliases=aliases) as browser:
            browser.login()
            real = discover(browser)
    assumed = crawled(layout, aliases)
    keys = ("title", "list_path", "columns", "detail_fields", "inferred_layer", "labels",
            "list_controls", "record_controls")
    assert [m.model_dump(include=set(keys)) for m in real.modules] == \
           [m.model_dump(include=set(keys)) for m in assumed.modules]
    assert normalise("Search") not in {normalise(c) for m in real.modules for c in m.list_controls}
