"""Rehearse the first hour with a real hospital export -- before it exists.

    python scripts/rehearse_day_one.py                 # builds data/rehearsal/, runs the procedure, audits
    python scripts/rehearse_day_one.py --keep          # leave the export and the map behind to inspect

The real dataset will not look like our synthetic export. It will have the
hospital's column names, a column we do not model, an Excel file among the
CSVs, dates written the Indian way, and a table split across several files.
This script fabricates exactly that from synthetic data (no real person is
involved), then runs the day-one procedure from ``docs/access/when-access-lands.md``
as a stranger would -- ``check_source.py`` to get the mapping template, the
template filled in, the check again, ``run_pipeline.py --dataset`` -- through
the real handling gate (the export sits under ``data/``, git-ignored, with a
``PROVENANCE.md``; no synthetic manifest, so it is treated as real).

It then audits what the run printed and every file it wrote for a known
patient's direct identifiers -- record number, name, phone. Real data would
be handled by exactly these code paths, so a value that leaks here would leak
then. The run fails loudly if one does.

# DPDP Act 2023 -- security safeguards, accountability: the day the real data
# arrives is the day the project's own claims are tested. Rehearse it.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import _present as present                                              # noqa: E402
from data_synthetic.generators.records import build_dataset            # noqa: E402
from interop.layers import HISLayer                                     # noqa: E402

REHEARSAL_DIR = ROOT / "data" / "rehearsal"

# How a hospital might label things. Left: our catalogue field; right: theirs.
HOSPITAL_HEADERS: dict[HISLayer, dict[str, str]] = {
    HISLayer.PATIENT_ADMINISTRATION: {
        "mrn": "Patient ID", "full_name": "Patient Name", "phone": "Mobile No", "email": "Email",
        "street_address": "Address", "date_of_birth": "DOB", "sex": "Gender", "pincode": "PIN",
        "admission_ward": "Ward", "admission_datetime": "Admitted On",
    },
    HISLayer.CLINICAL_EHR: {
        "mrn": "Patient ID", "primary_diagnosis": "Dx", "medication": "Rx", "lab_result": "Lab Value",
        "allergy": "Allergies", "encounter_datetime": "Visit Date", "attending_clinician": "Consultant",
    },
    HISLayer.ANCILLARY_DEPARTMENTAL: {
        "mrn": "Patient ID", "order_id": "Order No", "specimen_type": "Specimen", "result_value": "Result",
        "imaging_modality": "Modality", "report_text": "Report",
    },
    HISLayer.ADMINISTRATIVE_FINANCIAL: {
        "mrn": "Patient ID", "invoice_id": "Bill No", "billed_amount": "Amount (INR)",
        "insurance_policy_no": "Policy No", "payer_name": "Payer",
    },
    HISLayer.INFRASTRUCTURE_INTEGRATION: {
        "audit_event_id": "Event ID", "event_timestamp": "Timestamp", "actor_role": "Role", "action": "Action",
        "source_system": "System", "subject_mrn": "Patient ID",
    },
}
# A column the catalogue does not model, on the registration file.
UNKNOWN_COLUMN = "Referring Dept"


def _indian_date(iso: str) -> str:
    """'1988-03-14' -> '14/03/1988'; a datetime keeps its time."""

    date, _, rest = iso.partition("T")
    y, m, d = date.split("-")
    return f"{d}/{m}/{y}" + (f" {rest}" if rest else "")


def build_export(directory: Path, records: int = 40, seed: int = 7) -> dict[str, str]:
    """Write the hospital-shaped export; return one patient's direct identifiers."""

    import pandas as pd

    if directory.exists():
        shutil.rmtree(directory)
    directory.mkdir(parents=True)
    data = build_dataset(records, seed=seed)
    frames: dict[HISLayer, "pd.DataFrame"] = {}
    for layer, rows in data.items():
        frame = pd.DataFrame(rows)
        for col in ("date_of_birth", "admission_datetime", "encounter_datetime", "event_timestamp"):
            if col in frame.columns:
                frame[col] = frame[col].map(_indian_date)
        frames[layer] = frame.rename(columns=HOSPITAL_HEADERS[layer])

    reg = frames[HISLayer.PATIENT_ADMINISTRATION]
    reg[UNKNOWN_COLUMN] = ["OPD", "Cardiology", "Ortho", "OPD"] * (len(reg) // 4)
    half = len(reg) // 2
    reg.iloc[:half].to_csv(directory / "registration_jan.csv", index=False)
    reg.iloc[half:].to_csv(directory / "registration_feb.csv", index=False)
    frames[HISLayer.CLINICAL_EHR].to_excel(directory / "clinical_records.xlsx", index=False)
    frames[HISLayer.ANCILLARY_DEPARTMENTAL].to_csv(directory / "lab_orders.csv", index=False)
    frames[HISLayer.ADMINISTRATIVE_FINANCIAL].to_csv(directory / "billing.csv", index=False)
    frames[HISLayer.INFRASTRUCTURE_INTEGRATION].to_csv(directory / "audit_trail.csv", index=False)
    (directory / "PROVENANCE.md").write_text(
        "# Provenance\n\nRehearsal export, generated by scripts/rehearse_day_one.py from synthetic data. "
        "No real person. Written in a hospital's shape to rehearse the day-one procedure.\n\n"
        "De-identification: not applicable -- synthetic; treated as real by the handling gate on purpose.\n",
        encoding="utf-8",
    )
    first = data[HISLayer.PATIENT_ADMINISTRATION][0]
    return {"mrn": first["mrn"], "full_name": first["full_name"], "phone": first["phone"]}


def run(cmd: list[str]) -> tuple[int, str]:
    proc = subprocess.run([sys.executable, *cmd], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    return proc.returncode, proc.stdout + proc.stderr


def fill_map(template: Path) -> int:
    """Play the human: map every hospital header to its catalogue field."""

    data = json.loads(template.read_text(encoding="utf-8"))
    # The global map: what a header means on most files. 'Patient ID' is the
    # record number everywhere except the audit trail, which the human writes
    # under 'files' -- the check suggests exactly that line.
    lookup: dict[str, str] = {}
    for layer, names in HOSPITAL_HEADERS.items():
        if layer is HISLayer.INFRASTRUCTURE_INTEGRATION:
            continue
        lookup.update({theirs: ours for ours, theirs in names.items()})
    lookup.update({theirs: ours for ours, theirs in HOSPITAL_HEADERS[HISLayer.INFRASTRUCTURE_INTEGRATION].items()
                   if theirs != "Patient ID"})
    filled = 0
    for header in list(data["map"]):
        if header in lookup and not data["map"][header]:
            data["map"][header] = lookup[header]
            filled += 1
    data.setdefault("files", {}).setdefault("audit_trail.csv", {})["Patient ID"] = "subject_mrn"
    template.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return filled


def snapshot(dirs: list[Path]) -> dict[Path, float]:
    return {p: p.stat().st_mtime for d in dirs if d.exists() for p in d.rglob("*") if p.is_file()}


def audit_leaks(identifiers: dict[str, str], text: str, files: list[Path]) -> list[str]:
    findings: list[str] = []
    for what, value in identifiers.items():
        if value in text:
            findings.append(f"{what} '{value}' appeared in the terminal output")
        for path in files:
            try:
                if value in path.read_text(encoding="utf-8", errors="replace"):
                    findings.append(f"{what} '{value}' was written to {path.relative_to(ROOT)}")
            except OSError:
                pass
    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", default=str(REHEARSAL_DIR))
    parser.add_argument("--keep", action="store_true", help="leave the export and map in place afterwards")
    args = parser.parse_args()
    directory = Path(args.dir)
    map_path = directory / "column_map.json"

    print(present.banner("Day-one rehearsal: a hospital-shaped export through the real procedure"))
    identifiers = build_export(directory)
    print(f"  export written to {directory}: hospital column names, an unmodelled column "
          f"('{UNKNOWN_COLUMN}'), one .xlsx, dd/mm/yyyy dates, registration split across two files")
    print(f"  the audit will look for one patient's record number, name and phone in everything "
          f"printed or written\n")

    watched = [ROOT / "docs" / "benchmark_results", ROOT / "data" / "audit"]
    before = snapshot(watched)
    started = time.time()
    transcript = ""
    steps = [
        ("check_source.py -- template", ["scripts/check_source.py", str(directory), "--write-map", str(map_path)]),
    ]
    ok = True
    for title, cmd in steps:
        code, out = run(cmd)
        transcript += out
        print(present.rule()); print(f"[{title}] exit {code}"); print(out.rstrip())
        ok = ok and code == 0
    if not map_path.exists():
        print(present.banner("Rehearsal verdict")); print("  the source check refused or wrote no template; fix that first")
        return 1
    filled = fill_map(map_path)
    print(present.rule()); print(f"[fill the map] {filled} headers mapped by hand (simulated); "
                                 f"'{UNKNOWN_COLUMN}' left blank -> dropped")
    for title, cmd in [
        ("check_source.py -- with the map", ["scripts/check_source.py", str(directory), "--column-map", str(map_path)]),
        ("run_pipeline.py --dataset", ["scripts/run_pipeline.py", "--dataset", str(directory), "--column-map", str(map_path)]),
    ]:
        code, out = run(cmd)
        transcript += out
        print(present.rule()); print(f"[{title}] exit {code}"); print(out.rstrip())
        ok = ok and code == 0

    after = snapshot(watched)
    touched = [p for p, m in after.items() if before.get(p) != m and p.stat().st_mtime >= started - 1]
    leaks = audit_leaks(identifiers, transcript, touched)

    print(present.banner("Rehearsal verdict"))
    print(f"  commands succeeded : {'yes' if ok else 'NO'}")
    print(f"  files written      : {len(touched)}")
    for p in touched:
        print(f"    {p.relative_to(ROOT)}")
    print(f"  identifier leaks   : {len(leaks)}")
    for f in leaks:
        print(f"    LEAK: {f}")
    if not args.keep:
        shutil.rmtree(directory, ignore_errors=True)
        print(f"  rehearsal export removed ({directory})")
    return 0 if ok and not leaks else 1


if __name__ == "__main__":
    sys.exit(main())
