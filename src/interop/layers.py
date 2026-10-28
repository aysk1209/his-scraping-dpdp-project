"""Canonical definition of the five-layer HIS architecture.

Single source of truth for layer identity. `data_synthetic` schemas and
`extraction` adapters reference these constants rather than re-declaring layer
names, so the five layers are never flattened into a single schema.

The layers are a working reconstruction and may be refined if a real HIS differs.
"""

from __future__ import annotations

from enum import Enum


class HISLayer(str, Enum):
    """The five functional layers of a Hospital Information System."""

    PATIENT_ADMINISTRATION = "patient_administration"
    CLINICAL_EHR = "clinical_ehr"
    ANCILLARY_DEPARTMENTAL = "ancillary_departmental"
    ADMINISTRATIVE_FINANCIAL = "administrative_financial"
    INFRASTRUCTURE_INTEGRATION = "infrastructure_integration"


LAYER_DESCRIPTIONS: dict[HISLayer, str] = {
    HISLayer.PATIENT_ADMINISTRATION: (
        "Registration, admit/discharge/transfer (ADT), demographics, scheduling."
    ),
    HISLayer.CLINICAL_EHR: (
        "Encounters, diagnoses, clinical orders (CPOE), notes, medication records."
    ),
    HISLayer.ANCILLARY_DEPARTMENTAL: (
        "Departmental systems: laboratory, imaging, pharmacy dispensing."
    ),
    HISLayer.ADMINISTRATIVE_FINANCIAL: (
        "Billing, claims / insurance, revenue cycle, inventory, human resources."
    ),
    HISLayer.INFRASTRUCTURE_INTEGRATION: (
        "Interface engine, master patient index, audit / security, messaging fabric. "
        "Hosts interoperability and compliance instrumentation rather than a record schema."
    ),
}
