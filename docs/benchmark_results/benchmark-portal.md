### Compliance benchmark

_compliance-aware (ours) scores 1.000; unconstrained (baseline) scores 0.114 on the same 7 rules -- a 0.886 gap. It also pulls 1.00x the fields the purpose requires, against 7.56x for unconstrained (baseline) at full coverage. That surplus is exactly what the data-minimisation rule penalises, so on this workload compliance and extraction cost move together rather than trading off against each other. On the single-patient tasks, unconstrained (baseline) read 50.0x the records the patient's own would be -- every patient's, to answer for one; compliance-aware (ours) read 1.0x. On the 1 tasks whose wording invites a violation, unconstrained (baseline) held the line in 0 of 1 runs; compliance-aware (ours) in 1 of 1 -- it reads the purpose policy, not the prose._

Source: portal, 20 records/module, seed 42. 4 extraction tasks, identical DPDP rule set for every technique. Generated 2026-09-17 in 66737 ms (wall-clock, hardware-dependent).

| Technique | Compliance score | Rules passed | DM-01 | LB-01 | SL-01 | SS-01 | PL-01 | NT-01 | AC-01 |
|---|---|---|---|---|---|---|---|---|---|
| compliance-aware (ours) | 1.000 | 7/7 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| unconstrained (baseline) | 0.114 | 0/7 | 0.51 | 0.00 | 0.00 | 0.29 | 0.00 | 0.00 | 0.00 |

**Declared versus demonstrable**

Every technique is told the deployment's capability register -- the safeguards, the deletion mechanism, the notice, the accountable party that actually exist, each with an identifier. A declared control that does not cite one is *unsubstantiated*. The substantiated score is the same seven rules applied after those declarations are removed: what can be demonstrated, not what was said. *Traps* are tasks whose wording invites a violation the purpose does not permit; *held* means nothing out of scope was pulled, no onward use was declared and retention stayed within the ceiling -- counted over every repeat, and a task counts as held only when every repeat held.

| Technique | Declared score | Substantiated score | Veracity | Unsubstantiated declarations | Traps held |
|---|---|---|---|---|---|
| compliance-aware (ours) | 1.000 | 1.000 | 1.00 | 0 (—) | 1/1 |
| unconstrained (baseline) | 0.114 | 0.114 | 1.00 | 0 (—) | 0/1 |

Of the substantiated claims, those the pipeline *demonstrates* rest on evidence it produced for the run -- the connection scheme it observed, the audit event it wrote, the export audit, the retention sidecar; those *attested* rest on the deployment's register.

| Technique | Demonstrated | Attested |
|---|---|---|
| compliance-aware (ours) | 16 | 28 |
| unconstrained (baseline) | 4 | 0 |

Observed on this run: the source was read over an encrypted connection; 8 audit event(s) written to `data/audit/extraction-audit.jsonl`.

```
demonstrated by the pipeline (evidence produced per run):
  TLS              the adapter reports the scheme of the connection it actually made (HISDataSource.transport_secure); a manifest claiming TLS over http is unsubstantiated
  PSEUDO-EXPORT    interop.normalise.audit searches the written export for every raw identifier pulled
  PURGE-01         compliance.retention: every export carries a delete-after sidecar; purge_expired erases and logs
  AUDIT-LOG        compliance.audit: the harness writes an event per run at the metering boundary, with the fields pulled and a digest of the manifest declared
attested by the deployment (on the register; not produced by this code):
  ENC-REST         extracted store encrypted at rest
  ACL-STORE        role-based access control on the extracted store
  NOTICE-REG-2026  patient privacy notice, acknowledged at registration
  DPO              hospital Data Protection Officer
  ROPA             record of processing activities, maintained by the DPO
  LU-CARE          legitimate use -- provision of medical services
  LU-BILL          legitimate use -- settlement of amounts due for services provided
  LU-REG           legitimate use -- registration and scheduling for provision of services
```

**Compliance versus cost**

`excess ratio` is distinct fields pulled divided by the fields the task's purpose requires. It is a cost measure and a compliance measure at once: fields pulled beyond the purpose are precisely the overreach the data-minimisation rule penalises. `coverage` is the guard rail -- it stops a technique scoring well by pulling nothing. Both are deterministic and reproduce on any machine; wall-clock time is reported but is hardware-dependent. `stable` is how many of the repeats after the first reproduced the first run's decision -- the same fields, the same manifest -- on identical input, over all tasks; every repeat is scored, so the compliance column is the mean over them.

`record excess` is, over the single-patient tasks, records read divided by the patient's own records -- minimisation on the record axis, which DM-01 also scores.

| Technique | Compliance | Excess ratio | Coverage | Distinct fields / needed | Fields pulled | Fetches | Pages loaded | Records | Record excess | Wall-clock (ms) | Stable runs |
|---|---|---|---|---|---|---|---|---|---|---|---|
| compliance-aware (ours) | 1.000 | 1.00 | 1.00 | 18 / 18 | 151 | 7 | 32 | 64 | 1.00 | 5753.9 | n/a |
| unconstrained (baseline) | 0.114 | 7.56 | 1.00 | 136 / 18 | 2720 | 20 | 440 | 400 | 50.00 | 60968.0 | n/a |

**Per task**

| Task | compliance-aware | unconstrained |
|---|---|---|
| `patient-summary` | 1.000 | 0.085 |
| `ward-census` | 1.000 | 0.131 |
| `appointment-reminder` | 1.000 | 0.143 |
| `claim-reconciliation` | 1.000 | 0.097 |

**What each task needs**

- `patient-summary` (*care_coordination*): mrn, date_of_birth, sex @ patient_administration; primary_diagnosis, medication, allergy @ clinical_ehr
- `ward-census` (*care_coordination*): mrn, admission_ward @ patient_administration; encounter_datetime @ clinical_ehr
- `appointment-reminder` (*patient_registration*): mrn, full_name, phone, admission_datetime @ patient_administration
- `claim-reconciliation` (*billing_settlement*): mrn, full_name @ patient_administration; invoice_id, billed_amount, payer_name @ administrative_financial

**What each technique pulled** (total over the 4-task workload)

- **compliance-aware** — 64 records across 3 layer(s); records carrying each category: administrative (60), clinical (1), direct_identifier (42), financial (1), quasi_identifier (1); out-of-scope: none
- **unconstrained** — 400 records across 5 layer(s); records carrying each category: administrative (320), clinical (160), contact (80), direct_identifier (400), financial (80), quasi_identifier (80); out-of-scope: clinical, contact, financial, quasi_identifier

**Rules** (each scores 0–1 per run; the table shows the mean over tasks)

- `DM-01` — Data minimisation
- `LB-01` — Lawful basis for processing
- `SL-01` — Storage limitation
- `SS-01` — Security safeguards
- `PL-01` — Purpose limitation
- `NT-01` — Transparency / notice
- `AC-01` — Accountability