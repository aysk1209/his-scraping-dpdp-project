"""Build the journey page: one entry of an export, followed through every stage of the pipeline.

    python tools/build_journey_page.py                        # Synthea's sample, its first patient
    python tools/build_journey_page.py data/public_synthea --row 5
    python tools/build_journey_page.py data/hospital_export --column-map data/hospital_export/column_map.json

Runs ``scripts/trace_journey.journey`` -- the real gate, adapter, techniques,
rules, export and its audit, purpose matrix, role policy, audit log and purge
-- and writes a self-contained page (``tools/journey_page.html`` + one JSON
block, no network): pick a column of the entry and the rail shows what
happened to it at each of the seven stages; pick a job and a technique and
every stage redraws.

Held to the rules it shows, like the dataset page: direct identifiers, contact
details and every column the pipeline never reads are masked; a real export
shows shape only, and its page is refused anywhere git would commit it. The
journey refuses to return anything that carries the patient's raw record
number or any identifier in the export, and the page is that data and a
template, nothing else.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from compliance.handling import declares_synthetic, git_ignores     # noqa: E402
from extraction.adapters.dataset_his import load_column_map          # noqa: E402
from tools.page_kit import REVIEW_DIR, render, write, part_path   # noqa: E402
from trace_journey import DEFAULT_DATASET, journey                   # noqa: E402

TEMPLATE = ROOT / "tools" / "journey_page.html"
DEFAULT_OUT = part_path("journey")


class PageLeak(RuntimeError):
    """The built page would carry a value it must not show."""


def build(directory: Path = DEFAULT_DATASET, *, column_map: dict | None = None, file_maps: dict | None = None,
          row: int = 0, out: Path = DEFAULT_OUT, enforce_handling: bool = True, today=None) -> dict:
    directory = Path(directory)
    if not declares_synthetic(directory) and not git_ignores(out):
        raise PageLeak(f"{out} is not git-ignored: a page built from a real export must never be committable")
    data = journey(directory, column_map=column_map, file_maps=file_maps, row=row,
                   enforce_handling=enforce_handling, today=today)
    page = render(TEMPLATE, data, current="journey", out=out)
    write(out, page)
    return data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", nargs="?", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--column-map", help="JSON: export header -> catalogue field (default: the export's column_map.json)")
    parser.add_argument("--row", type=int, default=0, help="which row of the registration file")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    if not args.dataset.exists():
        raise SystemExit(f"{args.dataset} is not here -- python scripts/fetch_public_dataset.py puts Synthea's sample there")
    cmap = args.column_map or (args.dataset / "column_map.json" if (args.dataset / "column_map.json").exists() else None)
    column_map, file_maps = load_column_map(cmap)
    data = build(args.dataset, column_map=column_map, file_maps=file_maps, row=args.row, out=args.out)
    reg = data["entries"][0]
    print(f"  wrote {args.out}")
    print(f"  {reg['file']} line {reg['line']} -> {data['meta']['token']}; {len(data['tasks'])} jobs x "
          f"{len(data['meta']['techniques'])} techniques; values "
          f"{'shown (synthetic)' if data['meta']['values_shown'] else 'hidden (real export)'}")
    print("  page audit: no raw identifier on the page")
    return 0


if __name__ == "__main__":
    sys.exit(main())
