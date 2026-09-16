### Navigation map

Discovered by the browser in 11 page loads, starting from the home page after login. The HIS layer of each module is **inferred from the field names found on its pages**, matched against the field catalogue -- never from the URL. Confidence is the share of the fields seen that the inferred layer's catalogue explains.

| Module | Path | Pages | Records | Inferred layer | Confidence |
|---|---|---|---|---|---|
| Patient Registration | `/m/registration/` | 2 | 20 | `patient_administration` | 100% |
| Clinical Records | `/m/clinical/` | 2 | 20 | `clinical_ehr` | 100% |
| Departmental Orders | `/m/departments/` | 2 | 20 | `ancillary_departmental` | 100% |
| Billing & Accounts | `/m/billing/` | 2 | 20 | `administrative_financial` | 100% |
| Audit Log | `/m/integration/` | 2 | 20 | `infrastructure_integration` | 100% |

**Where each field lives.** Fields on the list page cost one load per page; fields only on the record page cost one load per record. That difference is what makes over-asking visible in the cost profile.

| Module | In the list table | Only on the record page |
|---|---|---|
| Patient Registration | `mrn`, `full_name`, `sex`, `admission_ward` | `phone`, `email`, `street_address`, `date_of_birth`, `pincode`, `admission_datetime` |
| Clinical Records | `encounter_datetime`, `primary_diagnosis`, `attending_clinician` | `medication`, `lab_result`, `allergy` |
| Departmental Orders | `order_id`, `specimen_type`, `imaging_modality` | `result_value`, `report_text` |
| Billing & Accounts | `invoice_id`, `billed_amount`, `payer_name` | `insurance_policy_no` |
| Audit Log | `audit_event_id`, `event_timestamp`, `actor_role`, `action` | `source_system`, `subject_mrn` |

*Discovered 2026-09-16.*