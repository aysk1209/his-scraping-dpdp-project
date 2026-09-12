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
| `hl7/messages.py` | HL7 v2 messages: ADT^A04, ORM^O01, ORU^R01, DFT^P03 — hand-rolled segment model, pipe-and-hat encoding | **implemented** |
| `fhir/resources.py` | FHIR R4 resources: Patient, Encounter, Condition, MedicationRequest, AllergyIntolerance, ServiceRequest, Observation, DiagnosticReport, Invoice, Coverage | **implemented** |
| `normalise.py` | Shapes a technique's rows per the layer↔standard matrix; applies pseudonymisation when the manifest declares it; **audits** the export for raw identifiers | **implemented** |
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
| 4 | Administrative / Financial | billing, claims, inventory, HR | HL7 v2 (DFT, BAR), FHIR (Coverage, Account, Invoice, ClaimResponse) |
| 5 | Infrastructure / Integration | audit events: who touched which record, when, from which system | FHIR (AuditEvent) — compliance instrumentation, not a patient-record schema |

Priority per PROJECT_CONTEXT.md: HL7 and FHIR shaping first and must be usable —
done 2026-09-12; DICOM and ISO/IEEE 11073 stay stubs and are skipped (and reported
as skipped) by `normalise`.

## Shaping is compliance work, not plumbing

Two properties make it so, and both are tested:

- **Shaping adds nothing.** A builder sets only the fields present in the row.
  Nothing is defaulted, inferred or looked up, so the data-minimisation property of
  the extraction survives into the artefacts a downstream system would receive.
- **The manifest's claim becomes behaviour, and is then checked.** If a run declares
  `identifiers_pseudonymised`, direct identifiers are replaced by keyed tokens
  (`compliance.pseudonymise`) before shaping. `normalise.audit` then searches the
  emitted HL7 and FHIR for the raw identifier values that were extracted. The
  compliant technique's export leaks none; the baseline's leaks every one. SS-01's
  pseudonymisation check is thereby verified against output rather than taken on
  faith from the manifest.
