### Compliance benchmark

_compliance-aware (ours) scores 1.000; unconstrained (baseline) scores 0.131 on the same 7 rules -- a 0.869 gap that is purely a compliance difference, not coverage or speed._

Techniques scored against 2 task(s): `patient-summary`, `ward-census`. Identical DPDP rule set for every technique. Generated 2026-08-29.

| Technique | Compliance score | Pass rate | DM-01 | LB-01 | SL-01 | SS-01 | PL-01 | NT-01 | AC-01 |
|---|---|---|---|---|---|---|---|---|---|
| compliance-aware (ours) | 1.000 | 100% | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| minimising, undocumented | 0.500 | 29% | 1.00 | 0.50 | 0.50 | 0.50 | 1.00 | 0.00 | 0.00 |
| unconstrained (baseline) | 0.131 | 0% | 0.67 | 0.00 | 0.00 | 0.25 | 0.00 | 0.00 | 0.00 |

**Rules**

- `DM-01` — Data minimisation
- `LB-01` — Lawful basis for processing
- `SL-01` — Storage limitation
- `SS-01` — Security safeguards
- `PL-01` — Purpose limitation
- `NT-01` — Transparency / notice
- `AC-01` — Accountability