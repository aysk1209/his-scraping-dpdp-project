"""Tests for the extraction technique abstraction and the three techniques."""

from __future__ import annotations

from compliance.checkers import run_all
from compliance.models import FieldCategory, Purpose
from data_synthetic.catalogue import fields_for
from extraction.adapters.mock_his import MockHISDataSource
from extraction.technique import ExtractionTask, LayerFields, TechniqueOutput
from extraction.techniques import (
    DEFAULT_TECHNIQUES,
    CompliantExtractionTechnique,
    UnconstrainedExtractionTechnique,
)
from extraction.techniques.ai_agent import AIAgentTechnique, AgentDecision, build_user_prompt
from extraction.techniques.ai_providers import FakeProvider, ProviderUnavailable
from interop.layers import HISLayer


def _task() -> ExtractionTask:
    return ExtractionTask(
        task_id="t",
        purpose=Purpose.CARE_COORDINATION,
        needed=[
            LayerFields(layer=HISLayer.PATIENT_ADMINISTRATION, fields=["mrn", "sex"]),
            LayerFields(layer=HISLayer.CLINICAL_EHR, fields=["primary_diagnosis"]),
        ],
    )


def _source() -> MockHISDataSource:
    return MockHISDataSource(records_per_layer=4, seed=42)


def test_every_default_technique_returns_output_with_records():
    task, source = _task(), _source()
    for technique in DEFAULT_TECHNIQUES:
        out = technique.extract(source, task)
        assert isinstance(out, TechniqueOutput)
        assert out.records
        assert out.run.purpose == Purpose.CARE_COORDINATION


def test_compliant_technique_pulls_only_needed_layers():
    out = CompliantExtractionTechnique().extract(_source(), _task())
    layers = {r.source_layer for r in out.records}
    assert layers == {"patient_administration", "clinical_ehr"}
    assert run_all(out.run, out.records).compliance_score == 1.0


def test_unconstrained_technique_pulls_every_layer_and_leaks_categories():
    out = UnconstrainedExtractionTechnique().extract(_source(), _task())
    layers = {r.source_layer for r in out.records}
    assert "administrative_financial" in layers  # not asked for
    all_categories = set().union(*(r.field_categories for r in out.records))
    assert FieldCategory.FINANCIAL in all_categories
    assert FieldCategory.CONTACT in all_categories
    assert run_all(out.run, out.records).compliance_score < 0.4


_DECISION = {
    "fields": ["patient_administration/mrn", "patient_administration/sex",
               "clinical_ehr/primary_diagnosis", "clinical_ehr/no_such_field", "bogus"],
    "purpose_specified": True, "secondary_uses": [],
    "lawful_basis_type": "consent", "lawful_basis_reference": "",
    "retention_days": 0, "deletion_mechanism": "",
    "transport_encrypted": True, "at_rest_encrypted": True,
    "access_controlled": False, "identifiers_pseudonymised": False,
    "notice_reference": "", "notice_covers_purpose": False, "notice_machine_readable": False,
    "audit_log_enabled": True, "accountable_party": "", "processing_record_kept": False,
    "rationale": "a summary needs identity and diagnosis",
}


def test_ai_agent_never_sees_a_value_and_is_not_shown_the_needed_list(tmp_path):
    provider = FakeProvider([_DECISION])
    tech = AIAgentTechnique(provider, mode="live", recordings_dir=tmp_path)
    source = _source()
    task = _task()
    tech.extract(source, task)
    system, user = provider.calls[0]
    # Field names go to the model; values never do.
    assert "patient_administration/mrn" in user
    for row in source.fetch(HISLayer.PATIENT_ADMINISTRATION):
        assert str(row["full_name"]) not in user and str(row["mrn"]) not in user
        break
    # The task's minimum-necessary list is the policy's output; the agent is
    # briefed with the job in words, not the answer.
    assert "needed" not in user.lower()
    assert task.task_id in user or task.description in user


