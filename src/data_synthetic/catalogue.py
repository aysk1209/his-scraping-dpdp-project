"""Field inventory for synthetic HIS records: which fields exist per HIS layer
and which DPDP field category each maps to.

This is the bridge between generated data and the compliance rules -- an
extraction pulls a set of named fields, and ``categories_for_fields`` turns that
selection into the ``FieldCategory`` set the rules score.

Assumptions (pending confirmation against Review-1 artifacts):
  - the five-layer model is functional (see ``interop.layers``);
  - the Infrastructure/Integration layer carries no patient-record schema and so
    has no entry here;
  - staff names (e.g. attending clinician) are ADMINISTRATIVE assignment data,
    not DIRECT_IDENTIFIER -- the Data Principal modelled here is the patient.
"""

from __future__ import annotations

from collections.abc import Iterable

from compliance.models import FieldCategory
from interop.layers import HISLayer

FIELD_CATALOGUE: dict[HISLayer, dict[str, FieldCategory]] = {
    HISLayer.PATIENT_ADMINISTRATION: {
        "mrn": FieldCategory.DIRECT_IDENTIFIER,
        "full_name": FieldCategory.DIRECT_IDENTIFIER,
        "phone": FieldCategory.DIRECT_IDENTIFIER,
        "email": FieldCategory.CONTACT,
        "street_address": FieldCategory.CONTACT,
        "date_of_birth": FieldCategory.QUASI_IDENTIFIER,
        "sex": FieldCategory.QUASI_IDENTIFIER,
        "pincode": FieldCategory.QUASI_IDENTIFIER,
        "admission_ward": FieldCategory.ADMINISTRATIVE,
        "admission_datetime": FieldCategory.ADMINISTRATIVE,
    },
    HISLayer.CLINICAL_EHR: {
        "primary_diagnosis": FieldCategory.CLINICAL,
        "medication": FieldCategory.CLINICAL,
        "lab_result": FieldCategory.CLINICAL,
        "allergy": FieldCategory.CLINICAL,
        "encounter_datetime": FieldCategory.ADMINISTRATIVE,
        "attending_clinician": FieldCategory.ADMINISTRATIVE,
    },
    HISLayer.ANCILLARY_DEPARTMENTAL: {
        "order_id": FieldCategory.ADMINISTRATIVE,
        "specimen_type": FieldCategory.CLINICAL,
        "result_value": FieldCategory.CLINICAL,
        "imaging_modality": FieldCategory.CLINICAL,
        "report_text": FieldCategory.CLINICAL,
    },
    HISLayer.ADMINISTRATIVE_FINANCIAL: {
        "invoice_id": FieldCategory.FINANCIAL,
        "billed_amount": FieldCategory.FINANCIAL,
        "insurance_policy_no": FieldCategory.FINANCIAL,
        "payer_name": FieldCategory.FINANCIAL,
    },
}


def fields_for(layer: HISLayer) -> list[str]:
    """All catalogue field names for a layer."""

    return list(FIELD_CATALOGUE[layer])


def categories_for_fields(layer: HISLayer, field_names: Iterable[str]) -> set[FieldCategory]:
    """Map a selection of field names to their DPDP categories via the catalogue.

    Unknown field names are ignored -- a rule cannot categorise what the
    catalogue does not describe.
    """

    catalogue = FIELD_CATALOGUE[layer]
    return {catalogue[name] for name in field_names if name in catalogue}
