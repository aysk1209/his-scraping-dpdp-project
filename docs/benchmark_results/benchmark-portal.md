### Compliance benchmark

_compliance-aware (ours) scores 1.000; unconstrained (baseline) scores 0.135 on the same 7 rules -- a 0.865 gap. It also pulls 1.00x the fields the purpose requires, against 7.15x for the baseline, at full coverage. That surplus is exactly what the data-minimisation rule penalises, so on this workload compliance and extraction cost move together rather than trading off against each other. morality (privacy by instinct) obtained only 85% of the fields the tasks require: it refused data the purpose lawfully needed. Privacy by instinct fails in both directions._

Synthetic data: portal, 20 records/module, seed 42. 3 extraction tasks, identical DPDP rule set for every technique. Generated 2026-09-15 in 54566 ms.

| Technique | Compliance score | Rules passed | DM-01 | LB-01 | SL-01 | SS-01 | PL-01 | NT-01 | AC-01 |
|---|---|---|---|---|---|---|---|---|---|
| compliance-aware (ours) | 1.000 | 7/7 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| morality (privacy by instinct) | 0.484 | 2/7 | 1.00 | 0.50 | 0.00 | 0.56 | 1.00 | 0.00 | 0.33 |
| unconstrained (baseline) | 0.135 | 0/7 | 0.67 | 0.00 | 0.00 | 0.28 | 0.00 | 0.00 | 0.00 |

**Compliance versus cost**

`excess ratio` is distinct fields pulled divided by the fields the task's purpose requires. It is a cost measure and a compliance measure at once: fields pulled beyond the purpose are precisely the overreach the data-minimisation rule penalises. `coverage` is the guard rail -- it stops a technique scoring well by pulling nothing. Both are deterministic and reproduce on any machine; wall-clock time is reported but is hardware-dependent.

| Technique | Compliance | Excess ratio | Coverage | Fields pulled | Fetches | Pages loaded | Records | Wall-clock (ms) |
|---|---|---|---|---|---|---|---|---|
| compliance-aware (ours) | 1.000 | 1.00 | 1.00 | 260 | 5 | 70 | 100 | 5200.4 |
| morality (privacy by instinct) | 0.484 | 0.85 | 0.85 | 220 | 5 | 70 | 100 | 5515.6 |
| unconstrained (baseline) | 0.135 | 7.15 | 1.00 | 1860 | 15 | 330 | 300 | 43846.4 |

**Per task**

| Task | compliance-aware | morality | unconstrained |
|---|---|---|---|
| `patient-summary` | 1.000 | 0.476 | 0.131 |
| `ward-census` | 1.000 | 0.476 | 0.131 |
| `appointment-reminder` | 1.000 | 0.500 | 0.143 |

**What each task needs**

- `patient-summary` (*care_coordination*): mrn, date_of_birth, sex @ patient_administration; primary_diagnosis, medication, allergy @ clinical_ehr
- `ward-census` (*care_coordination*): mrn, admission_ward @ patient_administration; encounter_datetime @ clinical_ehr
- `appointment-reminder` (*patient_registration*): mrn, full_name, phone, admission_datetime @ patient_administration

**What each technique pulled** (total over the 3-task workload)

- **compliance-aware** — 100 records across 2 layer(s); records carrying each category: administrative (60), clinical (20), direct_identifier (60), quasi_identifier (20); out-of-scope: none
- **morality** — 100 records across 2 layer(s); records carrying each category: administrative (60), clinical (20), direct_identifier (60), quasi_identifier (20); out-of-scope: none
- **unconstrained** — 300 records across 5 layer(s); records carrying each category: administrative (240), clinical (120), contact (60), direct_identifier (120), financial (60), quasi_identifier (60); out-of-scope: clinical, contact, financial

**Rules**

- `DM-01` — Data minimisation
- `LB-01` — Lawful basis for processing
- `SL-01` — Storage limitation
- `SS-01` — Security safeguards
- `PL-01` — Purpose limitation
- `NT-01` — Transparency / notice
- `AC-01` — Accountability