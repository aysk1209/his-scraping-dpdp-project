### Compliance benchmark

_compliance-aware (ours) scores 1.000; unconstrained (baseline) scores 0.134 on the same 7 rules -- a 0.866 gap. It also pulls 1.00x the fields the purpose requires, against 6.53x for the baseline, at full coverage. That surplus is exactly what the data-minimisation rule penalises, so on this workload compliance and extraction cost move together rather than trading off against each other. morality (privacy by instinct) obtained only 90% of the fields the tasks require: it refused data the purpose lawfully needed. Privacy by instinct fails in both directions._

Synthetic data: 50 records/layer x 5 layers, seed 42. 4 extraction tasks, identical DPDP rule set for every technique. Generated 2026-09-12 in 28 ms.

| Technique | Compliance score | Rules passed | DM-01 | LB-01 | SL-01 | SS-01 | PL-01 | NT-01 | AC-01 |
|---|---|---|---|---|---|---|---|---|---|
| compliance-aware (ours) | 1.000 | 7/7 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| morality (privacy by instinct) | 0.482 | 2/7 | 1.00 | 0.50 | 0.00 | 0.54 | 1.00 | 0.00 | 0.33 |
| unconstrained (baseline) | 0.134 | 0/7 | 0.67 | 0.00 | 0.00 | 0.27 | 0.00 | 0.00 | 0.00 |

**Compliance versus cost**

`excess ratio` is distinct fields pulled divided by the fields the task's purpose requires. It is a cost measure and a compliance measure at once: fields pulled beyond the purpose are precisely the overreach the data-minimisation rule penalises. `coverage` is the guard rail -- it stops a technique scoring well by pulling nothing. Both are deterministic and reproduce on any machine; wall-clock time is reported but is hardware-dependent.

| Technique | Compliance | Excess ratio | Coverage | Fields pulled | Fetches | Pages loaded | Records | Wall-clock (ms) |
|---|---|---|---|---|---|---|---|---|
| compliance-aware (ours) | 1.000 | 1.00 | 1.00 | 950 | 7 | n/a | 350 | 1.2 |
| morality (privacy by instinct) | 0.482 | 0.90 | 0.90 | 850 | 7 | n/a | 350 | 1.3 |
| unconstrained (baseline) | 0.134 | 6.53 | 1.00 | 6200 | 20 | n/a | 1000 | 5.0 |

**Per task**

| Task | compliance-aware | morality | unconstrained |
|---|---|---|---|
| `patient-summary` | 1.000 | 0.476 | 0.131 |
| `ward-census` | 1.000 | 0.476 | 0.131 |
| `medication-review` | 1.000 | 0.476 | 0.131 |
| `appointment-reminder` | 1.000 | 0.500 | 0.143 |

**What each task needs**

- `patient-summary` (*care_coordination*): mrn, date_of_birth, sex @ patient_administration; primary_diagnosis, medication, allergy @ clinical_ehr
- `ward-census` (*care_coordination*): mrn, admission_ward, admission_datetime @ patient_administration; encounter_datetime @ clinical_ehr
- `medication-review` (*care_coordination*): mrn, date_of_birth @ patient_administration; primary_diagnosis, medication, allergy @ clinical_ehr
- `appointment-reminder` (*patient_registration*): mrn, full_name, phone, admission_datetime @ patient_administration

**What each technique pulled** (total over the 4-task workload)

- **compliance-aware** — 350 records across 2 layer(s); fields by category: administrative (150), clinical (100), direct_identifier (200), quasi_identifier (100); out-of-scope: none
- **morality** — 350 records across 2 layer(s); fields by category: administrative (150), clinical (100), direct_identifier (200), quasi_identifier (100); out-of-scope: none
- **unconstrained** — 1000 records across 5 layer(s); fields by category: administrative (800), clinical (400), contact (200), direct_identifier (400), financial (200), quasi_identifier (200); out-of-scope: clinical, contact, financial

**Rules**

- `DM-01` — Data minimisation
- `LB-01` — Lawful basis for processing
- `SL-01` — Storage limitation
- `SS-01` — Security safeguards
- `PL-01` — Purpose limitation
- `NT-01` — Transparency / notice
- `AC-01` — Accountability