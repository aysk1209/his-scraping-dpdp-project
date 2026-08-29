# Five-layer HIS architecture

> **Status: working reconstruction.** `PROJECT_CONTEXT.md` establishes that a
> five-layer HIS architecture underpins the synthetic data generator and the
> extraction interfaces ("don't flatten this into a single schema"), but does not
> enumerate the five layers. The decomposition below was adopted on 2026-08-29 to
> unblock build step 1. **Confirm against the Review-1 deck / background report
> before build step 3 (synthetic data generator).**

The codebase treats this as canonical via
[`src/interop/layers.py`](../../src/interop/layers.py). Nothing should re-declare
layer names elsewhere.

## Layers

| # | Layer (`HISLayer`) | Scope | Representative records |
|---|--------------------|-------|------------------------|
| 1 | `PATIENT_ADMINISTRATION` | Front-office patient lifecycle | Registration, admit/discharge/transfer (ADT), demographics, scheduling, bed management |
| 2 | `CLINICAL_EHR` | Care documentation and ordering | Encounters, problems/diagnoses, clinical orders (CPOE), progress notes, medication records, care plans |
| 3 | `ANCILLARY_DEPARTMENTAL` | Departmental result-producing systems | Laboratory (LIS), imaging (RIS/PACS), pharmacy dispensing, blood bank |
| 4 | `ADMINISTRATIVE_FINANCIAL` | Business operations | Billing, claims / insurance, revenue cycle, inventory, human resources |
| 5 | `INFRASTRUCTURE_INTEGRATION` | Cross-cutting plumbing | Interface / integration engine, master patient index, audit logging, security, messaging fabric |

Layer 5 is structural: it carries no patient-record schema of its own. It is
where interoperability translation and DPDP compliance instrumentation live.

## Interoperability mapping

See [`src/interop/mapping.py`](../../src/interop/mapping.py) and
[`src/interop/README.md`](../../src/interop/README.md) for the layer ↔ standard
matrix (HL7 v2, FHIR, DICOM, ISO/IEEE 11073).

## Open items

- [ ] Verify layer names and boundaries against Review-1 artifacts.
- [ ] Confirm whether the established model is functional (as above) or
      technical (presentation / application / data / integration / infrastructure).
      If technical, `HISLayer` and the mapping need reworking before step 3.
