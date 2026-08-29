"""Tests for the DPDP compliance rule slice (DM-01, LB-01, SL-01, SS-01)."""

from __future__ import annotations

import pytest

from compliance.checkers import run_all
from compliance.models import (
    ExtractedRecord,
    ExtractionRun,
    FieldCategory,
    Governance,
    LawfulBasis,
    LawfulBasisType,
    Notice,
    Purpose,
    SecurityPosture,
)
from compliance.rules import ALL_RULES
from compliance.rules.base import RuleStatus


def _fully_compliant() -> tuple[ExtractionRun, list[ExtractedRecord]]:
    run = ExtractionRun(
        run_id="test-compliant",
        purpose=Purpose.CARE_COORDINATION,
        lawful_basis=LawfulBasis(
            type=LawfulBasisType.LEGITIMATE_USE, reference="legitimate use - medical services"
        ),
        retention_days=30,
        deletion_mechanism="daily purge",
        security=SecurityPosture(
            transport_encrypted=True,
            at_rest_encrypted=True,
            access_controlled=True,
            identifiers_pseudonymised=True,
        ),
        notice=Notice(reference="privacy notice v3", covers_purpose=True),
        governance=Governance(
            audit_log_enabled=True,
            accountable_party="Data Protection Officer",
            processing_record_kept=True,
        ),
    )
    records = [
        ExtractedRecord(
            source_layer="patient_administration",
            field_categories={FieldCategory.DIRECT_IDENTIFIER, FieldCategory.QUASI_IDENTIFIER},
        ),
        ExtractedRecord(
            source_layer="clinical_ehr",
            field_categories={FieldCategory.CLINICAL, FieldCategory.ADMINISTRATIVE},
        ),
    ]
    return run, records


def _result(report, rule_id: str):
    return next(r for r in report.results if r.rule_id == rule_id)


def test_rule_set_has_exactly_the_seven_expected_rules():
    assert {rule.rule_id for rule in ALL_RULES} == {
        "DM-01", "LB-01", "SL-01", "SS-01", "PL-01", "NT-01", "AC-01"
    }


def test_fully_compliant_run_scores_top_marks():
    run, records = _fully_compliant()
    report = run_all(run, records)
    assert report.compliance_score == 1.0
    assert report.pass_rate == 1.0
    assert all(r.status == RuleStatus.PASS for r in report.results)


def test_out_of_scope_category_fails_dm01():
    run, records = _fully_compliant()
    records.append(
        ExtractedRecord(
            source_layer="administrative_financial",
            field_categories={FieldCategory.FINANCIAL},
        )
    )
    report = run_all(run, records)
    dm01 = _result(report, "DM-01")
    assert dm01.status == RuleStatus.FAIL
    assert dm01.score < 1.0
    assert any("financial" in f for f in dm01.findings)


def test_missing_lawful_basis_fails_lb01():
    run, records = _fully_compliant()
    run.lawful_basis = None
    report = run_all(run, records)
    assert _result(report, "LB-01").status == RuleStatus.FAIL
    assert _result(report, "LB-01").score == 0.0


def test_lawful_basis_without_reference_is_partial_fail():
    run, records = _fully_compliant()
    run.lawful_basis = LawfulBasis(type=LawfulBasisType.CONSENT, reference=None)
    lb01 = _result(run_all(run, records), "LB-01")
    assert lb01.status == RuleStatus.FAIL
    assert lb01.score == pytest.approx(0.5)


def test_retention_over_policy_limit_fails_sl01():
    run, records = _fully_compliant()
    run.retention_days = 365  # policy max for care_coordination is 90
    sl01 = _result(run_all(run, records), "SL-01")
    assert sl01.status == RuleStatus.FAIL
    assert any("exceeds the policy maximum" in f for f in sl01.findings)


def test_missing_retention_and_deletion_zeroes_sl01():
    run, records = _fully_compliant()
    run.retention_days = None
    run.deletion_mechanism = None
    sl01 = _result(run_all(run, records), "SL-01")
    assert sl01.status == RuleStatus.FAIL
    assert sl01.score == 0.0


def test_weak_security_posture_fails_ss01_proportionally():
    run, records = _fully_compliant()
    run.security = SecurityPosture(transport_encrypted=True)  # 1 of 4 (pseudonymisation applies)
    ss01 = _result(run_all(run, records), "SS-01")
    assert ss01.status == RuleStatus.FAIL
    assert ss01.score == pytest.approx(0.25)


