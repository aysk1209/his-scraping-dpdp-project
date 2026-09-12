### Compliance benchmark

_compliance-aware (ours) scores 1.000; unconstrained (baseline) scores 0.135 on the same 7 rules -- a 0.865 gap. It also pulls 1.00x the fields the purpose requires, against 7.15x for the baseline, at full coverage. That surplus is exactly what the data-minimisation rule penalises, so on this workload compliance and extraction cost move together rather than trading off against each other. morality (privacy by instinct) obtained only 85% of the fields the tasks require: it refused data the purpose lawfully needed. Privacy by instinct fails in both directions._

Synthetic data: portal, 30 records/module, seed 42. 3 extraction tasks, identical DPDP rule set for every technique. Generated 2026-09-12 in 104348 ms.

| Technique | Compliance score | Rules passed | DM-01 | LB-01 | SL-01 | SS-01 | PL-01 | NT-01 | AC-01 |
|---|---|---|---|---|---|---|---|---|---|
| compliance-aware (ours) | 1.000 | 7/7 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| morality (privacy by instinct) | 0.484 | 2/7 | 1.00 | 0.50 | 0.00 | 0.56 | 1.00 | 0.00 | 0.33 |
| unconstrained (baseline) | 0.135 | 0/7 | 0.67 | 0.00 | 0.00 | 0.28 | 0.00 | 0.00 | 0.00 |

**Compliance versus cost**

`excess ratio` is distinct fields pulled divided by the fields the task's purpose requires. It is a cost measure and a compliance measure at once: fields pulled beyond the purpose are precisely the overreach the data-minimisation rule penalises. `coverage` is the guard rail -- it stops a technique scoring well by pulling nothing. Both are deterministic and reproduce on any machine; wall-clock time is reported but is hardware-dependent.

| Technique | Compliance | Excess ratio | Coverage | Fields pulled | Fetches | Pages loaded | Records | Wall-clock (ms) |
|---|---|---|---|---|---|---|---|---|
| compliance-aware (ours) | 1.000 | 1.00 | 1.00 | 390 | 5 | 100 | 150 | 16435.0 |
| morality (privacy by instinct) | 0.484 | 0.85 | 0.85 | 330 | 5 | 100 | 150 | 16738.8 |
| unconstrained (baseline) | 0.135 | 7.15 | 1.00 | 2790 | 15 | 480 | 450 | 71168.6 |

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

- **compliance-aware** — 150 records across 2 layer(s); fields by category: administrative (90), clinical (30), direct_identifier (90), quasi_identifier (30); out-of-scope: none
- **morality** — 150 records across 2 layer(s); fields by category: administrative (90), clinical (30), direct_identifier (90), quasi_identifier (30); out-of-scope: none
- **unconstrained** — 450 records across 5 layer(s); fields by category: administrative (360), clinical (180), contact (90), direct_identifier (180), financial (90), quasi_identifier (90); out-of-scope: clinical, contact, financial

**Rules**

- `DM-01` — Data minimisation
- `LB-01` — Lawful basis for processing
- `SL-01` — Storage limitation
- `SS-01` — Security safeguards
- `PL-01` — Purpose limitation
- `NT-01` — Transparency / notice
- `AC-01` — Accountability