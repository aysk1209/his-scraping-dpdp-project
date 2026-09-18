### Rule-weight sensitivity

Re-scored from `benchmark.json` (generated 2026-09-18): each technique's per-rule mean scores under alternative weightings of the seven rules. The committed score weighs every rule 1.0.

Ranking under equal weights: **compliance-aware > gemini-3.1-flash-lite-policy > gemini-3.1-flash-lite-informed > gemini-3.1-flash-lite-unaided > unconstrained**. **No weighting in the family reorders it** (a swap between techniques within 0.01 of each other is a tie changing sides, and is marked as such).

| Weighting | Scores, ranked | Ranking |
|---|---|---|
| equal | compliance-aware 1.000 > gemini-3.1-flash-lite-policy 0.984 > gemini-3.1-flash-lite-informed 0.948 > gemini-3.1-flash-lite-unaided 0.942 > unconstrained 0.100 | same |
| DM-01 x2 | compliance-aware 1.000 > gemini-3.1-flash-lite-policy 0.972 > gemini-3.1-flash-lite-informed 0.943 > gemini-3.1-flash-lite-unaided 0.937 > unconstrained 0.140 | same |
| LB-01 x2 | compliance-aware 1.000 > gemini-3.1-flash-lite-policy 0.986 > gemini-3.1-flash-lite-informed 0.955 > gemini-3.1-flash-lite-unaided 0.949 > unconstrained 0.087 | same |
| SL-01 x2 | compliance-aware 1.000 > gemini-3.1-flash-lite-policy 0.986 > gemini-3.1-flash-lite-informed 0.933 > gemini-3.1-flash-lite-unaided 0.922 > unconstrained 0.087 | same |
| SS-01 x2 | compliance-aware 1.000 > gemini-3.1-flash-lite-policy 0.986 > gemini-3.1-flash-lite-informed 0.955 > gemini-3.1-flash-lite-unaided 0.949 > unconstrained 0.123 | same |
| PL-01 x2 | compliance-aware 1.000 > gemini-3.1-flash-lite-policy 0.986 > gemini-3.1-flash-lite-informed 0.943 > gemini-3.1-flash-lite-unaided 0.937 > unconstrained 0.087 | same |
| NT-01 x2 | compliance-aware 1.000 > gemini-3.1-flash-lite-policy 0.986 > gemini-3.1-flash-lite-informed 0.955 > gemini-3.1-flash-lite-unaided 0.949 > unconstrained 0.087 | same |
| AC-01 x2 | compliance-aware 1.000 > gemini-3.1-flash-lite-policy 0.986 > gemini-3.1-flash-lite-informed 0.955 > gemini-3.1-flash-lite-unaided 0.949 > unconstrained 0.087 | same |
| drop DM-01 | gemini-3.1-flash-lite-policy 1.000 > compliance-aware 1.000 > gemini-3.1-flash-lite-informed 0.955 > gemini-3.1-flash-lite-unaided 0.949 > unconstrained 0.047 | tie swap (within 0.000) |
| drop LB-01 | compliance-aware 1.000 > gemini-3.1-flash-lite-policy 0.982 > gemini-3.1-flash-lite-informed 0.939 > gemini-3.1-flash-lite-unaided 0.932 > unconstrained 0.117 | same |
| drop SL-01 | compliance-aware 1.000 > gemini-3.1-flash-lite-policy 0.982 > gemini-3.1-flash-lite-informed 0.969 > gemini-3.1-flash-lite-unaided 0.968 > unconstrained 0.117 | same |
| drop SS-01 | compliance-aware 1.000 > gemini-3.1-flash-lite-policy 0.982 > gemini-3.1-flash-lite-informed 0.939 > gemini-3.1-flash-lite-unaided 0.932 > unconstrained 0.070 | same |
| drop PL-01 | compliance-aware 1.000 > gemini-3.1-flash-lite-policy 0.982 > gemini-3.1-flash-lite-informed 0.955 > gemini-3.1-flash-lite-unaided 0.948 > unconstrained 0.117 | same |
| drop NT-01 | compliance-aware 1.000 > gemini-3.1-flash-lite-policy 0.982 > gemini-3.1-flash-lite-informed 0.939 > gemini-3.1-flash-lite-unaided 0.932 > unconstrained 0.117 | same |
| drop AC-01 | compliance-aware 1.000 > gemini-3.1-flash-lite-policy 0.982 > gemini-3.1-flash-lite-informed 0.939 > gemini-3.1-flash-lite-unaided 0.932 > unconstrained 0.117 | same |
| minimisation + purpose x3 | compliance-aware 1.000 > gemini-3.1-flash-lite-policy 0.970 > gemini-3.1-flash-lite-informed 0.933 > gemini-3.1-flash-lite-unaided 0.928 > unconstrained 0.140 | same |
| paperwork x3 (LB, NT, AC) | compliance-aware 1.000 > gemini-3.1-flash-lite-policy 0.991 > gemini-3.1-flash-lite-informed 0.972 > gemini-3.1-flash-lite-unaided 0.969 > unconstrained 0.054 | same |
| safeguards + storage x3 | compliance-aware 1.000 > gemini-3.1-flash-lite-policy 0.990 > gemini-3.1-flash-lite-informed 0.935 > gemini-3.1-flash-lite-unaided 0.924 > unconstrained 0.115 | same |
