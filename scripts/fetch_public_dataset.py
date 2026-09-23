"""Fetch the public Synthea sample into data/ and prepare it for the dataset path.

    python scripts/fetch_public_dataset.py            # download (~6 MB), unzip, write PROVENANCE.md + map
    python scripts/fetch_public_dataset.py --force    # re-download even if it is already there

The hospital's export is not here yet. Until it is, the dataset path is shown
on data we did not generate: Synthea's public sample (MITRE, Apache-2.0) --
about a hundred synthetic US patients, one CSV per clinical concept, a
28-column registration file with SSN, passport and licence numbers. No real
person is described.

It lands in ``data/public_synthea/`` (git-ignored) with a ``PROVENANCE.md`` and
**no** synthetic manifest, so it passes through the real-data handling gate like
the hospital's export will. The provenance note says ``Synthetic: yes``, which
lets ``tools/build_dataset_page.py`` show its values; a real export's page
shows structure only. The column map is the committed
``docs/access/synthea-column-map.json``.

Then:

    python scripts/check_source.py data/public_synthea --column-map data/public_synthea/column_map.json
    python scripts/run_pipeline.py --dataset data/public_synthea --column-map data/public_synthea/column_map.json
    python tools/build_dataset_page.py data/public_synthea --column-map data/public_synthea/column_map.json
"""

from __future__ import annotations

import argparse
import io
import shutil
import sys
import urllib.request
import zipfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
URL = "https://synthetichealth.github.io/synthea-sample-data/downloads/latest/synthea_sample_data_csv_latest.zip"
TARGET = ROOT / "data" / "public_synthea"
COLUMN_MAP = ROOT / "docs" / "access" / "synthea-column-map.json"

PROVENANCE = """# Provenance -- public Synthea sample

- **What:** Synthea sample data, CSV export (`synthea_sample_data_csv_latest.zip`, {size:,} bytes).
- **Supplied by:** the Synthea project (MITRE), published at
  https://synthetichealth.github.io/synthea-sample-data/ under the Apache-2.0 licence.
- **Obtained:** {today}, by `scripts/fetch_public_dataset.py`, to show the dataset path on data
  we did not generate while the hospital's export is awaited.
- **Basis:** public, openly licensed data; no consent or agreement is needed.
- **Synthetic:** yes
- **De-identification status:** fully synthetic -- no real person is described. The records carry
  *synthetic* direct identifiers (names, SSN, driving licence and passport numbers, addresses),
  handled as if they were identifiable: that is the point of the exercise.
- **Structure:** unseen by the pipeline -- a US-style, long-format export, one file per clinical
  concept. Deliberately not marked `synthetic` in a manifest, so it goes through the real-data
  handling gate.
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="download again even if the data is present")
    args = parser.parse_args()

    if (TARGET / "patients.csv").exists() and not args.force:
        print(f"  already present: {TARGET.relative_to(ROOT)} (use --force to download again)")
    else:
        print(f"  downloading {URL}")
        try:
            with urllib.request.urlopen(URL, timeout=120) as response:
                payload = response.read()
        except OSError as exc:
            print(f"  download failed: {exc}")
            return 1
        if TARGET.exists():
            shutil.rmtree(TARGET)
        TARGET.mkdir(parents=True)
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            members = [m for m in archive.namelist() if m.lower().endswith(".csv")]
            for member in members:
                # Flatten any folder inside the archive; keep only the CSVs.
                (TARGET / Path(member).name).write_bytes(archive.read(member))
        print(f"  {len(members)} CSV files, {len(payload):,} bytes -> {TARGET.relative_to(ROOT)}")
        (TARGET / "PROVENANCE.md").write_text(
            PROVENANCE.format(size=len(payload), today=date.today().isoformat()), encoding="utf-8")

    shutil.copyfile(COLUMN_MAP, TARGET / "column_map.json")
    print(f"  column map: {COLUMN_MAP.relative_to(ROOT)} -> {(TARGET / 'column_map.json').relative_to(ROOT)}")
    print("  next: python tools/build_dataset_page.py data/public_synthea "
          "--column-map data/public_synthea/column_map.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
