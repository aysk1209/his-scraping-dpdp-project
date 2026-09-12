"""Tests for multi-purpose policy and cross-purpose scoring.

The property under test throughout is that the modelled purposes are *not*
nested (pairwise -- see also tests/compliance/test_roles.py). A test suite that only checked "billing is stricter than care" would pass
against a broken policy that ranked purposes on one axis of permissiveness.
"""

from __future__ import annotations

from compliance.models import Purpose
from compliance.policy import PURPOSE_POLICY, policy_for
from compliance.purpose_matrix import score_across_purposes
from extraction.adapters.mock_his import MockHISDataSource
from extraction.technique import ExtractionTask, LayerFields
from extraction.techniques.compliant import CompliantExtractionTechnique
from interop.layers import HISLayer

CARE_TASK = ExtractionTask(
    task_id="care",
    purpose=Purpose.CARE_COORDINATION,
    needed=[
        LayerFields(layer=HISLayer.PATIENT_ADMINISTRATION, fields=["mrn", "admission_ward"]),
        LayerFields(layer=HISLayer.CLINICAL_EHR, fields=["primary_diagnosis", "medication"]),
    ],
)

BILLING_TASK = ExtractionTask(
    task_id="billing",
    purpose=Purpose.BILLING_SETTLEMENT,
    needed=[
        LayerFields(layer=HISLayer.PATIENT_ADMINISTRATION, fields=["mrn", "email"]),
        LayerFields(
            layer=HISLayer.ADMINISTRATIVE_FINANCIAL,
            fields=["invoice_id", "billed_amount"],
        ),
    ],
)


def _matrix(task: ExtractionTask):
    source = MockHISDataSource(records_per_layer=4, seed=42)
    output = CompliantExtractionTechnique().extract(source, task)
    return score_across_purposes(output.run, output.records), output


def _verdict_for(matrix, purpose: Purpose):
    return next(v for v in matrix.verdicts if v.purpose == purpose.value)


# --- the policy table itself ------------------------------------------------

def test_all_three_purposes_are_modelled():
    assert set(PURPOSE_POLICY) == {
        Purpose.CARE_COORDINATION, Purpose.BILLING_SETTLEMENT, Purpose.PATIENT_REGISTRATION
    }


def test_neither_purpose_scope_contains_the_other():
    care = policy_for(Purpose.CARE_COORDINATION).allowed_categories
    billing = policy_for(Purpose.BILLING_SETTLEMENT).allowed_categories
    # This is the load-bearing property: purposes are not ranked strict-to-lax.
    assert not care.issubset(billing)
    assert not billing.issubset(care)
    assert care & billing            # they do overlap -- both need to identify a patient


def test_every_purpose_declares_its_legitimate_use():
    for purpose, policy in PURPOSE_POLICY.items():
        assert policy.legitimate_use_note, f"{purpose.value} has no legitimate use note"


def test_compliant_technique_takes_its_basis_from_the_policy():
    _, output = _matrix(BILLING_TASK)
    assert output.run.lawful_basis is not None
    assert output.run.lawful_basis.reference == (
        policy_for(Purpose.BILLING_SETTLEMENT).legitimate_use_note
    )


# --- cross-purpose scoring --------------------------------------------------

def test_each_pull_is_fully_compliant_for_its_own_purpose():
    for task in (CARE_TASK, BILLING_TASK):
        matrix, _ = _matrix(task)
        assert _verdict_for(matrix, task.purpose).compliance_score == 1.0


def test_the_same_pull_scores_lower_under_the_other_purpose():
    matrix, _ = _matrix(CARE_TASK)
    own = _verdict_for(matrix, Purpose.CARE_COORDINATION).compliance_score
    other = _verdict_for(matrix, Purpose.BILLING_SETTLEMENT).compliance_score
    assert other < own


def test_out_of_scope_runs_in_both_directions_for_different_reasons():
    care_matrix, _ = _matrix(CARE_TASK)
    billing_matrix, _ = _matrix(BILLING_TASK)

    care_under_billing = _verdict_for(care_matrix, Purpose.BILLING_SETTLEMENT)
    billing_under_care = _verdict_for(billing_matrix, Purpose.CARE_COORDINATION)

    assert "clinical" in care_under_billing.out_of_scope_categories
    assert "contact" in billing_under_care.out_of_scope_categories
    # Neither direction is a subset of the other -- that is the whole point.
    assert set(care_under_billing.out_of_scope_categories) != set(
        billing_under_care.out_of_scope_categories
    )


def test_declared_purpose_is_flagged_and_listed_first():
    matrix, _ = _matrix(BILLING_TASK)
    assert matrix.verdicts[0].is_declared_purpose
    assert matrix.verdicts[0].purpose == Purpose.BILLING_SETTLEMENT.value
    assert sum(1 for v in matrix.verdicts if v.is_declared_purpose) == 1


def test_notice_is_treated_as_not_covering_an_undeclared_purpose():
    matrix, _ = _matrix(CARE_TASK)
    other = _verdict_for(matrix, Purpose.BILLING_SETTLEMENT)
    assert "NT-01" in other.failed_rules
    # ...and the declared purpose keeps its notice.
    assert "NT-01" not in _verdict_for(matrix, Purpose.CARE_COORDINATION).failed_rules


def test_retention_lawful_for_one_purpose_breaches_the_other():
    _, output = _matrix(BILLING_TASK)
    long_hold = output.run.model_copy(update={"retention_days": 365})
    matrix = score_across_purposes(long_hold, output.records)
    # 365 days sits inside billing's audit-driven ceiling and outside care's.
    assert "SL-01" not in _verdict_for(matrix, Purpose.BILLING_SETTLEMENT).failed_rules
    assert "SL-01" in _verdict_for(matrix, Purpose.CARE_COORDINATION).failed_rules
    assert "retention exceeds 90d limit" in _verdict_for(
        matrix, Purpose.CARE_COORDINATION
    ).verdict()


def test_renderers_and_artifacts(tmp_path):
    matrix, _ = _matrix(CARE_TASK)
    assert "Purpose matrix" in matrix.render_table()
    assert "lawful for this purpose" in matrix.render_table()
    md = matrix.to_markdown_file(tmp_path).read_text(encoding="utf-8")
    assert md.startswith("### Purpose matrix")
    assert "care_coordination" in md and "billing_settlement" in md
    assert '"verdicts"' in matrix.to_json_file(tmp_path).read_text(encoding="utf-8")
