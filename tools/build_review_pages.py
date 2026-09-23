"""Rebuild every Review-II demo page in docs/review/, in one command.

    python tools/build_review_pages.py                  # index, portal run, assistant, dataset (Synthea)
    python tools/build_review_pages.py --skip-portal    # no browser on this machine

The portal run needs Chromium (``python -m playwright install chromium``) and
takes about a minute. The dataset page needs the public Synthea sample
(``python scripts/fetch_public_dataset.py``, once); without it the committed
copy is left as it is. Every page is synthetic or public-synthetic data, so all
of them are committable -- the hospital's export is built separately, to a
git-ignored path, by ``tools/build_dataset_page.py``.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from tools.page_kit import REVIEW_DIR, render, write   # noqa: E402

SYNTHEA = ROOT / "data" / "public_synthea"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-portal", action="store_true", help="leave the portal page as it is")
    args = parser.parse_args()

    index = REVIEW_DIR / "index.html"
    write(index, render(ROOT / "tools" / "review_index.html", None, current="index", out=index))
    print(f"  wrote {index.relative_to(ROOT)}")

    from tools import build_assistant_page
    build_assistant_page.build()
    print(f"  wrote {build_assistant_page.DEFAULT_OUT.relative_to(ROOT)}")

    if args.skip_portal:
        print("  portal page: skipped")
    else:
        from tools import build_portal_page
        build_portal_page.build()
        print(f"  wrote {build_portal_page.DEFAULT_OUT.relative_to(ROOT)}")

    if (SYNTHEA / "patients.csv").exists():
        from extraction.adapters.dataset_his import load_column_map
        from tools import build_dataset_page
        out = REVIEW_DIR / "dataset-walkthrough.html"
        column_map, file_maps = load_column_map(SYNTHEA / "column_map.json")
        build_dataset_page.build(SYNTHEA, column_map=column_map, file_maps=file_maps, out=out)
        print(f"  wrote {out.relative_to(ROOT)}")
    else:
        print("  dataset page: no Synthea sample here (scripts/fetch_public_dataset.py); committed copy kept")
    return 0


if __name__ == "__main__":
    sys.exit(main())
