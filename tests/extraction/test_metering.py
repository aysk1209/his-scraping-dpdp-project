"""Tests for extraction cost metering (the benchmark's second axis)."""

from __future__ import annotations

from compliance.models import Purpose
from extraction.adapters.mock_his import MockHISDataSource
from extraction.metering import ExtractionCost, MeteredSource, combine
from extraction.technique import ExtractionTask, LayerFields
from extraction.techniques.compliant import CompliantExtractionTechnique
from extraction.techniques.unconstrained import UnconstrainedExtractionTechnique
from interop.layers import HISLayer

TASK = ExtractionTask(
    task_id="t",
    purpose=Purpose.CARE_COORDINATION,
    needed=[
        LayerFields(layer=HISLayer.PATIENT_ADMINISTRATION, fields=["mrn", "sex"]),
        LayerFields(layer=HISLayer.CLINICAL_EHR, fields=["primary_diagnosis"]),
    ],
)


def _source() -> MockHISDataSource:
    return MockHISDataSource(records_per_layer=4, seed=7)


def test_field_refs_are_layer_qualified():
    assert TASK.field_refs() == {
        ("patient_administration", "mrn"),
        ("patient_administration", "sex"),
        ("clinical_ehr", "primary_diagnosis"),
    }


def test_metered_source_passes_records_through_unchanged():
    plain = list(_source().fetch(HISLayer.PATIENT_ADMINISTRATION, fields=["mrn"]))
    metered = list(MeteredSource(_source()).fetch(HISLayer.PATIENT_ADMINISTRATION, fields=["mrn"]))
    assert plain == metered


def test_fetch_is_counted_even_when_nothing_is_consumed():
    meter = MeteredSource(_source())
    meter.fetch(HISLayer.PATIENT_ADMINISTRATION, fields=["mrn"])  # never iterated
    assert meter.fetches == 1
    assert meter.records == 0


def test_compliant_technique_pulls_exactly_what_the_task_needs():
    meter = MeteredSource(_source())
    CompliantExtractionTechnique().extract(meter, TASK)
    cost = meter.cost(TASK.field_refs(), elapsed_ms=1.0)
    assert cost.excess_ratio == 1.0
    assert cost.coverage == 1.0
    assert cost.fetches == 2          # one per needed layer
    assert cost.records == 8          # 4 records x 2 layers


def test_baseline_overreach_shows_up_as_excess_without_losing_coverage():
    meter = MeteredSource(_source())
    UnconstrainedExtractionTechnique().extract(meter, TASK)
    cost = meter.cost(TASK.field_refs(), elapsed_ms=1.0)
    # It still obtains everything the task needs -- the failure is surplus, and
    # the metric has to show that rather than looking like under-delivery.
    assert cost.coverage == 1.0
    assert cost.excess_ratio > 1.0
    assert cost.fetches > 2


def test_coverage_falls_when_a_needed_field_is_never_pulled():
    meter = MeteredSource(_source())
    list(meter.fetch(HISLayer.PATIENT_ADMINISTRATION, fields=["mrn"]))
    cost = meter.cost(TASK.field_refs(), elapsed_ms=0.0)
    assert cost.coverage is not None and cost.coverage < 1.0
    assert cost.matched_fields == 1 and cost.needed_fields == 3


def test_ratios_are_none_when_the_task_declares_nothing():
    cost = MeteredSource(_source()).cost(set(), elapsed_ms=0.0)
    assert cost.coverage is None and cost.excess_ratio is None


def test_combine_micro_averages_rather_than_averaging_ratios():
    # Two tasks of unequal size: a per-task mean of the ratios would give 1.5,
    # but the workload actually pulled 5 distinct fields against 3 needed.
    costs = [
        ExtractionCost.build(
            fetches=1, records=1, fields_pulled=1,
            pulled={("l", "a"), ("l", "b")}, needed={("l", "a")}, elapsed_ms=1.0,
        ),
        ExtractionCost.build(
            fetches=1, records=1, fields_pulled=1,
            pulled={("l", "a"), ("l", "b"), ("l", "c")},
            needed={("l", "a"), ("l", "b")}, elapsed_ms=1.0,
        ),
    ]
    merged = combine(costs)
    assert merged.excess_ratio == round(5 / 3, 3)
    assert merged.coverage == 1.0
    assert merged.elapsed_ms == 2.0


def test_combine_of_nothing_is_empty_not_an_error():
    assert combine([]).fetches == 0
