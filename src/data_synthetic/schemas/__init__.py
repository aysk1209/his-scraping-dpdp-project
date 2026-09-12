"""Per-layer record schemas (build step 3), derived from the field catalogue.

One pydantic model per HIS layer, built from ``FIELD_CATALOGUE`` so the schema
and the catalogue cannot disagree about which fields a layer has. The catalogue
says what a field *is* for compliance (its DPDP category); the schema says what
shape its value takes (string, date, amount). Both are keyed by the same names.

Kept as one model per layer rather than one flat record type -- the five-layer
structure is preserved through the pipeline (PROJECT_CONTEXT.md). The types are
deliberately permissive where a real export might be messy (dates and timestamps
as ISO strings, amounts as floats), so that a real hospital file validates on
structure without a normalisation pass first.

    from data_synthetic.schemas import schema_for, validate_record
    PatientAdministrationRecord = schema_for(HISLayer.PATIENT_ADMINISTRATION)
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError, create_model

from data_synthetic.catalogue import FIELD_CATALOGUE
from interop.layers import HISLayer

# Value shape per field. Anything not listed is a string.
_FIELD_TYPES: dict[str, type] = {
    "lab_result": float,
    "result_value": float,
    "billed_amount": float,
}

_MODEL_NAMES: dict[HISLayer, str] = {
    HISLayer.PATIENT_ADMINISTRATION: "PatientAdministrationRecord",
    HISLayer.CLINICAL_EHR: "ClinicalRecord",
    HISLayer.ANCILLARY_DEPARTMENTAL: "DepartmentalRecord",
    HISLayer.ADMINISTRATIVE_FINANCIAL: "FinancialRecord",
    HISLayer.INFRASTRUCTURE_INTEGRATION: "AuditEventRecord",
}


def _build(layer: HISLayer) -> type[BaseModel]:
    fields: dict[str, Any] = {}
    for name in FIELD_CATALOGUE[layer]:
        # Every field is optional: an extraction may legitimately pull a subset,
        # and a real export may omit columns. Presence is a compliance question
        # (minimisation), not a validity one.
        fields[name] = (_FIELD_TYPES.get(name, str) | None, None)
    return create_model(
        _MODEL_NAMES[layer],
        __config__=ConfigDict(extra="forbid", str_strip_whitespace=True),
        **fields,
    )


SCHEMAS: dict[HISLayer, type[BaseModel]] = {layer: _build(layer) for layer in FIELD_CATALOGUE}

PatientAdministrationRecord = SCHEMAS[HISLayer.PATIENT_ADMINISTRATION]
ClinicalRecord = SCHEMAS[HISLayer.CLINICAL_EHR]
DepartmentalRecord = SCHEMAS[HISLayer.ANCILLARY_DEPARTMENTAL]
FinancialRecord = SCHEMAS[HISLayer.ADMINISTRATIVE_FINANCIAL]
AuditEventRecord = SCHEMAS[HISLayer.INFRASTRUCTURE_INTEGRATION]


def schema_for(layer: HISLayer) -> type[BaseModel]:
    return SCHEMAS[layer]


def validate_record(layer: HISLayer, row: dict[str, Any]) -> BaseModel:
    """Validate one row against its layer's schema; raises ``ValidationError``."""

    return SCHEMAS[layer].model_validate(row)


def validate_rows(layer: HISLayer, rows: list[dict[str, Any]]) -> list[str]:
    """Validate many rows; return one message per failure (empty list = all valid)."""

    problems: list[str] = []
    for i, row in enumerate(rows):
        try:
            validate_record(layer, row)
        except ValidationError as exc:
            problems.append(f"row {i}: {exc.errors()[0]['msg']} ({exc.errors()[0]['loc']})")
    return problems


__all__ = [
    "SCHEMAS", "schema_for", "validate_record", "validate_rows",
    "PatientAdministrationRecord", "ClinicalRecord", "DepartmentalRecord",
    "FinancialRecord", "AuditEventRecord",
]
