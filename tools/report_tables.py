"""Write the report's result tables from the tracked artefacts, in place.

    python tools/report_tables.py            # rewrite every marked table in docs/report/
    python tools/report_tables.py --check    # exit 1 if any table differs from the artefacts

A table in a chapter is a block between ``<!-- table:NAME -->`` and
``<!-- /table:NAME -->``; this script regenerates the block from
``docs/benchmark_results/*.json`` so the report cannot drift from the numbers it
reports. Run it after the benchmarks, as the demo page and the deck are.

    agents   one row per technique, each AI model at the told-the-policy briefing (in memory)
    rules    compliance per rule, every technique and briefing (in memory)
    cost     cost, veracity, traps and stability, in memory and on the portal
    public   the public export (Synthea), one row per model, with the coverage ceiling
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from compliance.benchmark import BenchmarkResult   # noqa: E402

RESULTS = ROOT / "docs" / "benchmark_results"
REPORT = ROOT / "docs" / "report"
BLOCK = re.compile(r"(<!-- table:(\w+) -->\n)(.*?)(<!-- /table:\2 -->)", re.S)


def _load(name: str) -> BenchmarkResult:
    return BenchmarkResult.model_validate(json.loads((RESULTS / f"{name}.json").read_text(encoding="utf-8")))


def _name(s) -> str:
    if s.short == "compliance-aware":
        return "compliance-aware (ours)"
    if s.short == "unconstrained":
        return "unconstrained (baseline)"
    label = {"policy": "told the policy", "informed": "told the Act", "unaided": "unaided"}[s.briefing]
    return f"{s.model}, {label}"


def _bold_ours(s, text: str) -> str:
    return f"**{text}**" if s.short == "compliance-aware" else text


def _stable(s) -> str:
    return f"{s.stable_runs} / {s.repeat_runs}" if s.repeat_runs else "— (1 run)"


def _rx(v) -> str:
    return "—" if v is None else (f"{v:.1f}" if v >= 10 else f"{v:.2f}")


def table_agents() -> str:
    r = _load("benchmark")
    rows = ["| Technique | Runs per task | Compliance | Trap runs held | Coverage | Excess | Record excess | Stable |",
            "|---|---|---|---|---|---|---|---|"]
    for s, flagged in r.by_model():
        rows.append(f"| {_name(s)}{' *' if flagged else ''} | {s.repeats} | {_bold_ours(s, f'{s.mean_compliance_score:.3f}')} "
                    f"| {_bold_ours(s, f'{s.traps_resisted} / {s.traps}')} | {s.cost.coverage:.2f} | "
                    f"{s.cost.excess_ratio:.2f} | {_rx(s.cost.record_excess)} | {_bold_ours(s, _stable(s))} |")
    return "\n".join(rows) + "\n"


def table_rules() -> str:
    r = _load("benchmark")
    head = "| Technique | Score | Rules passed | " + " | ".join(r.rule_ids) + " |"
    rows = [head, "|" + "---|" * (3 + len(r.rule_ids))]
    for s in r.scores:
        cells = " | ".join("n/a" if s.per_rule_mean.get(k) is None else f"{s.per_rule_mean[k]:.2f}" for k in r.rule_ids)
        rows.append(f"| {_name(s)} | {_bold_ours(s, f'{s.mean_compliance_score:.3f}')} | {s.rules_passed} | {cells} |")
    return "\n".join(rows) + "\n"


def table_cost() -> str:
    rows = ["| Source | Technique | Runs | Compliance | Substantiated | Veracity | Traps held (runs / tasks) | Coverage | "
            "Excess | Record excess | Distinct / needed | Page loads | Stable (repeats / tasks) |",
            "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for label, name in (("in memory", "benchmark"), ("portal", "benchmark-portal")):
        for s in _load(name).scores:
            c = s.cost
            traps = f"{s.traps_resisted} / {s.traps}" + (f" ({s.trap_tasks_held} / {s.trap_tasks})" if s.repeats > 1 else "")
            stable = f"{s.stable_runs} / {s.repeat_runs} ({s.stable_tasks} / {s.tasks})" if s.repeat_runs else "—"
            rows.append(f"| {label} | {_name(s)} | {s.repeats} | {_bold_ours(s, f'{s.mean_compliance_score:.3f}')} | "
                        f"{s.substantiated_score:.3f} | {'—' if s.veracity is None else f'{s.veracity:.2f}'} | {traps} | "
                        f"{c.coverage:.2f} | {c.excess_ratio:.2f} | {_rx(c.record_excess)} | "
                        f"{c.distinct_fields} / {c.needed_fields} | {'n/a' if c.page_loads is None else c.page_loads} | {stable} |")
    return "\n".join(rows) + "\n"


def table_public() -> str:
    r = _load("benchmark-public")
    rows = ["| Technique | Compliance | Coverage | Excess | Records read ÷ the patient's own | Trap held |",
            "|---|---|---|---|---|---|"]
    for s, flagged in r.by_model():
        rows.append(f"| {_name(s)}{' *' if flagged else ''} | {_bold_ours(s, f'{s.mean_compliance_score:.3f}')} | "
                    f"{s.cost.coverage:.2f} | {s.cost.excess_ratio:.2f} | {_rx(s.cost.record_excess)}× | "
                    f"{s.traps_resisted} / {s.traps} |")
    if r.coverage_needed:
        rows.append("")
        rows.append(f"Coverage ceiling, measured from the export: {r.coverage_reachable} of the {r.coverage_needed} "
                    f"fields the tasks need are obtainable; {r.coverage_needed - r.coverage_in_source} are not in the "
                    f"export and {r.coverage_in_source - r.coverage_reachable} are not in the records of the patient a "
                    f"single-patient task is about.")
    return "\n".join(rows) + "\n"


# --- appendices: the policy and vocabulary tables, verbatim from the code ----------


def table_mapping() -> str:
    """Appendix A: the verified section mapping, as kept in docs/compliance/dpdp-provision-map.md."""

    text = (ROOT / "docs" / "compliance" / "dpdp-provision-map.md").read_text(encoding="utf-8")
    section = text.split("## Section mapping", 1)[1].split("\n## ", 1)[0]
    lines = [l for l in section.splitlines() if l.startswith("|")]
    return "\n".join(lines) + "\n"


def table_catalogue() -> str:
    from data_synthetic.catalogue import FIELD_CATALOGUE
    rows = ["| Layer | Field | DPDP category |", "|---|---|---|"]
    for layer, fields in FIELD_CATALOGUE.items():
        for i, (name, cat) in enumerate(fields.items()):
            rows.append(f"| {layer.value if i == 0 else ''} | `{name}` | {cat.value.replace('_', ' ')} |")
    return "\n".join(rows) + "\n"


def table_policy() -> str:
    from compliance.policy import PURPOSE_POLICY
    rows = ["| Purpose | Categories permitted | Retention ceiling | Pseudonymised identifiers required | Basis relied on |",
            "|---|---|---|---|---|"]
    for purpose, pol in PURPOSE_POLICY.items():
        cats = ", ".join(sorted(c.value.replace("_", " ") for c in pol.allowed_categories))
        rows.append(f"| `{purpose.value}` | {cats} | {pol.max_retention_days} days | "
                    f"{'yes' if pol.requires_pseudonymised_identifiers else 'no'} | {pol.legitimate_use_note} |")
    return "\n".join(rows) + "\n"


def table_roles() -> str:
    from compliance.roles import ROLE_POLICY
    rows = ["| Role | Purposes | Artefacts handled | Derived scope (purposes ∩ artefacts) |", "|---|---|---|---|"]
    for role, pol in ROLE_POLICY.items():
        rows.append(f"| {role.value} | {', '.join(sorted(p.value for p in pol.purposes))} | "
                    f"{', '.join(f'`{a}`' for a in sorted(pol.artefacts))} | "
                    f"{', '.join(sorted(c.value.replace('_', ' ') for c in pol.allowed_categories()))} |")
    return "\n".join(rows) + "\n"


def table_artefacts() -> str:
    from compliance.roles import ARTEFACTS, ROLE_POLICY
    rows = ["| Artefact | Standard | Name | Layer | Categories carried | Granted to |", "|---|---|---|---|---|---|"]
    for key, art in sorted(ARTEFACTS.items()):
        who = [r.value for r, pol in ROLE_POLICY.items() if key in pol.artefacts] or ["no role"]
        rows.append(f"| `{key}` | {art.standard.value} | {art.name} | {art.layer.value} | "
                    f"{', '.join(sorted(c.value.replace('_', ' ') for c in art.categories))} | {', '.join(who)} |")
    return "\n".join(rows) + "\n"


def table_functions() -> str:
    from agent.functions import REGISTRY
    from compliance.roles import StaffRole
    rows = ["| Function | Purpose | Artefacts | Inputs asked for | May be used by |", "|---|---|---|---|---|"]
    for spec in REGISTRY:
        who = [r.value for r in StaffRole if spec.permitted_for(r)] or ["no role"]
        rows.append(f"| {spec.label} | {spec.purpose.value} | {', '.join(f'`{a}`' for a in sorted(spec.artefacts))} | "
                    f"{', '.join(i.name for i in spec.inputs)} | {', '.join(who)} |")
    return "\n".join(rows) + "\n"


TABLES = {"agents": table_agents, "rules": table_rules, "cost": table_cost, "public": table_public,
          "mapping": table_mapping, "catalogue": table_catalogue, "policy": table_policy, "roles": table_roles,
          "artefacts": table_artefacts, "functions": table_functions}


def rewrite(check: bool = False) -> list[str]:
    changed = []
    for path in [*sorted(REPORT.glob("*.md")), ROOT / "README.md"]:
        text = path.read_text(encoding="utf-8")

        def fill(m):
            body = TABLES[m.group(2)]()
            return m.group(1) + body + m.group(4)

        new = BLOCK.sub(fill, text)
        if new != text:
            changed.append(path.name)
            if not check:
                path.write_text(new, encoding="utf-8")
    return changed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    changed = rewrite(check=args.check)
    if args.check:
        print("report tables " + ("differ from the artefacts: " + ", ".join(changed) if changed else "match the artefacts"))
        return 1 if changed else 0
    print("rewrote tables in: " + (", ".join(changed) or "nothing (already current)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
