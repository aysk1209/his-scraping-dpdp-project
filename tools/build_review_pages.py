"""Rebuild every Review-II demo page in docs/review/, in one command.

    python tools/build_review_pages.py                  # index, rules vs AI, assistant, portal run, dataset and journey (Synthea), real export
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
RESULTS = ROOT / "docs" / "benchmark_results"


def _update_numbers() -> dict:
    """The HIS-update page's headline, read back from the page itself when it has been built."""

    import json
    import re
    from agent.functions import REGISTRY
    page = REVIEW_DIR / "his-update.html"
    if page.exists():
        m = re.search(r'<script id="data" type="application/json">(.*?)</script>', page.read_text(encoding="utf-8"), re.S)
        if m:
            meta = json.loads(m.group(1).replace(r"<\/", "</"))["meta"]
            return {"restored": meta["restored"], "tasks": meta["tasks"]}
    return {"restored": len(REGISTRY), "tasks": len(REGISTRY)}


def index_data() -> dict:
    """The index's one number per demo, read from the committed artefacts -- never typed."""

    import json
    from agent.functions import REGISTRY
    from compliance.roles import StaffRole

    def scores(name):
        return {s["short"]: s for s in json.loads((RESULTS / f"{name}.json").read_text(encoding="utf-8"))["scores"]}

    portal, public, memory = scores("benchmark-portal"), scores("benchmark-public"), scores("benchmark")
    unaided = [s for s in memory.values() if s.get("briefing") == "unaided"]
    real = {}
    if (RESULTS / "benchmark-real.json").exists() and (REVIEW_DIR / "real-data.html").exists():
        r = json.loads((RESULTS / "benchmark-real.json").read_text(encoding="utf-8"))
        real = {"days": next(s["record_count"] for s in r["scores"] if s["short"] == "compliance-aware"),
                "carried": r["coverage_in_source"], "needed": r["coverage_needed"]}
    return {
        "real": real,
        "portal": {"ours": portal["compliance-aware"]["cost"]["page_loads"],
                   "baseline": portal["unconstrained"]["cost"]["page_loads"]},
        "dataset": {"ours": public["compliance-aware"]["mean_compliance_score"],
                    "baseline": public["unconstrained"]["mean_compliance_score"]},
        "assistant": {"functions": len(REGISTRY), "roles": len(StaffRole)},
        "update": _update_numbers(),
        "rules": {"ours_held": memory["compliance-aware"]["traps_resisted"], "ours_traps": memory["compliance-aware"]["traps"],
                  "agents_held": sum(s["traps_resisted"] for s in unaided), "agents_traps": sum(s["traps"] for s in unaided),
                  "models": len({s["model"] for s in memory.values() if s.get("model")})},
        "rules_href": "../benchmark_results/rules-vs-just-ai.html",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-portal", action="store_true", help="leave the portal page as it is")
    args = parser.parse_args()

    real_dir = ROOT / "data" / "hospital_export"
    if (real_dir / "PROVENANCE.md").exists() and (RESULTS / "benchmark-real.json").exists():
        from tools import build_real_page
        print(f"  wrote {build_real_page.build(real_dir).relative_to(ROOT)}")
    else:
        print("  real-data page: no real export here (or no benchmark-real.json); committed copy kept")

    if not args.skip_portal:            # the update page crawls the fixture in a browser
        from tools import build_update_page
        build_update_page.build()
        print(f"  wrote {build_update_page.DEFAULT_OUT.relative_to(ROOT)}")

    index = REVIEW_DIR / "index.html"
    write(index, render(ROOT / "tools" / "review_index.html", index_data(), current="index", out=index))
    print(f"  wrote {index.relative_to(ROOT)}")

    from tools import build_demo_page
    build_demo_page.main()

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
        from tools import build_journey_page
        build_journey_page.build(SYNTHEA, column_map=column_map, file_maps=file_maps)
        print(f"  wrote {build_journey_page.DEFAULT_OUT.relative_to(ROOT)}")
    else:
        print("  dataset and journey pages: no Synthea sample here (scripts/fetch_public_dataset.py); committed copies kept")
    return 0


if __name__ == "__main__":
    sys.exit(main())
