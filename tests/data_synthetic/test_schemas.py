"""Tests for the per-layer record schemas derived from the catalogue."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from data_synthetic.catalogue import FIELD_CATALOGUE
from data_synthetic.generators import build_dataset
from data_synthetic.schemas import (
    SCHEMAS,
    AuditEventRecord,
    PatientAdministrationRecord,
    schema_for,
    validate_record,
    validate_rows,
)
from interop.layers import HISLayer


def test_one_schema_per_catalogue_layer_with_the_same_fields():
    assert set(SCHEMAS) == set(FIELD_CATALOGUE)
    for layer, model in SCHEMAS.items():
        assert set(model.model_fields) == set(FIELD_CATALOGUE[layer])


def test_generator_output_validates_on_every_layer():
    for layer, rows in build_dataset(5, seed=3).items():
        assert validate_rows(layer, rows) == []


def test_partial_rows_are_valid_because_presence_is_a_compliance_question():
    record = validate_record(HISLayer.PATIENT_ADMINISTRATION, {"mrn": "MRN1", "sex": "F"})
    assert record.mrn == "MRN1" and record.date_of_birth is None


def test_unknown_columns_are_rejected():
    with pytest.raises(ValidationError):
        PatientAdministrationRecord(mrn="MRN1", favourite_colour="blue")


def test_amounts_and_results_are_numeric():
    with pytest.raises(ValidationError):
        validate_record(HISLayer.ADMINISTRATIVE_FINANCIAL, {"billed_amount": "not a number"})
    ok = validate_record(HISLayer.ADMINISTRATIVE_FINANCIAL, {"billed_amount": "1200.50"})
    assert ok.billed_amount == 1200.5


def test_audit_event_schema_exists_for_the_fifth_layer():
    assert schema_for(HISLayer.INFRASTRUCTURE_INTEGRATION) is AuditEventRecord
    ev = AuditEventRecord(audit_event_id="EVT1", action="read", subject_mrn="MRN1")
    assert ev.actor_role is None


def test_validate_rows_reports_each_failure_with_its_row():
    problems = validate_rows(HISLayer.CLINICAL_EHR, [{"lab_result": 1.0}, {"lab_result": "x"}, {"bogus": 1}])
    assert len(problems) == 2
    assert problems[0].startswith("row 1") and problems[1].startswith("row 2")
