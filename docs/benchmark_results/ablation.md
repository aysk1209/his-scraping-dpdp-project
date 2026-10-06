### Ablation — what each design choice buys

Ours with one design choice switched off at a time; eight tasks in memory, the same seven rules. *Leaked* is the export audit on the patient summary: raw identifiers found in the export.

| Variant | Serves | Compliance | Excess | Record excess | Traps held | Leaked | Rules below 1.00 |
|---|---|---|---|---|---|---|---|
| **compliance-aware (ours)** | all five | 1.000 | 1.00 | 1.00 | 4/4 | 0/1 | none |
| ours without scope | data minimisation (records) | 0.948 | 1.00 | 50.00 | 0/4 | 0/50 | DM-01 0.63 |
| ours without field list | data minimisation (fields) | 0.988 | 3.43 | 1.00 | 1/4 | 0/3 | DM-01 0.91 |
| ours without manifest | lawful basis, notice, accountability | 0.690 | 1.00 | 1.00 | 4/4 | 0/1 | NT-01 0.00, AC-01 0.33, LB-01 0.50 |
| ours without retention | storage limitation | 0.857 | 1.00 | 1.00 | 4/4 | 0/1 | SL-01 0.00 |
| ours without pseudonymise | security safeguards | 0.978 | 1.00 | 1.00 | 4/4 | 1/1 | SS-01 0.84 |
| unconstrained (baseline) | -- | 0.100 | 7.77 | 136.36 | 0/4 | 150/150 | LB-01 0.00, SL-01 0.00, PL-01 0.00, NT-01 0.00, AC-01 0.00, SS-01 0.28, DM-01 0.42 |
