"""Field inventory for synthetic HIS records: which fields exist per HIS layer
and which DPDP field category each maps to.

This is the bridge between generated data and the compliance rules -- an
extraction pulls a set of named fields, and ``categories_for_fields`` turns that
selection into the ``FieldCategory`` set the rules score.

Assumptions (working set; reconfigure if real HIS access shows otherwise):
  - the five-layer model is functional (see ``interop.layers``);
  - the Infrastructure/Integration layer carries no *patient-record* schema; its
    records are compliance instrumentation -- audit events describing who touched
    which record, when, from which system. They reference the patient by MRN, so
    the layer is not identifier-free, which is exactly why it is worth modelling;
  - staff names (e.g. attending clinician) are ADMINISTRATIVE assignment data,
    not DIRECT_IDENTIFIER -- the Data Principal modelled here is the patient.

``infer_layer`` is the inverse mapping: given field names seen somewhere (a
scraped table, an exported spreadsheet), which layer explains the most of them?
It is how the Tier 2 crawler and the dataset adapter classify what they find
without being told.
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
    # DPDP Act 2023 -- accountability principle: the Data Fiduciary can show what
    # was done with personal data. The audit log is that evidence, and it is
    # personal data itself because it names the record it concerns.
    HISLayer.INFRASTRUCTURE_INTEGRATION: {
        "audit_event_id": FieldCategory.ADMINISTRATIVE,
        "event_timestamp": FieldCategory.ADMINISTRATIVE,
        "actor_role": FieldCategory.ADMINISTRATIVE,
        "action": FieldCategory.ADMINISTRATIVE,
        "source_system": FieldCategory.ADMINISTRATIVE,
        "subject_mrn": FieldCategory.DIRECT_IDENTIFIER,
    },
}


def fields_for(layer: HISLayer) -> list[str]:
    """All catalogue field names for a layer."""

    return list(FIELD_CATALOGUE[layer])


def infer_layer(field_names: Iterable[str]) -> tuple[HISLayer | None, float]:
    """Which layer's catalogue explains the most of these field names?

    Returns the layer and the share of the names it explains (0-1), or
    ``(None, 0.0)`` when nothing matches. Used to classify a scraped module or an
    exported file from its content rather than from what it is called.
    """

    names = [n for n in dict.fromkeys(field_names) if n]
    if not names:
        return None, 0.0
    best_layer, best_hits = None, 0
    for layer, catalogue in FIELD_CATALOGUE.items():
        hits = sum(1 for n in names if n in catalogue)
        if hits > best_hits:
            best_layer, best_hits = layer, hits
    if best_layer is None:
        return None, 0.0
    return best_layer, round(best_hits / len(names), 3)


def categories_for_fields(layer: HISLayer, field_names: Iterable[str]) -> set[FieldCategory]:
    """Map a selection of field names to their DPDP categories via the catalogue.

    Unknown field names are ignored -- a rule cannot categorise what the
    catalogue does not describe.
    """

    catalogue = FIELD_CATALOGUE[layer]
    return {catalogue[name] for name in field_names if name in catalogue}
