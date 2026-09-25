"""Photograph the demo pages in their most telling state, for the review deck.

    python tools/capture_demo_pages.py        # writes docs/review/img/*.png (needs Chromium)

Each page is opened from disk in headless Chromium at a projector-like size,
driven into the moment the presenter points at -- the crawl finished, the
billing trap on one patient, a refusal with its three checks -- and captured.
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

# name -> (page, script run on it before capture, element to capture[, cut below the lowest of these])
SHOTS = {
    "portal-crawl": (REVIEW / "portal-run.html", """
        document.querySelector('#steps button[data-step="3"]').click();
        await new Promise(r => setTimeout(r, 500));
        document.querySelector('#speedseg button[data-v="3"]').click();
        document.getElementById('play').click();
        await new Promise(r => { const t = setInterval(() => { if (!document.getElementById('play').disabled) { clearInterval(t); r(); } }, 100); });
        document.querySelectorAll('.sq b.now').forEach(b => b.classList.remove('now'));
    """, "#lanes"),
    "dataset-patient": (REVIEW / "dataset-walkthrough.html", """
        document.querySelector('#steps button[data-step="3"]').click();
        document.querySelector('#taskseg button[data-t="claim-reconciliation"]').click();
    """, "#who", "#who .fchips"),
    "assistant-refusal": (REVIEW / "assistant.html", """
        const box = document.getElementById('input');
        box.value = "what is the patient's diagnosis";
        document.getElementById('compose').requestSubmit();
        document.querySelector('.chat').style.height = '400px';   // no empty chat below the refusal
    """, ".main"),
    "rules-vs-ai": (ROOT / "docs" / "benchmark_results" / "rules-vs-just-ai.html", "", ".pane"),
}


def capture() -> list[Path]:
    OUT.mkdir(parents=True, exist_ok=True)
    written = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport=VIEWPORT, device_scale_factor=2, color_scheme="light")
        for name, (path, script, selector, *cut) in SHOTS.items():
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
