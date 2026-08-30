### Compliance benchmark

_compliance-aware (ours) scores 1.000; unconstrained (baseline) scores 0.131 on the same 7 rules -- a 0.869 gap that is purely a compliance difference, not coverage or speed._

Synthetic data: 5 records/layer x 4 layers, seed 42. 3 extraction tasks, identical DPDP rule set for every technique. Generated 2026-08-30 in 1 ms.

| Technique | Compliance score | Rules passed | DM-01 | LB-01 | SL-01 | SS-01 | PL-01 | NT-01 | AC-01 |
|---|---|---|---|---|---|---|---|---|---|
| compliance-aware (ours) | 1.000 | 7/7 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| minimising, undocumented | 0.500 | 2/7 | 1.00 | 0.50 | 0.50 | 0.50 | 1.00 | 0.00 | 0.00 |
| unconstrained (baseline) | 0.131 | 0/7 | 0.67 | 0.00 | 0.00 | 0.25 | 0.00 | 0.00 | 0.00 |

**Per task**

| Task | compliance-aware | minimising | unconstrained |
|---|---|---|---|
| `patient-summary` | 1.000 | 0.500 | 0.131 |
| `ward-census` | 1.000 | 0.500 | 0.131 |
| `medication-review` | 1.000 | 0.500 | 0.131 |

**What each task needs**

- `patient-summary` (*care_coordination*): mrn, date_of_birth, sex @ patient_administration; primary_diagnosis, medication, allergy @ clinical_ehr
- `ward-census` (*care_coordination*): mrn, admission_ward, admission_datetime @ patient_administration; encounter_datetime @ clinical_ehr
- `medication-review` (*care_coordination*): mrn, date_of_birth @ patient_administration; primary_diagnosis, medication, allergy @ clinical_ehr

**What each technique pulled** (across all tasks)

- **compliance-aware** — 30 records across 2 layer(s); fields by category: administrative (10), clinical (10), direct_identifier (15), quasi_identifier (10); out-of-scope: none
- **minimising** — 30 records across 2 layer(s); fields by category: administrative (10), clinical (10), direct_identifier (15), quasi_identifier (10); out-of-scope: none
- **unconstrained** — 60 records across 4 layer(s); fields by category: administrative (45), clinical (30), contact (15), direct_identifier (15), financial (15), quasi_identifier (15); out-of-scope: contact, financial

**Rules**

- `DM-01` — Data minimisation
- `LB-01` — Lawful basis for processing
- `SL-01` — Storage limitation
- `SS-01` — Security safeguards
- `PL-01` — Purpose limitation
- `NT-01` — Transparency / notice
- `AC-01` — Accountability