"""Mapping from each HIS layer to the interoperability standards that realistically
carry that layer's records.

Used by `data_synthetic` (to decide which shaped outputs to emit per layer) and
by the compliance benchmarking harness (to report extraction coverage per
standard).

Priority per PROJECT_CONTEXT.md: HL7 and FHIR first; DICOM and ISO/IEEE 11073
are stubs for this phase.
"""

from __future__ import annotations

from enum import Enum

from interop.layers import HISLayer


class InteropStandard(str, Enum):
    """The four interoperability standards established for this project."""

    HL7_V2 = "hl7_v2"
    FHIR = "fhir"
    DICOM = "dicom"
    ISO_IEEE_11073 = "iso_ieee_11073"


# Working reconstruction alongside interop.layers — revisit if the five layers
# are refined.
LAYER_STANDARDS: dict[HISLayer, tuple[InteropStandard, ...]] = {
    HISLayer.PATIENT_ADMINISTRATION: (
        InteropStandard.HL7_V2,
        InteropStandard.FHIR,
    ),
    HISLayer.CLINICAL_EHR: (
        InteropStandard.HL7_V2,
        InteropStandard.FHIR,
    ),
    HISLayer.ANCILLARY_DEPARTMENTAL: (
        InteropStandard.HL7_V2,
        InteropStandard.FHIR,
        InteropStandard.DICOM,
        InteropStandard.ISO_IEEE_11073,
    ),
    HISLayer.ADMINISTRATIVE_FINANCIAL: (InteropStandard.FHIR,),
    HISLayer.INFRASTRUCTURE_INTEGRATION: (),
}


def standards_for(layer: HISLayer) -> tuple[InteropStandard, ...]:
    """Return the interoperability standards associated with a HIS layer."""
    return LAYER_STANDARDS[layer]
