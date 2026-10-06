### Scale — cost as the portal grows

The four-task portal workload, 10 records per page, ours against the baseline. Wall-clock is hardware-dependent; page loads are not.

| Records per module | Ours: page loads | Baseline: page loads | Ours: s | Baseline: s | Ours: score | Baseline: score | Baseline: records read ÷ needed |
|---|---|---|---|---|---|---|---|
| 20 | 32 | 440 | 6.2 | 68.3 | 1.000 | 0.114 | 50.0× |
| 40 | 58 | 880 | 11.9 | 150.6 | 1.000 | 0.114 | 100.0× |
| 80 | 110 | 1760 | 23.5 | 198.3 | 1.000 | 0.114 | 200.0× |
| 160 | 214 | 3520 | 40.1 | 515.2 | 1.000 | 0.113 | 400.0× |
