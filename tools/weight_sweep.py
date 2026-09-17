"""Does the ranking depend on how the seven rules are weighted? Check, don't assert.

    python tools/weight_sweep.py                       # docs/benchmark_results/benchmark.json
    python tools/weight_sweep.py path/to/benchmark.json

The compliance score is the weighted mean of seven per-rule scores, and every
rule weighs 1.0 by default. A reader may ask whether a different weighting
would reorder the techniques. This re-scores each technique's per-rule means
under a family of weightings -- equal; each rule doubled in turn; each rule
dropped in turn; a minimisation-and-purpose-heavy scheme; a paperwork-heavy
scheme -- and reports the ranking under each. It writes a Markdown table for
the report beside the benchmark artefacts.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / "docs" / "benchmark_results" / "benchmark.json"
OUT = ROOT / "docs" / "benchmark_results" / "weight-sweep.md"


def schemes(rule_ids: list[str]) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {"equal": {r: 1.0 for r in rule_ids}}
    for r in rule_ids:
        out[f"{r} x2"] = {q: (2.0 if q == r else 1.0) for q in rule_ids}
    for r in rule_ids:
        out[f"drop {r}"] = {q: (0.0 if q == r else 1.0) for q in rule_ids}
    out["minimisation + purpose x3"] = {q: (3.0 if q in ("DM-01", "PL-01") else 1.0) for q in rule_ids}
    out["paperwork x3 (LB, NT, AC)"] = {q: (3.0 if q in ("LB-01", "NT-01", "AC-01") else 1.0) for q in rule_ids}
    out["safeguards + storage x3"] = {q: (3.0 if q in ("SS-01", "SL-01") else 1.0) for q in rule_ids}
    return out


def weighted(per_rule: dict[str, float | None], weights: dict[str, float]) -> float:
    num = den = 0.0
    for rule, w in weights.items():
        v = per_rule.get(rule)
        if v is None or w == 0:
            continue
        num += w * v
        den += w
    return round(num / den, 3) if den else 0.0


def sweep(data: dict) -> tuple[list[str], list[list[str]], bool]:
    rule_ids = data["rule_ids"]
    techs = [(s["short"], s["per_rule_mean"]) for s in data["scores"]]
    baseline_order = [t for t, _ in techs]           # the committed ranking (sorted by equal weights)
    rows: list[list[str]] = []
    stable = True
    for name, weights in schemes(rule_ids).items():
        scored = sorted(((weighted(pr, weights), short) for short, pr in techs), reverse=True)
        order = [short for _, short in scored]
        same = order == baseline_order
        # A swap between techniques whose scores sit within 0.01 of each other is
        # a tie changing sides, not a reordering; anything wider is reported as one.
        verdict = "same"
        if not same:
            by_short = {short: score for score, short in scored}
            swapped = [t for t, u in zip(order, baseline_order) if t != u]
            gap = max(by_short[t] for t in swapped) - min(by_short[t] for t in swapped)
            verdict = f"tie swap (within {gap:.3f})" if gap < 0.01 else "**reordered**"
            stable = stable and gap < 0.01
        rows.append([name, " > ".join(f"{short} {score:.3f}" for score, short in scored), verdict])
    return baseline_order, rows, stable


def render(data: dict, order: list[str], rows: list[list[str]], stable: bool, source: Path) -> str:
    lines = [
        "### Rule-weight sensitivity",
        "",
        f"Re-scored from `{source.name}` (generated {data['generated_at'][:10]}): each technique's "
        "per-rule mean scores under alternative weightings of the seven rules. The committed score "
        "weighs every rule 1.0.",
        "",
        f"Ranking under equal weights: **{' > '.join(order)}**. "
        + ("**No weighting in the family reorders it** (a swap between techniques within 0.01 of each "
           "other is a tie changing sides, and is marked as such)." if stable else "Some weightings reorder it -- see below."),
        "",
        "| Weighting | Scores, ranked | Ranking |",
        "|---|---|---|",
    ]
    lines += [f"| {a} | {b} | {c} |" for a, b, c in rows]
    return "\n".join(lines) + "\n"


def main() -> None:
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT
    data = json.loads(source.read_text(encoding="utf-8"))
    if len(sys.argv) > 2:
        data["generated_at"] = sys.argv[2]            # a label for the source, e.g. a recording date
    order, rows, stable = sweep(data)
    text = render(data, order, rows, stable, source)
    OUT.write_text(text, encoding="utf-8")
    print(text)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
