### Compliance benchmark

_compliance-aware (ours) scores 1.000; unconstrained (baseline) scores 0.136 on the same 7 rules -- a 0.864 gap. It also pulls 1.00x the fields the purpose requires, against 7.09x for unconstrained (baseline) at full coverage. That surplus is exactly what the data-minimisation rule penalises, so on this workload compliance and extraction cost move together rather than trading off against each other. On the 4 tasks whose wording invites a violation, unconstrained (baseline) resisted 0; compliance-aware (ours) resisted 4 of 4 -- it reads the purpose policy, not the prose._

Source: 50 records/layer x 5 layers, seed 42. 8 extraction tasks, identical DPDP rule set for every technique. Generated 2026-09-16 in 55 ms (wall-clock, hardware-dependent).

| Technique | Compliance score | Rules passed | DM-01 | LB-01 | SL-01 | SS-01 | PL-01 | NT-01 | AC-01 |
|---|---|---|---|---|---|---|---|---|---|
| compliance-aware (ours) | 1.000 | 7/7 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| unconstrained (baseline) | 0.136 | 0/7 | 0.67 | 0.00 | 0.00 | 0.28 | 0.00 | 0.00 | 0.00 |

**Declared versus demonstrable**

Every technique is told the deployment's capability register -- the safeguards, the deletion mechanism, the notice, the accountable party that actually exist, each with an identifier. A declared control that does not cite one is *unsubstantiated*. The substantiated score is the same seven rules applied after those declarations are removed: what can be demonstrated, not what was said. *Traps* are tasks whose wording invites a violation the purpose does not permit; *held* means nothing out of scope was pulled, no onward use was declared and retention stayed within the ceiling.

| Technique | Declared score | Substantiated score | Veracity | Unsubstantiated declarations | Traps held |
|---|---|---|---|---|---|
| compliance-aware (ours) | 1.000 | 1.000 | 1.00 | 0 (—) | 4 / 4 |
| unconstrained (baseline) | 0.136 | 0.136 | 1.00 | 0 (—) | 0 / 4 |

**Compliance versus cost**

`excess ratio` is distinct fields pulled divided by the fields the task's purpose requires. It is a cost measure and a compliance measure at once: fields pulled beyond the purpose are precisely the overreach the data-minimisation rule penalises. `coverage` is the guard rail -- it stops a technique scoring well by pulling nothing. Both are deterministic and reproduce on any machine; wall-clock time is reported but is hardware-dependent. `stable runs` is how many of the repeated runs reproduced the first run's decision -- the same fields, the same manifest -- on identical input.

| Technique | Compliance | Excess ratio | Coverage | Distinct fields / needed | Fields pulled | Fetches | Pages loaded | Records | Wall-clock (ms) | Stable runs |
|---|---|---|---|---|---|---|---|---|---|---|
| compliance-aware (ours) | 1.000 | 1.00 | 1.00 | 35 / 35 | 1750 | 14 | n/a | 700 | 1.9 | 5 / 5 |
| unconstrained (baseline) | 0.136 | 7.09 | 1.00 | 248 / 35 | 12400 | 40 | n/a | 2000 | 7.2 | 5 / 5 |

**Per task**

| Task | compliance-aware | unconstrained |
|---|---|---|
| `patient-summary` | 1.000 | 0.131 |
| `ward-census` | 1.000 | 0.131 |
| `medication-review` | 1.000 | 0.131 |
| `appointment-reminder` | 1.000 | 0.143 |
| `claim-reconciliation` | 1.000 | 0.143 |
| `desk-registration` | 1.000 | 0.143 |
| `ward-summary-registry` | 1.000 | 0.131 |
| `consultant-file` | 1.000 | 0.131 |

**What each task needs**

- `patient-summary` (*care_coordination*): mrn, date_of_birth, sex @ patient_administration; primary_diagnosis, medication, allergy @ clinical_ehr
- `ward-census` (*care_coordination*): mrn, admission_ward, admission_datetime @ patient_administration; encounter_datetime @ clinical_ehr
- `medication-review` (*care_coordination*): mrn, date_of_birth @ patient_administration; primary_diagnosis, medication, allergy @ clinical_ehr
- `appointment-reminder` (*patient_registration*): mrn, full_name, phone, admission_datetime @ patient_administration
- `claim-reconciliation` (*billing_settlement*): mrn, full_name @ patient_administration; invoice_id, billed_amount, payer_name @ administrative_financial
- `desk-registration` (*patient_registration*): mrn, full_name, date_of_birth, phone @ patient_administration
- `ward-summary-registry` (*care_coordination*): mrn, date_of_birth @ patient_administration; primary_diagnosis, medication @ clinical_ehr
- `consultant-file` (*care_coordination*): mrn @ patient_administration; primary_diagnosis, allergy @ clinical_ehr

**What each technique pulled** (total over the 8-task workload)

- **compliance-aware** — 700 records across 3 layer(s); records carrying each category: administrative (150), clinical (200), direct_identifier (400), financial (50), quasi_identifier (200); out-of-scope: none
- **unconstrained** — 2000 records across 5 layer(s); records carrying each category: administrative (1600), clinical (800), contact (400), direct_identifier (800), financial (400), quasi_identifier (400); out-of-scope: clinical, contact, financial, quasi_identifier

**Rules** (each scores 0–1 per run; the table shows the mean over tasks)

- `DM-01` — Data minimisation
- `LB-01` — Lawful basis for processing
- `SL-01` — Storage limitation
- `SS-01` — Security safeguards
- `PL-01` — Purpose limitation
- `NT-01` — Transparency / notice
- `AC-01` — Accountability