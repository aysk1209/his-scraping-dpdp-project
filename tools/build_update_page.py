"""Build the HIS-update page: a vendor release, and what it did to the assistant and the scraper.

    python tools/build_update_page.py

The fixture portal is crawled as every benchmark crawls it (layout v1), then as
a simulated vendor release (layout v2) with the hospital's alias file, then
again after a person confirms the two proposals the comparison makes. Every
one of the assistant's tasks is placed on all three crawls; the page shows what
changed, each task before and after, the two steps withheld and restored, and
the scraper's benchmark on both layouts (``benchmark-portal.json`` and
``benchmark-portal-v2.json``, from ``scripts/run_pipeline.py [--layout v2]``).

Nothing here is typed by hand: every sentence on the page about a change comes
from ``agent.drift``, and every step from ``agent.guidance``. No patient value is
on the page -- the steps carry the registry's own example inputs.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from agent import REGISTRY, ScreenMap, StaffRole, capabilities, compare        # noqa: E402
from agent.guidance import build_guidance                                      # noqa: E402
from agent.drift import _successors                                            # noqa: E402
from tools.page_kit import REVIEW_DIR, render, write, part_path   # noqa: E402

TEMPLATE = ROOT / "tools" / "update_page.html"
DEFAULT_OUT = part_path("update")
RESULTS = ROOT / "docs" / "benchmark_results"


def _steps(spec, screens: ScreenMap) -> list[dict]:
    role = next(r for r in StaffRole if spec.permitted_for(r))
    g = build_guidance(role, spec, {s.name: s.example for s in spec.inputs}, screens)
    return [{"text": s.text, "where": s.where or "", "withheld": s.withheld or ""} for s in g.steps]


def _scraper() -> dict:
    def load(name):
        path = RESULTS / f"{name}.json"
        return {s["short"]: s for s in json.loads(path.read_text(encoding="utf-8"))["scores"]} if path.exists() else {}

    v1, v2 = load("benchmark-portal"), load("benchmark-portal-v2")
    rows = []
    for short, a in v1.items():
        b = v2.get(short)
        if b is None:
            continue
        same = (round(a["mean_compliance_score"], 4) == round(b["mean_compliance_score"], 4)
                and a["cost"]["coverage"] == b["cost"]["coverage"]
                and a["traps_resisted"] == b["traps_resisted"]
                and a["cost"]["distinct_fields"] == b["cost"]["distinct_fields"])
        kind = "ours" if short == "compliance-aware" else "baseline" if short == "unconstrained" else "agent"
        rows.append({"name": a["technique"], "kind": kind, "briefing": a.get("briefing") or "",
                     "score": [a["mean_compliance_score"], b["mean_compliance_score"]],
                     "coverage": [a["cost"]["coverage"], b["cost"]["coverage"]],
                     "traps": [f"{a['traps_resisted']}/{a['traps']}", f"{b['traps_resisted']}/{b['traps']}"],
                     "pages": [a["cost"]["page_loads"], b["cost"]["page_loads"]], "same": same})
    return {"rows": rows, "available": bool(v2)}


def _release(before: ScreenMap, after: ScreenMap, changes) -> list[dict]:
    """The release as rows: each old module, the module(s) now holding its content, and every
    change (field, button, unmapped) drift tagged to either side -- matched by content, as
    ``agent.drift`` matches them, so the picture and the sentences cannot disagree."""

    succ, _ = _successors(before, after)
    rows = []
    for o in before.modules or []:
        news = succ[o.title]
        names = {o.title, *(n.title for n in news)}
        # Tagged by drift, or naming the module in its own words ("... (Front Office, record page).").
        mine = [c for c in changes.changes if c.kind != "module"
                and (c.modules & names or any(name in c.text for name in names))]
        kind = ("gone" if not news else "split" if len(news) > 1
                else "renamed" if news[0].title != o.title else "moved" if news[0].path != o.path else "same")
        rows.append({
            "old": {"title": o.title, "path": o.path},
            "new": [{"title": n.title, "path": n.path} for n in news],
            "kind": kind,
            "changes": [{"kind": c.kind, "text": c.text.replace(" -> ", " → ").replace("--", "—")} for c in mine],
        })
    placed = {c["text"] for r in rows for c in r["changes"]}
    rest = [c for c in changes.changes if c.kind != "module"
            and c.text.replace(" -> ", " → ").replace("--", "—") not in placed]
    if rest:
        rows.append({"old": None, "new": [], "kind": "across",
                     "changes": [{"kind": c.kind, "text": c.text.replace(" -> ", " → ").replace("--", "—")} for c in rest]})
    return rows


def build(out: Path = DEFAULT_OUT) -> dict:
    from scripts.check_ui_update import _crawl
    from tools.mock_portal.layouts import V2_FIELD_ALIASES

    before_nav = _crawl("v1", {})
    after_nav = _crawl("v2", V2_FIELD_ALIASES)
    before, after = ScreenMap.from_navigation(before_nav), ScreenMap.from_navigation(after_nav)
    changes = compare(before, after)
    fixed_nav = _crawl("v2", {**V2_FIELD_ALIASES, **changes.field_proposals})
    fixed = ScreenMap.from_navigation(fixed_nav, changes.control_proposals)
    rechecked = compare(before, fixed)

    status = {t.function_id: t for t in changes.impact}
    restored = {t.function_id: t.status for t in rechecked.impact}
    tasks = [{
        "id": spec.id, "label": spec.label, "group": spec.group,
        "status": status[spec.id].status, "reasons": status[spec.id].reasons,
        "fixed_status": restored[spec.id],
        "before": _steps(spec, before), "after": _steps(spec, after), "fixed": _steps(spec, fixed),
    } for spec in REGISTRY]

    roles = [{"id": r.value, "tasks": [s.id for s in capabilities(r)],
              "heard": changes.for_role(r)} for r in StaffRole]

    groups: dict[str, list[str]] = {}
    for c in changes.changes:
        groups.setdefault(c.kind, []).append(c.text)

    scraper = _scraper()
    counts = changes.by_status()
    data = {
        "release": _release(before, after, changes),
        "groups": groups,
        "proposals": {"fields": changes.field_proposals, "buttons": changes.control_proposals},
        "tasks": tasks, "roles": roles, "scraper": scraper,
        "meta": {
            "modules": len(groups.get("module", [])), "buttons": len(groups.get("button", [])),
            "fields": len(groups.get("field", [])),
            "reworded": len(counts["re-worded"]), "withheld": len(counts["withheld"]),
            "unchanged": len(counts["unchanged"]), "tasks": len(REGISTRY),
            "restored": sum(1 for t in rechecked.impact if t.status != "withheld"),
            "scraper_same": sum(1 for r in scraper["rows"] if r["same"]), "scraper_rows": len(scraper["rows"]),
        },
    }
    write(out, render(TEMPLATE, data, current="update", out=out))
    return data


def main() -> int:
    data = build()
    m = data["meta"]
    print(f"  wrote {DEFAULT_OUT}")
    print(f"  {m['tasks']} tasks: {m['reworded']} re-worded, {m['withheld']} withheld, {m['restored']} after the "
          f"two confirmations; scraper rows identical on every compliance figure: {m['scraper_same']}/{m['scraper_rows']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
