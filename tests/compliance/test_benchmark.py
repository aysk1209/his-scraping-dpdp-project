"""Tests for the compliance benchmarking harness."""

from __future__ import annotations

from compliance.benchmark import BenchmarkResult, run_benchmark
from compliance.models import Purpose
from extraction.adapters.mock_his import MockHISDataSource
from extraction.technique import ExtractionTask, LayerFields
from extraction.techniques import DEFAULT_TECHNIQUES
from interop.layers import HISLayer

TASKS = [
    ExtractionTask(
        task_id="patient-summary",
        purpose=Purpose.CARE_COORDINATION,
        needed=[
            LayerFields(layer=HISLayer.PATIENT_ADMINISTRATION, fields=["mrn", "sex"]),
            LayerFields(layer=HISLayer.CLINICAL_EHR, fields=["primary_diagnosis", "medication"]),
        ],
    ),
    ExtractionTask(
        task_id="ward-census",
        purpose=Purpose.CARE_COORDINATION,
        needed=[
            LayerFields(
                layer=HISLayer.PATIENT_ADMINISTRATION,
                fields=["mrn", "admission_ward"],
            ),
        ],
    ),
]


def _result() -> BenchmarkResult:
    source = MockHISDataSource(records_per_layer=5, seed=42)
    return run_benchmark(DEFAULT_TECHNIQUES, TASKS, source)


def test_result_is_ranked_best_first():
    scores = _result().scores
    values = [s.mean_compliance_score for s in scores]
    assert values == sorted(values, reverse=True)


def test_compliance_aware_wins_and_baseline_loses():
    scores = {s.technique: s for s in _result().scores}
    assert scores["compliance-aware (ours)"].mean_compliance_score == 1.0
    assert scores["unconstrained (baseline)"].mean_compliance_score < 0.4
    mid = scores["minimising, undocumented"].mean_compliance_score
    assert 0.4 < mid < 1.0


def test_per_rule_mean_covers_every_rule():
    for score in _result().scores:
        assert set(score.per_rule_mean) == {
            "DM-01", "LB-01", "SL-01", "SS-01", "PL-01", "NT-01", "AC-01"
        }


def test_per_task_has_an_entry_per_task():
    for score in _result().scores:
        assert set(score.per_task) == {"patient-summary", "ward-census"}


def test_markdown_and_json_artifacts_write(tmp_path):
    result = _result()
    md = result.to_markdown_file(tmp_path)
    js = result.to_json_file(tmp_path)
    assert md.read_text(encoding="utf-8").startswith("### Compliance benchmark")
    assert "compliance-aware (ours)" in md.read_text(encoding="utf-8")
    assert '"scores"' in js.read_text(encoding="utf-8")


def test_json_is_valid_json_no_nan(tmp_path):
    import json

    result = _result()
    data = json.loads(result.to_json_file(tmp_path).read_text(encoding="utf-8"))
    assert len(data["scores"]) == 3
