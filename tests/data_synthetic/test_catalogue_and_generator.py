"""Tests for the synthetic field catalogue and record generator (build step 3 slice)."""

from __future__ import annotations

from compliance.models import FieldCategory
from data_synthetic.catalogue import FIELD_CATALOGUE, categories_for_fields, fields_for
from data_synthetic.generators import build_dataset, generate_layer_records
from interop.layers import HISLayer

_RECORD_LAYERS = set(HISLayer)


def test_catalogue_covers_all_five_layers():
    assert set(FIELD_CATALOGUE) == _RECORD_LAYERS


def test_infrastructure_layer_is_audit_instrumentation_not_a_patient_record():
    fields = FIELD_CATALOGUE[HISLayer.INFRASTRUCTURE_INTEGRATION]
    assert "audit_event_id" in fields and "action" in fields
    # ...but it still references the patient, so it is not identifier-free.
    assert fields["subject_mrn"] == FieldCategory.DIRECT_IDENTIFIER
    assert FieldCategory.CLINICAL not in fields.values()


def test_every_catalogue_category_is_a_valid_field_category():
    for layer_fields in FIELD_CATALOGUE.values():
        for category in layer_fields.values():
            assert isinstance(category, FieldCategory)


def test_generate_layer_records_has_all_catalogue_fields():
    rows = generate_layer_records(HISLayer.CLINICAL_EHR, 3, seed=1)
    assert len(rows) == 3
    for row in rows:
        assert set(row) == set(fields_for(HISLayer.CLINICAL_EHR))


def test_generation_is_deterministic_with_a_seed():
    a = generate_layer_records(HISLayer.PATIENT_ADMINISTRATION, 5, seed=7)
    b = generate_layer_records(HISLayer.PATIENT_ADMINISTRATION, 5, seed=7)
    assert a == b


def test_build_dataset_produces_every_layer_at_requested_size():
    dataset = build_dataset(2, seed=42)
    assert set(dataset) == _RECORD_LAYERS
    assert all(len(rows) == 2 for rows in dataset.values())


def test_categories_for_fields_maps_via_catalogue_and_ignores_unknowns():
    cats = categories_for_fields(
        HISLayer.PATIENT_ADMINISTRATION,
        ["mrn", "email", "sex", "not_a_real_field"],
    )
    assert cats == {
        FieldCategory.DIRECT_IDENTIFIER,
        FieldCategory.CONTACT,
        FieldCategory.QUASI_IDENTIFIER,
    }


def test_financial_layer_is_all_financial_category():
    cats = categories_for_fields(
        HISLayer.ADMINISTRATIVE_FINANCIAL,
        fields_for(HISLayer.ADMINISTRATIVE_FINANCIAL),
    )
    assert cats == {FieldCategory.FINANCIAL}
