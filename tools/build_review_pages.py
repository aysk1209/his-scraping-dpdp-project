"""Build the one demo portal, docs/review/portal.html, in one command.

    python tools/build_review_pages.py                  # every demo that can be built here
    python tools/build_review_pages.py --skip-portal    # no browser on this machine

Every demo is built as a part into the git-ignored ``build/review-parts/`` and
the parts are assembled into a single self-contained file with a tab per demo
(``tools/page_kit.assemble``). A part this machine cannot rebuild -- the portal
run and the HIS update need Chromium (``python -m playwright install chromium``),
the dataset and journey need the public Synthea sample
(``python scripts/fetch_public_dataset.py``), the real-data part needs the
hospital's export -- is carried over from the portal already committed, never
dropped. Every part is synthetic or public-synthetic data or, for the real
export, counts and ratios only, so the portal is committable.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from tools.page_kit import (                                     # noqa: E402
    PORTAL, REVIEW_DIR, TABS, assemble, part_data, part_path, parts_in, render, write,
)

SYNTHEA = ROOT / "data" / "public_synthea"
RESULTS = ROOT / "docs" / "benchmark_results"
REAL_DIR = ROOT / "data" / "hospital_export"

# The separate pages the portal replaced (2026-10-06). Removed when the portal is built.
RETIRED = [REVIEW_DIR / n for n in ("index.html", "portal-run.html", "dataset-walkthrough.html", "real-data.html",
                                    "journey.html", "assistant.html", "his-update.html", "patient-rights.html")] \
    + [RESULTS / "rules-vs-just-ai.html", RESULTS / "techniques-compared.html"]


def index_data(parts: dict[str, str]) -> dict:
    """The overview's one number per demo, read from the artefacts and the parts -- never typed."""

    from agent.functions import REGISTRY
    from compliance.roles import StaffRole

    def scores(name):
        return {s["short"]: s for s in json.loads((RESULTS / f"{name}.json").read_text(encoding="utf-8"))["scores"]}

    portal, public, memory = scores("benchmark-portal"), scores("benchmark-public"), scores("benchmark")
    unaided = [s for s in memory.values() if s.get("briefing") == "unaided"]
    real = {}
    if (RESULTS / "benchmark-real.json").exists() and "real" in parts:
        r = json.loads((RESULTS / "benchmark-real.json").read_text(encoding="utf-8"))
        real = {"days": next(s["record_count"] for s in r["scores"] if s["short"] == "compliance-aware"),
                "carried": r["coverage_in_source"], "needed": r["coverage_needed"]}
    update = part_data(parts["update"]).get("meta", {}) if "update" in parts else {}
    rights = part_data(parts["rights"]).get("breach", {}) if "rights" in parts else {}
    return {
        "real": real,
        "portal": {"ours": portal["compliance-aware"]["cost"]["page_loads"],
                   "baseline": portal["unconstrained"]["cost"]["page_loads"]},
        "dataset": {"ours": public["compliance-aware"]["mean_compliance_score"],
                    "baseline": public["unconstrained"]["mean_compliance_score"]},
        "assistant": {"functions": len(REGISTRY), "roles": len(StaffRole)},
        "update": {"restored": update.get("restored", len(REGISTRY)), "tasks": update.get("tasks", len(REGISTRY))},
        "rights": {"ours": rights.get("ours", {}).get("patients", 0), "base": rights.get("baseline", {}).get("patients", 0)},
        "rules": {"ours_held": memory["compliance-aware"]["traps_resisted"], "ours_traps": memory["compliance-aware"]["traps"],
                  "agents_held": sum(s["traps_resisted"] for s in unaided), "agents_traps": sum(s["traps"] for s in unaided),
                  "models": len({s["model"] for s in memory.values() if s.get("model")})},
    }


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
        from tools import build_dataset_page, build_journey_page
        column_map, file_maps = load_column_map(SYNTHEA / "column_map.json")
        build_dataset_page.build(SYNTHEA, column_map=column_map, file_maps=file_maps)
        done("dataset")
        build_journey_page.build(SYNTHEA, column_map=column_map, file_maps=file_maps)
        done("journey")
    else:
        print("  dataset and journey: no Synthea sample here (scripts/fetch_public_dataset.py) -- carried over")

    if (REAL_DIR / "PROVENANCE.md").exists() and (RESULTS / "benchmark-real.json").exists():
        from tools import build_real_page
        build_real_page.build(REAL_DIR)
        done("real")
    else:
        print("  real data: no real export here -- carried over")

    return {k: p.read_text(encoding="utf-8") for k, p in built.items()}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-portal", action="store_true", help="no browser here: carry the browser-built demos over")
    args = parser.parse_args()

    previous = parts_in(PORTAL)
    parts = build_parts(skip_browser=args.skip_portal)
    for key, html in previous.items():
        if key not in parts and key != "index":
            parts[key] = html
            print(f"  carried over {key} from the committed portal")

    index = part_path("index")
    write(index, render(ROOT / "tools" / "review_index.html", index_data(parts), current="index", out=index))
    parts["index"] = index.read_text(encoding="utf-8")

    missing = [k for k, _ in TABS if k not in parts]
    write(PORTAL, assemble(parts))
    size = PORTAL.stat().st_size / 1024 / 1024
    print(f"  wrote {PORTAL.relative_to(ROOT)}  ({len(parts)} tabs, {size:.1f} MB)"
          + (f"; not available: {', '.join(missing)}" if missing else ""))

    for old in RETIRED:
        if old.exists():
            old.unlink()
            print(f"  removed {old.relative_to(ROOT)} (now a tab of the portal)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