def test_pseudonymisation_not_required_when_no_direct_identifiers():
    run, records = _fully_compliant()
    records = [
        ExtractedRecord(source_layer="clinical_ehr", field_categories={FieldCategory.CLINICAL})
    ]
    run.security = SecurityPosture(
        transport_encrypted=True, at_rest_encrypted=True, access_controlled=True
    )
    ss01 = _result(run_all(run, records), "SS-01")
    assert ss01.status == RuleStatus.PASS
    assert ss01.score == 1.0


def test_report_writes_json_artifact(tmp_path):
    run, records = _fully_compliant()
    report = run_all(run, records)
    path = report.to_json_file(tmp_path)
    assert path.exists()
    assert path.name == "test-compliant.json"
    assert '"compliance_score"' in path.read_text(encoding="utf-8")


def test_report_writes_markdown_artifact(tmp_path):
    run, records = _fully_compliant()
    report = run_all(run, records)
    path = report.to_markdown_file(tmp_path)
    assert path.exists()
    assert path.name == "test-compliant.md"
    text = path.read_text(encoding="utf-8")
    assert "| Rule | DPDP principle | Status | Score |" in text
    assert "DM-01" in text


def test_rules_cite_dpdp_principles_not_pinned_sections():
    run, records = _fully_compliant()
    report = run_all(run, records)
    for result in report.results:
        assert result.provision.startswith("DPDP Act 2023")
        # principle-level wording, not a pinned sub-section like "s.6(1)"
        assert "s." not in result.provision


def test_partial_run_scores_in_the_middle_band():
    """Tight field scope but sloppy manifest -> a score clearly between the extremes."""
    run, records = _fully_compliant()
    run.lawful_basis = LawfulBasis(type=LawfulBasisType.CONSENT, reference=None)
    run.deletion_mechanism = None
    run.security = SecurityPosture(transport_encrypted=True, at_rest_encrypted=True)
    run.notice = None
    run.governance = Governance()
    report = run_all(run, records)
    assert 0.4 <= report.compliance_score <= 0.65
    assert _result(report, "DM-01").status == RuleStatus.PASS
    assert _result(report, "PL-01").status == RuleStatus.PASS


def test_no_declared_purpose_fails_pl01():
    run, records = _fully_compliant()
    run.purpose_specified = False
    pl01 = _result(run_all(run, records), "PL-01")
    assert pl01.status == RuleStatus.FAIL
    assert pl01.score == 0.0


def test_secondary_use_is_partial_pl01():
    run, records = _fully_compliant()
    run.secondary_uses = ["analytics dashboard for hospital management"]
    pl01 = _result(run_all(run, records), "PL-01")
    assert pl01.status == RuleStatus.FAIL
    assert pl01.score == pytest.approx(0.5)


def test_missing_notice_fails_nt01():
    run, records = _fully_compliant()
    run.notice = None
    nt01 = _result(run_all(run, records), "NT-01")
    assert nt01.status == RuleStatus.FAIL
    assert nt01.score == 0.0


def test_notice_not_covering_purpose_is_partial_nt01():
    run, records = _fully_compliant()
    run.notice = Notice(reference="generic site notice", covers_purpose=False)
    nt01 = _result(run_all(run, records), "NT-01")
    assert nt01.status == RuleStatus.FAIL
    assert nt01.score == pytest.approx(0.5)


def test_partial_governance_scores_ac01_proportionally():
    run, records = _fully_compliant()
    run.governance = Governance(audit_log_enabled=True)  # 1 of 3
    ac01 = _result(run_all(run, records), "AC-01")
    assert ac01.status == RuleStatus.FAIL
    assert ac01.score == pytest.approx(1 / 3)


def test_full_governance_and_notice_pass():
    run, records = _fully_compliant()
    report = run_all(run, records)
    for rule_id in ("PL-01", "NT-01", "AC-01"):
        assert _result(report, rule_id).status == RuleStatus.PASS


def test_empty_records_makes_dm01_not_applicable():
    run, _ = _fully_compliant()
    report = run_all(run, [])
    assert _result(report, "DM-01").status == RuleStatus.NOT_APPLICABLE
