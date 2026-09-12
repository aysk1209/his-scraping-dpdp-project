### Compliance benchmark

_compliance-aware (ours) scores 1.000; unconstrained (baseline) scores 0.131 on the same 7 rules -- a 0.869 gap. It also pulls 1.00x the fields the purpose requires, against 6.89x for the baseline, at full coverage. That surplus is exactly what the data-minimisation rule penalises, so on this workload compliance and extraction cost move together rather than trading off against each other._

Synthetic data: portal, 30 records/module, seed 42. 2 extraction tasks, identical DPDP rule set for every technique. Generated 2026-09-12 in 65940 ms.

| Technique | Compliance score | Rules passed | DM-01 | LB-01 | SL-01 | SS-01 | PL-01 | NT-01 | AC-01 |
|---|---|---|---|---|---|---|---|---|---|
| compliance-aware (ours) | 1.000 | 7/7 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| minimising, undocumented | 0.500 | 2/7 | 1.00 | 0.50 | 0.50 | 0.50 | 1.00 | 0.00 | 0.00 |
| unconstrained (baseline) | 0.131 | 0/7 | 0.67 | 0.00 | 0.00 | 0.25 | 0.00 | 0.00 | 0.00 |

**Compliance versus cost**

`excess ratio` is distinct fields pulled divided by the fields the task's purpose requires. It is a cost measure and a compliance measure at once: fields pulled beyond the purpose are precisely the overreach the data-minimisation rule penalises. `coverage` is the guard rail -- it stops a technique scoring well by pulling nothing. Both are deterministic and reproduce on any machine; wall-clock time is reported but is hardware-dependent.

| Technique | Compliance | Excess ratio | Coverage | Fields pulled | Fetches | Pages loaded | Records | Wall-clock (ms) |
|---|---|---|---|---|---|---|---|---|
| compliance-aware (ours) | 1.000 | 1.00 | 1.00 | 270 | 4 | 68 | 120 | 11102.4 |
| minimising, undocumented | 0.500 | 1.00 | 1.00 | 270 | 4 | 68 | 120 | 10978.6 |
| unconstrained (baseline) | 0.131 | 6.89 | 1.00 | 1860 | 10 | 320 | 300 | 43855.2 |

**Per task**

| Task | compliance-aware | minimising | unconstrained |
|---|---|---|---|
| `patient-summary` | 1.000 | 0.500 | 0.131 |
| `ward-census` | 1.000 | 0.500 | 0.131 |

**What each task needs**

- `patient-summary` (*care_coordination*): mrn, date_of_birth, sex @ patient_administration; primary_diagnosis, medication, allergy @ clinical_ehr
- `ward-census` (*care_coordination*): mrn, admission_ward @ patient_administration; encounter_datetime @ clinical_ehr

**What each technique pulled** (total over the 2-task workload)

- **compliance-aware** — 120 records across 2 layer(s); fields by category: administrative (60), clinical (30), direct_identifier (60), quasi_identifier (30); out-of-scope: none
- **minimising** — 120 records across 2 layer(s); fields by category: administrative (60), clinical (30), direct_identifier (60), quasi_identifier (30); out-of-scope: none
- **unconstrained** — 300 records across 5 layer(s); fields by category: administrative (240), clinical (120), contact (60), direct_identifier (120), financial (60), quasi_identifier (60); out-of-scope: contact, financial

**Rules**

- `DM-01` — Data minimisation
- `LB-01` — Lawful basis for processing
- `SL-01` — Storage limitation
- `SS-01` — Security safeguards
- `PL-01` — Purpose limitation
- `NT-01` — Transparency / notice
- `AC-01` — Accountability