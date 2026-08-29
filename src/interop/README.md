# `interop` — interoperability helpers

Hand-rolled, lightweight shapers for the four interoperability standards
established for this project. No external interop libraries and no HIS vendor
names (CLAUDE.md convention). Everything here is *shaping only* — building
standard-structured records out of internal data. No wire transport.

## Layout

| Path | Purpose | Phase state |
|------|---------|-------------|
| `layers.py` | Canonical five-layer HIS architecture — single source of truth | defined |
| `mapping.py` | Layer → interoperability standards it carries | defined |
| `hl7/messages.py` | HL7 v2 messages: ADT / ORM / ORU | stub (with FHIR, priority for step 3) |
| `fhir/resources.py` | FHIR R4 resource shaping | stub (priority path for step 3) |
| `dicom/metadata.py` | DICOM imaging metadata (no pixels) | stub, this phase only |
| `iso_ieee_11073/pocd.py` | Point-of-care device observations | stub, this phase only |

## Five-layer ↔ standard matrix

> The five layers are a **working reconstruction** — PROJECT_CONTEXT.md names the
> architecture but does not enumerate it. Adopted 2026-08-29; revisit before
> build step 3. See [`../../docs/architecture/five-layer-his.md`](../../docs/architecture/five-layer-his.md).

| # | HIS layer | Representative records | Standards |
|---|-----------|------------------------|-----------|
| 1 | Patient Administration | registration, ADT, demographics, scheduling | HL7 v2 (ADT), FHIR (Patient, Appointment) |
| 2 | Clinical / EHR | encounters, diagnoses, orders, notes, meds | HL7 v2 (ORM), FHIR (Encounter, Condition, MedicationRequest) |
| 3 | Ancillary / Departmental | lab, imaging, pharmacy | HL7 v2 (ORU), FHIR (Observation, DiagnosticReport), DICOM, ISO/IEEE 11073 |
| 4 | Administrative / Financial | billing, claims, inventory, HR | FHIR (Claim, Coverage, Invoice) |
| 5 | Infrastructure / Integration | interface engine, master patient index, audit | — (hosts interop + compliance instrumentation, not a record schema) |

Priority per PROJECT_CONTEXT.md: HL7 and FHIR shaping first and must be usable;
DICOM and ISO/IEEE 11073 stay stubs for Review 2.
