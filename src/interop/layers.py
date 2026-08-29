"""Canonical definition of the five-layer HIS architecture.

Single source of truth for layer identity. `data_synthetic` schemas and
`extraction` adapters reference these constants rather than re-declaring layer
names, so the "don't flatten into a single schema" constraint from
PROJECT_CONTEXT.md is enforced structurally.

NOTE: PROJECT_CONTEXT.md names the five-layer architecture but does not enumerate
it. The layers below are the team's working reconstruction (adopted 2026-08-29)
and may be refined before the synthetic data generator (build step 3) is built.
See docs/architecture/five-layer-his.md.
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
