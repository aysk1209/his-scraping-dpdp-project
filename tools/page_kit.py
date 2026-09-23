"""Shared by the demo-page builders: one look, one navigation bar, one data block.

Every page stays a single self-contained file -- it opens by double-click, with
no network -- so the shared stylesheet (``tools/page_base.css``) is inlined at
build time rather than linked, and the navigation bar's links are computed
relative to wherever the page is written.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE_CSS = ROOT / "tools" / "page_base.css"
REVIEW_DIR = ROOT / "docs" / "review"

# The demo pages, in the order the Review-II flow shows them.
PAGES = [
    ("index", REVIEW_DIR / "index.html", "All demos"),
    ("portal", REVIEW_DIR / "portal-run.html", "Portal run"),
    ("dataset", REVIEW_DIR / "dataset-walkthrough.html", "Dataset"),
    ("assistant", REVIEW_DIR / "assistant.html", "Assistant"),
    ("rules", ROOT / "docs" / "benchmark_results" / "rules-vs-just-ai.html", "Rules vs just AI"),
]


def nav_html(current: str, out: Path) -> str:
    links = []
    for key, path, label in PAGES:
        try:
            href = Path(os.path.relpath(path, out.parent)).as_posix()
        except ValueError:                   # another drive (Windows): no relative path exists
            href = path.resolve().as_uri()
        here = ' aria-current="page"' if key == current else ""
        links.append(f'<a href="{href}"{here}>{label}</a>')
    return f'<nav class="sitenav" aria-label="Demo pages">{"".join(links)}</nav>'


def render(template: Path, data: dict | None, *, current: str, out: Path) -> str:
    """The template with the base stylesheet, the navigation bar and the data block filled in."""

    html = template.read_text(encoding="utf-8")
    html = html.replace("/*__BASE__*/", BASE_CSS.read_text(encoding="utf-8"))
    html = html.replace("<!--__NAV__-->", nav_html(current, out))
    if data is not None:
        payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
        html = html.replace("/*__DATA__*/null", payload)
    return html


def write(out: Path, html: str) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return out
