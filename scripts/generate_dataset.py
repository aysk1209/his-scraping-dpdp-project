"""Write a synthetic HIS dataset to disk, in the shape a hospital export would take.

    python scripts/generate_dataset.py                       # 200 records/layer -> data/synthetic_export/
    python scripts/generate_dataset.py --records 5000        # large enough to matter
    python scripts/generate_dataset.py --out data/my_export  # elsewhere (still under data/)

One CSV per HIS layer plus a manifest.json that says the data is synthetic. The
dataset adapter (extraction.adapters.dataset_his) reads exactly this layout, so
the real export -- when it arrives -- is a column mapping, not new code.

data/ is git-ignored. Nothing written here can end up in the repository.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import _present as present
from data_synthetic.export import DEFAULT_DIR, read_manifest, write_export


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--records", type=int, default=200, help="records per layer")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=Path, default=DEFAULT_DIR)
    args = parser.parse_args()

    print(present.banner("Synthetic HIS export"))
    directory = write_export(args.out, records_per_layer=args.records, seed=args.seed)
    manifest = read_manifest(directory) or {}
    for name, info in manifest.get("files", {}).items():
        print(f"  {name:<34} {info['rows']:>6} rows  {len(info['columns']):>2} columns  ({info['layer']})")
    print()
    print(present.wrote(directory / "manifest.json"))
    print(f"\n  {manifest.get('note', '')}")


if __name__ == "__main__":
    main()
