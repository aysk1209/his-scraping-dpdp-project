"""Ablation: what each design choice of our technique buys, one switched off at a time.

    python scripts/run_ablation.py

Our technique is five choices -- scope a single-patient task to that patient,
take the fields from the purpose's necessary list, declare the manifest from
the capability register, declare a retention within the purpose's ceiling, and
pseudonymise identifiers on export. Each variant below lacks exactly one; the
eight benchmark tasks, the seven rules and the meter are the same for all.

Read the table by row: the drop from ours is what that choice was worth, and
the column it lands in says which part of the law it serves. The last column
is the export audit on the patient summary -- raw identifiers found in what
would leave the hospital.

Writes ``docs/benchmark_results/ablation.{json,md}``.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import _present as present                                                       # noqa: E402
from compliance.audit import AuditLog                                            # noqa: E402
from compliance.benchmark import bind_subject, run_benchmark                     # noqa: E402
from extraction.adapters.mock_his import MockHISDataSource                       # noqa: E402
from extraction.techniques.compliant import ABLATIONS, CompliantExtractionTechnique   # noqa: E402
from extraction.techniques.unconstrained import UnconstrainedExtractionTechnique  # noqa: E402
from interop.normalise import audit, normalise                                   # noqa: E402
from run_benchmark import TASKS                                                  # noqa: E402

OUT = ROOT / "docs" / "benchmark_results"
SERVES = {
    "scope": "data minimisation (records)", "field_list": "data minimisation (fields)",
    "manifest": "lawful basis, notice, accountability", "retention": "storage limitation",
    "pseudonymise": "security safeguards",
}


def main() -> int:
    print(present.banner("Ablation: what each of our design choices buys"))
    source = MockHISDataSource(records_per_layer=50, seed=42)
    tasks = bind_subject(TASKS, source)
    techniques = [CompliantExtractionTechnique()] + [CompliantExtractionTechnique(without=a) for a in ABLATIONS] \
        + [UnconstrainedExtractionTechnique()]
    with tempfile.TemporaryDirectory() as tmp:
        result = run_benchmark(techniques, tasks, source, dataset_note="ablation, in memory",
                               audit=AuditLog(Path(tmp) / "audit.jsonl"))

    summary = next(t for t in tasks if t.task_id == "patient-summary")
    rows = []
    by_name = {s.technique: s for s in result.scores}
    for technique in techniques:
        s = by_name[technique.name]
        out = technique.extract(source, summary)
        leak = audit(out, normalise(out))
        without = getattr(technique, "without", None)
        lost = sorted((k for k, v in s.per_rule_mean.items() if v is not None and v < 1.0),
                      key=lambda k: s.per_rule_mean[k])
        rows.append({
            "technique": technique.name, "without": without,
            "serves": SERVES.get(without, "" if technique.name.startswith("compliance") else "--"),
            "score": round(s.mean_compliance_score, 3),
            "rules_lost": {k: round(s.per_rule_mean[k], 2) for k in lost},
            "excess": round(s.cost.excess_ratio, 2), "record_excess": s.cost.record_excess,
            "coverage": round(s.cost.coverage, 2),
            "traps": f"{s.traps_resisted}/{s.traps}",
            "leaked": f"{leak.leaked}/{leak.identifier_values}",
        })

    print(f"  {'variant':<34} {'score':>6}  {'excess':>6} {'rec.exc':>7} {'traps':>6} {'leaked':>7}  rules below 1.00")
    print("  " + "-" * 110)
    for r in rows:
        rx = "-" if r["record_excess"] is None else f"{r['record_excess']:.2f}"
        lost = ", ".join(f"{k} {v:.2f}" for k, v in r["rules_lost"].items()) or "none"
        print(f"  {r['technique']:<34} {r['score']:>6.3f}  {r['excess']:>6.2f} {rx:>7} {r['traps']:>6} {r['leaked']:>7}  {lost}")
    print()
    print("  Each design choice carries a different part of the law: switch one off and the rule that")
    print("  serves it falls, and only that rule. No single choice explains the gap to the baseline;")
    print("  together they close it.")

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "ablation.json").write_text(json.dumps({"rows": rows}, indent=2), encoding="utf-8")
    md = ["### Ablation — what each design choice buys", "",
          "Ours with one design choice switched off at a time; eight tasks in memory, the same seven rules. "
          "*Leaked* is the export audit on the patient summary: raw identifiers found in the export.", "",
          "| Variant | Serves | Compliance | Excess | Record excess | Traps held | Leaked | Rules below 1.00 |",
          "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        rx = "—" if r["record_excess"] is None else f"{r['record_excess']:.2f}"
        lost = ", ".join(f"{k} {v:.2f}" for k, v in r["rules_lost"].items()) or "none"
        name = f"**{r['technique']}**" if r["without"] is None and r["technique"].startswith("compliance") else r["technique"]
        md.append(f"| {name} | {r['serves'] or 'all five'} | {r['score']:.3f} | {r['excess']:.2f} | {rx} | "
                  f"{r['traps']} | {r['leaked']} | {lost} |")
    (OUT / "ablation.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print()
    print(present.wrote(OUT / "ablation.md"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
