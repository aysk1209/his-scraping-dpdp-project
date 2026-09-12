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
    MoralityTechnique,
    UnconstrainedExtractionTechnique,
)
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


def test_morality_model_gets_instinct_right_and_law_wrong():
    out = MoralityTechnique().extract(_source(), _task())
    report = run_all(out.run, out.records)
    by_id = {r.rule_id: r for r in report.results}
    # Nothing it pulled for care coordination is out of scope -- instinct happens
    # to agree with the purpose here -- so minimisation passes...
    assert by_id["DM-01"].status.value == "pass"
    # ...but the legal artefacts intuition never thinks of all fail.
    assert by_id["LB-01"].status.value == "fail"       # consent asserted, not recorded
    assert by_id["NT-01"].status.value == "fail"       # no notice
    assert by_id["SL-01"].status.value == "fail"       # no retention, no mechanism
    assert 0.3 <= report.compliance_score <= 0.75


def test_morality_model_refuses_what_feels_private_even_when_the_purpose_needs_it():
    from compliance.models import Purpose as P
    from extraction.techniques.morality import FEELS_PRIVATE
    task = ExtractionTask(
        task_id="reminder", purpose=P.PATIENT_REGISTRATION,
        needed=[LayerFields(layer=HISLayer.PATIENT_ADMINISTRATION,
                            fields=["mrn", "full_name", "phone", "admission_datetime"])],
    )
    out = MoralityTechnique().extract(_source(), task)
    pulled = {k for row in out.rows[HISLayer.PATIENT_ADMINISTRATION.value] for k in row}
    assert "full_name" in FEELS_PRIVATE and "phone" in FEELS_PRIVATE
    assert pulled == {"mrn", "admission_datetime"}     # the lawful, needed fields were refused
    # ...while the compliance-aware technique pulls exactly what the purpose needs.
    lawful = CompliantExtractionTechnique().extract(_source(), task)
    assert {k for row in lawful.rows[HISLayer.PATIENT_ADMINISTRATION.value] for k in row} == {
        "mrn", "full_name", "phone", "admission_datetime"}


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