def test_ai_agent_decision_drops_unknown_fields_and_maps_the_manifest():
    d = AgentDecision.model_validate(_DECISION)
    sel = d.selection()
    assert sel == {HISLayer.PATIENT_ADMINISTRATION: ["mrn", "sex"],
                   HISLayer.CLINICAL_EHR: ["primary_diagnosis"]}
    assert d.unknown_fields() == ["clinical_ehr/no_such_field", "bogus"]
    run = d.manifest("r", Purpose.CARE_COORDINATION)
    assert run.lawful_basis is not None and run.lawful_basis.reference is None   # asserted, not referenced
    assert run.retention_days is None and run.deletion_mechanism is None
    assert run.notice is None
    assert run.security.transport_encrypted and not run.security.identifiers_pseudonymised
    assert run.governance.audit_log_enabled and run.governance.accountable_party is None


def test_ai_agent_output_is_scored_by_the_same_rules(tmp_path):
    tech = AIAgentTechnique(FakeProvider([_DECISION]), mode="live", recordings_dir=tmp_path)
    out = tech.extract(_source(), _task())
    report = run_all(out.run, out.records)
    by_id = {r.rule_id: r for r in report.results}
    assert by_id["DM-01"].status.value == "pass"       # pulled within scope
    assert by_id["LB-01"].score == 0.5                 # consent asserted, no reference
    assert by_id["NT-01"].status.value == "fail"       # no notice
    assert by_id["SL-01"].status.value == "fail"
    assert 0.2 < report.compliance_score < 1.0
    assert out.run.run_id == "t--fake-unaided"


def test_ai_agent_records_live_decisions_and_replays_them_without_a_provider(tmp_path):
    live = AIAgentTechnique(FakeProvider([_DECISION]), mode="live", recordings_dir=tmp_path)
    live.extract(_source(), _task())
    assert live.last_source == "live"
    assert (tmp_path / "fake-unaided.json").exists()
    assert live.has_recording("t")

    # Replay by provider *name*: no provider object, no key, no network.
    replay = AIAgentTechnique("fake", mode="replay", recordings_dir=tmp_path)
    out = replay.extract(_source(), _task())
    assert replay.last_source == "replay"
    assert {k for row in out.rows["patient_administration"] for k in row} == {"mrn", "sex"}

    # And a task with no recording is refused rather than silently improvised.
    other = ExtractionTask(task_id="unrecorded", purpose=Purpose.CARE_COORDINATION)
    try:
        replay.extract(_source(), other)
        assert False, "expected ProviderUnavailable"
    except ProviderUnavailable:
        pass


def test_ai_agent_recording_holds_no_personal_data(tmp_path):
    import json
    live = AIAgentTechnique(FakeProvider([_DECISION]), mode="live", recordings_dir=tmp_path)
    source = _source()
    live.extract(source, _task())
    text = (tmp_path / "fake-unaided.json").read_text(encoding="utf-8")
    data = json.loads(text)
    assert set(data["tasks"]["t"]["samples"][0]) == set(_DECISION)
    for row in source.fetch(HISLayer.PATIENT_ADMINISTRATION):
        assert row["full_name"] not in text and row["mrn"] not in text
        break


def test_informed_briefing_carries_the_obligations_and_unaided_does_not():
    from extraction.techniques.ai_agent import SYSTEM_INFORMED, SYSTEM_UNAIDED
    assert "Digital Personal Data Protection Act" in SYSTEM_INFORMED
    assert "Digital Personal Data Protection Act" not in SYSTEM_UNAIDED
    assert "data minimisation" in SYSTEM_INFORMED.lower()


def test_unconstrained_ignores_task_needed_list():
    source = _source()
    small_task = ExtractionTask(
        task_id="tiny",
        purpose=Purpose.CARE_COORDINATION,
        needed=[LayerFields(layer=HISLayer.CLINICAL_EHR, fields=["allergy"])],
    )
    out = UnconstrainedExtractionTechnique().extract(source, small_task)
    # still pulled all catalogue fields for clinical_ehr, plus other layers
    clinical_records = [r for r in out.records if r.source_layer == "clinical_ehr"]
    assert len(clinical_records) == 4  # records_per_layer, not filtered
    assert len(fields_for(HISLayer.CLINICAL_EHR)) > 1
