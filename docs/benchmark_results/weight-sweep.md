### Rule-weight sensitivity

Re-scored from `benchmark-prev.json` (generated 2026-09-17): each technique's per-rule mean scores under alternative weightings of the seven rules. The committed score weighs every rule 1.0.

Ranking under equal weights: **compliance-aware > gemini-informed > gemini-unaided > unconstrained**. **No weighting in the family reorders it** (a swap between techniques within 0.01 of each other is a tie changing sides, and is marked as such).

| Weighting | Scores, ranked | Ranking |
|---|---|---|
| equal | compliance-aware 1.000 > gemini-informed 0.948 > gemini-unaided 0.941 > unconstrained 0.135 | same |
| DM-01 x2 | compliance-aware 1.000 > gemini-informed 0.944 > gemini-unaided 0.937 > unconstrained 0.202 | same |
| LB-01 x2 | compliance-aware 1.000 > gemini-informed 0.954 > gemini-unaided 0.949 > unconstrained 0.119 | same |
| SL-01 x2 | compliance-aware 1.000 > gemini-informed 0.931 > gemini-unaided 0.928 > unconstrained 0.119 | same |
| SS-01 x2 | compliance-aware 1.000 > gemini-informed 0.954 > gemini-unaided 0.949 > unconstrained 0.154 | same |
| PL-01 x2 | compliance-aware 1.000 > gemini-informed 0.943 > gemini-unaided 0.929 > unconstrained 0.119 | same |
| NT-01 x2 | compliance-aware 1.000 > gemini-informed 0.954 > gemini-unaided 0.949 > unconstrained 0.119 | same |
| AC-01 x2 | compliance-aware 1.000 > gemini-informed 0.954 > gemini-unaided 0.949 > unconstrained 0.119 | same |
| drop DM-01 | compliance-aware 1.000 > gemini-informed 0.953 > gemini-unaided 0.947 > unconstrained 0.047 | same |
| drop LB-01 | compliance-aware 1.000 > gemini-informed 0.939 > gemini-unaided 0.932 > unconstrained 0.158 | same |
| drop SL-01 | compliance-aware 1.000 > gemini-informed 0.971 > gemini-unaided 0.959 > unconstrained 0.158 | same |
| drop SS-01 | compliance-aware 1.000 > gemini-informed 0.939 > gemini-unaided 0.932 > unconstrained 0.111 | same |
| drop PL-01 | compliance-aware 1.000 > gemini-unaided 0.958 > gemini-informed 0.955 > unconstrained 0.158 | tie swap (within 0.003) |
| drop NT-01 | compliance-aware 1.000 > gemini-informed 0.939 > gemini-unaided 0.932 > unconstrained 0.158 | same |
| drop AC-01 | compliance-aware 1.000 > gemini-informed 0.939 > gemini-unaided 0.932 > unconstrained 0.158 | same |
| minimisation + purpose x3 | compliance-aware 1.000 > gemini-informed 0.935 > gemini-unaided 0.918 > unconstrained 0.207 | same |
| paperwork x3 (LB, NT, AC) | compliance-aware 1.000 > gemini-informed 0.972 > gemini-unaided 0.968 > unconstrained 0.073 | same |
| safeguards + storage x3 | compliance-aware 1.000 > gemini-unaided 0.933 > gemini-informed 0.933 > unconstrained 0.137 | tie swap (within 0.000) |
