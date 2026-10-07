"""Photograph the demo pages in their most telling state, for the review deck.

    python tools/capture_demo_pages.py        # writes docs/review/img/*.png (needs Chromium)

Each demo is taken from the portal (``docs/review/portal.html``), written out
on its own to a temporary file, and opened in headless Chromium at a projector-like size,
driven into the moment the presenter points at -- the crawl finished, the
billing trap on one patient, the diagnosis followed into the trap, a refusal
with its three checks -- and captured.
The deck (``tools/build_review_deck.py``) places these on its demonstration
slide, so the pictures are there even if the room's browser is not. Rebuild
after ``tools/build_review_pages.py``.
"""

from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "docs" / "review"
OUT = REVIEW / "img"
VIEWPORT = {"width": 1366, "height": 900}

# name -> (portal tab, script run on it before capture, element to capture[, cut below the lowest of these])
SHOTS = {
    "portal-crawl": ("portal", """
        document.querySelector('#steps button[data-step="3"]').click();
        await new Promise(r => setTimeout(r, 500));
        document.querySelector('#speedseg button[data-v="3"]').click();
        document.getElementById('play').click();
        await new Promise(r => { const t = setInterval(() => { if (!document.getElementById('play').disabled) { clearInterval(t); r(); } }, 100); });
        document.querySelectorAll('.sq b.now').forEach(b => b.classList.remove('now'));
    """, "#lanes"),
    "dataset-patient": ("dataset", """
        document.querySelector('#steps button[data-step="3"]').click();
        document.querySelector('#taskseg button[data-t="claim-reconciliation"]').click();
    """, "#who", "#who .fchips"),
    "real-questions": ("real", """
        document.querySelector('#steps button[data-step="2"]').click();
    """, "#funnel", "#pcards"),
    "journey-follow": ("journey", """
        document.querySelector('#steps button[data-step="3"]').click();
        document.querySelector('#lensseg button[data-k^="agent:gemini"]').click();
        await new Promise(r => setTimeout(r, 100));
        [...document.querySelectorAll('#quick button')].find(b => b.textContent.trim() === 'DESCRIPTION').click();
    """, ".controls", "#techs tr.on"),
    "assistant-refusal": ("assistant", """
        const box = document.getElementById('input');
        box.value = "what is the patient's diagnosis";
        document.getElementById('compose').requestSubmit();
        document.querySelector('.chat').style.height = '560px';   // the whole refusal, no empty chat below it
    """, ".main"),
    "rules-vs-ai": ("rules", "", ".pane"),
}


def capture() -> list[Path]:
    import tempfile
    sys.path.insert(0, str(ROOT))
    from tools.page_kit import PORTAL, parts_in

    parts = parts_in(PORTAL)
    tmp = Path(tempfile.mkdtemp(prefix="demo-parts-"))
    OUT.mkdir(parents=True, exist_ok=True)
    written = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport=VIEWPORT, device_scale_factor=2, color_scheme="light")
        for name, (key, script, selector, *cut) in SHOTS.items():
            if key not in parts:
                print(f"  {name}: the portal has no '{key}' tab -- skipped")
                continue
            path = tmp / f"{key}.html"
            path.write_text(parts[key], encoding="utf-8")
            page.goto(path.resolve().as_uri())
            page.wait_for_load_state("load")
            if script.strip():
                page.evaluate(f"async () => {{ {script} }}")
            page.wait_for_timeout(2500)          # the pages animate in; capture them settled
            target = OUT / f"{name}.png"
            if cut:
                # Only the part that carries the point: down to the lowest element matching ``cut``.
                box = page.locator(selector).first.bounding_box()
                bottom = page.evaluate(f"() => Math.max(...[...document.querySelectorAll('{cut[0]}')]"
                                       f".map(e => e.getBoundingClientRect().bottom + window.scrollY))")
                page.screenshot(path=str(target), full_page=True, clip={
                    "x": box["x"], "y": box["y"], "width": box["width"], "height": bottom - box["y"] + 14})
            else:
                page.locator(selector).first.screenshot(path=str(target))
            written.append(target)
        browser.close()
    return written


def main() -> int:
    for path in capture():
        print(f"  wrote {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
