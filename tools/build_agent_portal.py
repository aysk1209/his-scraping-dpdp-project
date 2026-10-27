"""The HIS Staff Assistant portal, ``docs/review/agent-portal.html``.

    python tools/build_agent_portal.py

The staff assistant (``src/agent/``) as its own portal. A member of staff puts on a
badge (reception, nurse, administrator) and asks for an HIS task in their own
words, or plays that badge's tour; beside the conversation the page shows the
request walking its route: understood, the DPDP check for that badge (before a
single detail is asked), the details, the department, and the screen, with a
replica of the HIS screen lighting the column and the button each step uses.

Everything comes from the assistant itself. The engine's tables, every badge's
gate and every recorded Python conversation come from
``tools/build_assistant_page.collect`` (the page's port of the engine replays them
all on open and switches typing off on any difference); the steps' placements and
the screens come from ``agent.ui.ScreenMap`` over the crawler's committed
``navigation-map.json``. The tours are recorded Python conversations, so they play
even where typing is off. Inputs are the registry's own examples; the replica
carries no record value, and the builder audits its own output with the Portal's
audit before writing.
"""

from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "src", ROOT / "scripts"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from agent.functions import REGISTRY                                         # noqa: E402
from agent.guidance import build_guidance, place_steps                       # noqa: E402
from agent.ui import ScreenMap                                               # noqa: E402
from compliance.roles import StaffRole                                       # noqa: E402
from extraction.tier2.navigation import NavigationMap                        # noqa: E402
from tools import build_assistant_page as assistant                          # noqa: E402
from tools import build_portal_app as v1                                     # noqa: E402
from tools.page_kit import REVIEW_DIR, write                                 # noqa: E402

HERE = ROOT / "tools" / "agent_portal"
OUT = REVIEW_DIR / "agent-portal.html"
SHELL = HERE / "agent.html"
CSS = HERE / "agent.css"
SCRIPTS = ["engine.js", "agent.js"]
FONT = HERE / "fonts" / "Inter-latin-wght.woff2"       # Portal v2's face (user, 2026-10-23)

# One tour per badge (user, 2026-10-16), each a recorded Python conversation. A tour
# opens on a request the badge may not make for a reason other than purpose (user,
# 2026-10-28), refused before the record number typed with it is read: reception on
# SS-01 (an artefact it does not handle), the administrator on DM-01 (the diagnosis is
# not necessary for billing). The nurse has no such refusal: every request the gate
# refuses a nurse fails on purpose first, so the nurse's tour shows the answer that
# does not fit instead.
TOURS = [
    ("reception", "Register a new patient",
     ["allocate a bed for MRN2867825",
      "register a new patient", "Priya Raman", "1988-03-14", "+91-9800000012"]),
    ("nurse", "Record a patient's vital signs",
     ["record obs for MRN2867825", "one twenty", "128/82", "76", "37.1"]),
    ("administrator", "Raise a bill",
     ["send the diagnosis for MRN2867825 to the insurer",
      "raise the bill", "MRN2867825", "ENC-20260912-07"]),
]
# A request each badge may not make, offered beside its common tasks so the staff-only door is found.
OUTSIDE = {"reception": "view_diagnosis", "nurse": "generate_invoice", "administrator": "record_vitals"}
# The common tasks shown first for each badge.
COMMON = {
    "reception": ["register_patient", "check_in_arrival", "book_appointment", "verify_insurance"],
    "nurse": ["record_vitals", "view_medications", "view_diagnosis", "shift_handover"],
    "administrator": ["allocate_bed", "post_charges", "generate_invoice", "ward_census"],
}


def _screens(nav: ScreenMap) -> list[dict]:
    """Each module as the crawler found it: its columns and fields as headed on screen, its buttons."""

    return [{
        "title": m.title, "path": m.path, "layer": m.layer.value,
        "list": [{"field": f, "label": m.label(f)} for f in m.list_fields],
        "record": [{"field": f, "label": m.label(f)} for f in m.record_fields],
        "listButtons": list(m.list_actions.values()),
        "recordButtons": list(m.record_actions.values()),
    } for m in nav.modules]


def payload() -> dict:
    data = assistant.collect()
    nav_map = NavigationMap.model_validate_json(assistant.NAV_MAP.read_text(encoding="utf-8"))
    nav = ScreenMap.from_navigation(nav_map)
    spec_of = {s.id: s for s in REGISTRY}

    # Where every step happens: the module, the screen, the button and the fields, as the crawl has them.
    for f in data["functions"]:
        spec = spec_of[f["id"]]
        template = build_guidance(StaffRole.NURSE, spec, {s.name: "{" + s.name + "}" for s in spec.inputs}, nav)
        for step, tmpl, place in zip(f["steps"], template.steps, place_steps(spec, nav)):
            step["fields"] = list(tmpl.fields)
            step["place"] = None if place is None or place.withheld else {
                "module": place.module, "path": place.path, "screen": place.screen,
                "button": place.button.strip('"') if place.button else None,
                "labels": place.labels,
            }

    tours = []
    for role, title, turns in TOURS:
        played = assistant._play(StaffRole(role), turns, nav)
        tours.append({"role": role, "title": title, **played})
    data.update({
        "screens": _screens(nav),
        "tours": tours,
        "outside": OUTSIDE,
        "common": COMMON,
        "portalAsOf": nav_map.discovered_at.date().isoformat(),
    })
    data.pop("scenes", None)
    return data


def _secrets() -> set[str]:
    """Every identifier, contact detail and quasi-identifier the portal's own source holds."""

    from data_synthetic.catalogue import FIELD_CATALOGUE
    from extraction.adapters.mock_his import MockHISDataSource

    source = MockHISDataSource(records_per_layer=v1.RECORDS, seed=v1.SEED)
    cat = {l.value: {f: c.value for f, c in fields.items()} for l, fields in FIELD_CATALOGUE.items()}
    secrets: set[str] = set()
    for layer in source.layers():
        for r in source.fetch(layer):
            for f, v in r.items():
                if (cat[layer.value].get(f) in v1.DIRECT and f != "sex") or f == "insurance_policy_no":
                    secrets |= v1._variants(v)
    return secrets


def render(data: dict) -> str:
    html = SHELL.read_text(encoding="utf-8")
    font = base64.b64encode(FONT.read_bytes()).decode("ascii")
    css = CSS.read_text(encoding="utf-8").replace("/*__FONT__*/", f"url(data:font/woff2;base64,{font}) format('woff2')")
    html = html.replace("/*__CSS__*/", css)
    html = html.replace("/*__JS__*/", "\n".join((HERE / name).read_text(encoding="utf-8") for name in SCRIPTS))
    blob = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    return html.replace("/*__DATA__*/null", blob)


def build(out: Path = OUT) -> Path:
    data = payload()
    html = render(data)
    v1.check(html, _secrets())
    return write(out, html)


def main() -> int:
    out = build()
    size = out.stat().st_size / 1024
    print(f"  wrote {out.relative_to(ROOT)}  (the HIS Staff Assistant portal, {size:.0f} KB); audit: no raw identifier on the page")
    return 0


if __name__ == "__main__":
    sys.exit(main())
