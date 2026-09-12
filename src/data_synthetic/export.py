"""Write a synthetic dataset to disk in the shape a hospital export would take.

One CSV per HIS layer, plus a ``manifest.json`` recording how it was produced.
This is the *raw structure* the dataset adapter (``extraction.adapters.dataset_his``)
reads, so that adapter is built and tested now against files of the right shape,
and the real hospital export -- when it arrives -- is a column mapping rather than
new code.

The manifest states plainly that the data is synthetic. A real export dropped
into the same directory would carry its own provenance note instead; the
handling requirements in PLAN.md section 4 apply to it and not to this.

Output goes under ``data/``, which is git-ignored -- the same place a real export
will land, so that the ignore rule is in force before any real data exists.
"""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from data_synthetic.catalogue import FIELD_CATALOGUE
from data_synthetic.generators import build_dataset
from interop.layers import HISLayer

_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DIR = _REPO_ROOT / "data" / "synthetic_export"
MANIFEST = "manifest.json"


def write_export(
    directory: Path | None = None,
    *,
    records_per_layer: int = 200,
    seed: int | None = 42,
) -> Path:
    """Generate and write one CSV per layer; return the directory."""

    directory = Path(directory) if directory else DEFAULT_DIR
    directory.mkdir(parents=True, exist_ok=True)

    dataset = build_dataset(records_per_layer, seed=seed)
    files: dict[str, dict[str, Any]] = {}
    for layer, rows in dataset.items():
        path = directory / f"{layer.value}.csv"
        columns = list(FIELD_CATALOGUE[layer])
        with path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)
        files[path.name] = {"layer": layer.value, "rows": len(rows), "columns": columns}

    manifest = {
        "kind": "synthetic",
        "note": "Faker-generated records; no real patients, no real hospital. "
                "Safe to share, regenerate at will.",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "seed": seed,
        "records_per_layer": records_per_layer,
        "files": files,
    }
    (directory / MANIFEST).write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return directory


def read_manifest(directory: Path) -> dict[str, Any] | None:
    path = Path(directory) / MANIFEST
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


__all__ = ["write_export", "read_manifest", "DEFAULT_DIR", "MANIFEST"]
