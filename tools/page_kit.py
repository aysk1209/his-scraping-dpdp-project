"""Shared by the demo builders: one look, one data block, and one portal that holds them all.

Every demo is built as its own self-contained page (``tools/*_page.html`` with
``tools/page_base.css`` and ``tools/page_base.js`` inlined), but none of them is
published on its own any more. The builders write their pages as *parts* into a
git-ignored staging folder, and ``tools/build_review_pages.py`` assembles the
parts into a single file, ``docs/review/portal.html``: a slim shell with one tab
per demo, each demo embedded whole and loaded into its own frame on first open,
so no demo's script or ids can collide with another's. One file opens by
double-click, offline.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE_CSS = ROOT / "tools" / "page_base.css"
BASE_JS = ROOT / "tools" / "page_base.js"
REVIEW_DIR = ROOT / "docs" / "review"
PARTS_DIR = ROOT / "build" / "review-parts"            # git-ignored staging
PORTAL = REVIEW_DIR / "portal.html"
SHELL = ROOT / "tools" / "portal_shell.html"

# The portal's tabs, in the order the review shows them: key, label.
TABS = [
    ("index", "Overview"),
    ("portal", "Portal run"),
    ("dataset", "Dataset"),
    ("real", "Real data"),
    ("journey", "Journey"),
    ("assistant", "Assistant"),
    ("update", "HIS update"),
    ("rights", "Patient rights"),
    ("rules", "Rules vs AI"),
]


def part_path(key: str) -> Path:
    return PARTS_DIR / f"{key}.html"


def render(template: Path, data: dict | None, *, current: str = "", out: Path | None = None) -> str:
    """The template with the base stylesheet, the base script and the data block filled in."""

    html = template.read_text(encoding="utf-8")
    html = html.replace("/*__BASE__*/", BASE_CSS.read_text(encoding="utf-8"))
    html = html.replace("/*__KIT__*/", BASE_JS.read_text(encoding="utf-8"))
    html = html.replace("<!--__NAV__-->", "")             # the portal's tab bar is the navigation
    if data is not None:
        payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
        html = html.replace("/*__DATA__*/null", payload)
    return html


def write(out: Path, html: str) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return out


# Appended to every part inside the portal: the part's own toolbar is hidden (the
# shell has one), the shell's theme and text size are followed, and a tile marked
# data-open asks the shell to switch tabs.
BRIDGE = """
<style>.tools,.sitenav{display:none!important}</style>
<script>(()=>{const r=document.documentElement;
addEventListener("message",(e)=>{const m=e.data||{};if(m.type!=="portal-settings")return;
if(m.theme)r.dataset.theme=m.theme;else delete r.dataset.theme;r.classList.toggle("big",!!m.big);});
document.addEventListener("click",(e)=>{const a=e.target.closest("[data-open]");if(!a)return;
e.preventDefault();parent.postMessage({type:"portal-open",key:a.dataset.open},"*");});
parent.postMessage({type:"portal-ready"},"*");})();</script>
"""

_PARTS = re.compile(r'<script id="parts" type="application/json">(.*?)</script>', re.S)


def assemble(parts: dict[str, str]) -> str:
    """The one portal file: the shell, and every part embedded as data."""

    tabs = [{"key": k, "label": label} for k, label in TABS if k in parts]
    payload = {k: parts[k] + BRIDGE for k, _ in TABS if k in parts}
    # No "<" survives inside the script element, so nothing in a part can end it early.
    data = json.dumps({"tabs": tabs, "parts": payload}, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    html = render(SHELL, None)
    return html.replace("/*__PARTS__*/null", data)


def parts_in(portal: Path = PORTAL) -> dict[str, str]:
    """The parts a previously built portal carries, without their bridge -- for carrying over a
    demo this machine cannot rebuild (no browser, no public sample, no real export)."""

    if not portal.exists():
        return {}
    m = _PARTS.search(portal.read_text(encoding="utf-8"))
    if not m:
        return {}
    parts = json.loads(m.group(1))["parts"]
    return {k: v[: -len(BRIDGE)] if v.endswith(BRIDGE) else v for k, v in parts.items()}


def part_data(html: str) -> dict:
    """The data block of one part, as its builder embedded it."""

    m = re.search(r'<script id="data" type="application/json">(.*?)</script>', html, re.S)
    return json.loads(m.group(1).replace("<\\/", "</")) if m else {}
