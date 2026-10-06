"""Each design choice of our technique, switched off alone, moves the rule it serves."""

from __future__ import annotations

import pytest

from compliance.benchmark import bind_subject, run_benchmark
from extraction.adapters.mock_his import MockHISDataSource
from extraction.techniques.compliant import ABLATIONS, CompliantExtractionTechnique
from scripts.run_benchmark import TASKS


@pytest.fixture(scope="module")
def scores(tmp_path_factory):
    from compliance.audit import AuditLog
    source = MockHISDataSource(records_per_layer=8, seed=3)
    techniques = [CompliantExtractionTechnique()] + [CompliantExtractionTechnique(without=a) for a in ABLATIONS]
    result = run_benchmark(techniques, bind_subject(TASKS, source), source,
                           audit=AuditLog(tmp_path_factory.mktemp("abl") / "a.jsonl"))
    return {s.technique: s for s in result.scores}


def _rules_below_one(s):
    return {k for k, v in s.per_rule_mean.items() if v is not None and v < 1.0}


def test_ours_is_untouched_by_the_flags(scores):
    assert scores["compliance-aware (ours)"].mean_compliance_score == 1.0


@pytest.mark.parametrize("without,rules", [
    ("scope", {"DM-01"}), ("field_list", {"DM-01"}), ("retention", {"SL-01"}),
    ("pseudonymise", {"SS-01"}), ("manifest", {"LB-01", "NT-01", "AC-01"}),
])
def test_switching_one_choice_off_moves_its_own_rules_only(scores, without, rules):
    s = scores[f"ours without {without.replace('_', ' ')}"]
    assert _rules_below_one(s) == rules


def test_without_scope_the_record_axis_carries_the_cost(scores):
    s = scores["ours without scope"]
    assert s.cost.record_excess > 1 and s.cost.excess_ratio == 1.0


def test_an_unknown_choice_is_refused():
    with pytest.raises(ValueError):
        CompliantExtractionTechnique(without="vibes")
