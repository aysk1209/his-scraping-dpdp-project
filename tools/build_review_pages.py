"""Build the one demo portal, docs/review/portal.html, in one command.

    python tools/build_review_pages.py                  # every demo that can be built here
    python tools/build_review_pages.py --skip-portal    # no browser on this machine

Every demo is built as a part into the git-ignored ``build/review-parts/`` and
the parts are assembled into a single self-contained file with a tab per demo
(``tools/page_kit.assemble``; six tabs since 2026-10-09). A part this machine
cannot rebuild -- the portal run and the HIS update need Chromium
(``python -m playwright install chromium``), the journey needs the public
Synthea sample (``python scripts/fetch_public_dataset.py``) -- is carried over
from the portal already committed, never dropped. Every part is synthetic or
public-synthetic data, so the portal is committable. The dataset walkthrough
and the hospital-register page left the portal; ``tools/build_dataset_page.py``
and ``tools/build_real_page.py`` still build them on their own.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from tools.page_kit import (                                     # noqa: E402
    PORTAL, REVIEW_DIR, TABS, assemble, part_path, parts_in, write,
)

SYNTHEA = ROOT / "data" / "public_synthea"
RESULTS = ROOT / "docs" / "benchmark_results"

# The separate pages the portal replaced (2026-10-06). Removed when the portal is built.
RETIRED = [REVIEW_DIR / n for n in ("index.html", "portal-run.html", "dataset-walkthrough.html", "real-data.html",
                                    "journey.html", "assistant.html", "his-update.html", "patient-rights.html")] \
    + [RESULTS / "rules-vs-just-ai.html", RESULTS / "techniques-compared.html"]


def build_parts(*, skip_browser: bool = False) -> dict[str, str]:
    """Every part this machine can build, written to the staging folder; returns {key: html}."""

    built: dict[str, Path] = {}

    def done(key: str) -> None:
        built[key] = part_path(key)
        print(f"  built {key}")

    from tools import build_demo_page
    build_demo_page.main()
    done("rules")

    from tools import build_assistant_page
    build_assistant_page.build()
    done("assistant")

    from tools import build_rights_page
    build_rights_page.build()
    done("rights")

    if skip_browser:
        print("  portal run and HIS update: skipped (no browser) -- carried over")
    else:
        from tools import build_portal_page, build_update_page
        build_portal_page.build()
        done("portal")
        build_update_page.build()
        done("update")

    if (SYNTHEA / "patients.csv").exists():
        from extraction.adapters.dataset_his import load_column_map
        from tools import build_journey_page
        column_map, file_maps = load_column_map(SYNTHEA / "column_map.json")
        build_journey_page.build(SYNTHEA, column_map=column_map, file_maps=file_maps)
        done("journey")
    else:
        print("  journey: no Synthea sample here (scripts/fetch_public_dataset.py) -- carried over")

    return {k: p.read_text(encoding="utf-8") for k, p in built.items()}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-portal", action="store_true", help="no browser here: carry the browser-built demos over")
    args = parser.parse_args()

    previous = parts_in(PORTAL)
    parts = build_parts(skip_browser=args.skip_portal)
    tabs = {k for k, _ in TABS}
    for key, html in previous.items():
        if key not in parts and key in tabs:
            parts[key] = html
            print(f"  carried over {key} from the committed portal")

    missing = [k for k, _ in TABS if k not in parts]
    write(PORTAL, assemble(parts))
    size = PORTAL.stat().st_size / 1024 / 1024
    print(f"  wrote {PORTAL.relative_to(ROOT)}  ({len([k for k in parts if k in tabs])} tabs, {size:.1f} MB)"
          + (f"; not available: {', '.join(missing)}" if missing else ""))

    for old in RETIRED:
        if old.exists():
            old.unlink()
            print(f"  removed {old.relative_to(ROOT)} (now a tab of the portal)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
