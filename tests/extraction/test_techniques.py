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
    MinimisingUndocumentedTechnique,
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


def test_minimising_technique_passes_dm01_but_not_the_rest():
    out = MinimisingUndocumentedTechnique().extract(_source(), _task())
    report = run_all(out.run, out.records)
    by_id = {r.rule_id: r for r in report.results}
    assert by_id["DM-01"].status.value == "pass"
    assert by_id["LB-01"].status.value == "fail"
    assert 0.5 <= report.compliance_score <= 0.75


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
