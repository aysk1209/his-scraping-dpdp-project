"""Interoperability helpers for the four established standards: HL7 v2, FHIR,
DICOM, ISO/IEEE 11073.

Responsibilities:
  - `layers`   : canonical definition of the five-layer HIS architecture
                 (single source of truth, imported across the codebase).
  - `mapping`  : which standards realistically carry each layer's records.
  - `hl7` / `fhir` / `dicom` / `iso_ieee_11073` : lightweight, hand-rolled
                 record shapers per standard.

Priority (PROJECT_CONTEXT.md): HL7 and FHIR shaping come first and must be
usable; DICOM and ISO/IEEE 11073 are modelled as stubs for this phase.

No HIS vendor names in this package (CLAUDE.md convention).
"""
