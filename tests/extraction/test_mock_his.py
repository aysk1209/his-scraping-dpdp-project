"""Tests for MockHISDataSource and the synthetic -> extraction -> compliance flow."""

from __future__ import annotations

from compliance.checkers import run_all
from compliance.models import (
    ExtractedRecord,
    ExtractionRun,
    Governance,
    LawfulBasis,
    LawfulBasisType,
    Notice,
    Purpose,
    SecurityPosture,
)
from data_synthetic.catalogue import categories_for_fields, fields_for
from extraction.adapters.mock_his import MockHISDataSource
from extraction.base import HISDataSource
from interop.layers import HISLayer


def test_mock_source_is_a_hisdatasource():
    assert isinstance(MockHISDataSource(records_per_layer=1, seed=1), HISDataSource)


def test_layers_are_the_record_layers_not_infrastructure():
    source = MockHISDataSource(records_per_layer=1, seed=1)
    assert HISLayer.PATIENT_ADMINISTRATION in source.layers()
    assert HISLayer.INFRASTRUCTURE_INTEGRATION not in source.layers()


def test_fetch_without_fields_returns_full_records():
    source = MockHISDataSource(records_per_layer=2, seed=1)
    rows = list(source.fetch(HISLayer.CLINICAL_EHR))
    assert len(rows) == 2
    assert set(rows[0]) == set(fields_for(HISLayer.CLINICAL_EHR))


def test_fetch_with_fields_projects_to_requested_only():
    source = MockHISDataSource(records_per_layer=3, seed=1)
    rows = list(source.fetch(HISLayer.PATIENT_ADMINISTRATION, fields=["mrn", "sex"]))
    assert len(rows) == 3
    assert all(set(row) == {"mrn", "sex"} for row in rows)


def test_in_scope_selection_scores_fully_compliant():
    source = MockHISDataSource(records_per_layer=3, seed=42)
    records = [
        ExtractedRecord(
            source_layer=HISLayer.CLINICAL_EHR.value,
            field_categories=categories_for_fields(HISLayer.CLINICAL_EHR, row.keys()),
        )
        for row in source.fetch(
            HISLayer.CLINICAL_EHR, fields=["primary_diagnosis", "medication"]
        )
    ]
    run = ExtractionRun(
        run_id="t-compliant",
        purpose=Purpose.CARE_COORDINATION,
        lawful_basis=LawfulBasis(
            type=LawfulBasisType.LEGITIMATE_USE, reference="medical services"
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
    assert run_all(run, records).compliance_score == 1.0


def test_grab_everything_with_no_manifest_scores_low():
    source = MockHISDataSource(records_per_layer=3, seed=42)
    records = [
        ExtractedRecord(
            source_layer=HISLayer.ADMINISTRATIVE_FINANCIAL.value,
            field_categories=categories_for_fields(
                HISLayer.ADMINISTRATIVE_FINANCIAL, row.keys()
            ),
        )
        for row in source.fetch(HISLayer.ADMINISTRATIVE_FINANCIAL)
    ]
    run = ExtractionRun(run_id="t-careless", purpose=Purpose.CARE_COORDINATION)
    assert run_all(run, records).compliance_score < 0.5
