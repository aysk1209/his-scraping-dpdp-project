"""An export shaped like nothing we generated -- the defects a public dataset found.

Run through the day-one procedure on 2026-09-23, a public synthetic export
(US-style, one file per clinical concept, 28-column registration file) found
three defects that the hospital-shaped rehearsal had not:

1. identifiers read as numbers: ``000123`` became ``123``, or ``123.0`` in a
   column with a blank, and the single-patient lookup silently found nothing;
2. an export the adapter understood none of still produced a benchmark and a
   headline gap, because the rules score an empty pull as compliant;
3. a header blanked in the map ("drop it") still counted against the file's
   confidence, so a wide file with honest mappings could never be read -- and
   ``check_source`` reported a percentage while the adapter silently skipped it.

These fixtures are tiny and written here; no downloaded data is needed.
"""

from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

import pytest

from compliance.benchmark import run_benchmark
from compliance.models import Purpose
from extraction.adapters.dataset_his import DatasetHISDataSource, load_column_map, read_columns
from extraction.technique import ExtractionTask, LayerFields
from extraction.techniques import CompliantExtractionTechnique, UnconstrainedExtractionTechnique
from interop.layers import HISLayer

ROOT = Path(__file__).resolve().parents[2]

# A registration file with far more columns than the catalogue models.
WIDE_HEADERS = ["Id", "BIRTHDATE", "SSN", "PASSPORT", "FIRST", "LAST", "MARITAL", "RACE", "GENDER",
                "ADDRESS", "CITY", "STATE", "COUNTY", "ZIP", "LAT", "LON", "INCOME"]
WIDE_MAP = {"Id": "mrn", "BIRTHDATE": "date_of_birth", "GENDER": "sex", "ADDRESS": "street_address"}


def _write(path: Path, header: list[str], *rows: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)


def _wide_row(mrn: str) -> list[str]:
    values = {"Id": mrn, "BIRTHDATE": "1978-01-16", "SSN": "999-55-9547", "PASSPORT": "X81842955X",
              "GENDER": "M", "ADDRESS": "733 Boehm Ville", "ZIP": "01535"}
    return [values.get(h, "x") for h in WIDE_HEADERS]


def _mark_synthetic(directory: Path) -> None:
    # Lets the scripts' handling gate pass on a throwaway tmp directory.
    (directory / "manifest.json").write_text(json.dumps({"kind": "synthetic"}), encoding="utf-8")


# ------------------------------------------------ 1. values are read as text

def test_leading_zeros_survive_and_a_blank_does_not_break_the_patient_join(tmp_path):
    _write(tmp_path / "reg.csv", ["mrn", "full_name", "phone"],
           ["000123", "A Person", "09800000012"], ["000456", "B Person", ""])
    # A blank patient key in the clinical file used to turn the column into floats.
    _write(tmp_path / "clin.csv", ["mrn", "primary_diagnosis", "medication"],
           ["000123", "flu", "x"], ["", "unknown", "y"], ["000456", "cold", "z"])
    src = DatasetHISDataSource(tmp_path, enforce_handling=False)
    reg = list(src.fetch(HISLayer.PATIENT_ADMINISTRATION))
    assert reg[0] == {"mrn": "000123", "full_name": "A Person", "phone": "09800000012"}
    assert reg[1] == {"mrn": "000456", "full_name": "B Person"}          # the blank phone is absent, not "nan"
    rows = list(src.fetch(HISLayer.CLINICAL_EHR, where={"mrn": reg[0]["mrn"]}))
    assert rows == [{"mrn": "000123", "primary_diagnosis": "flu", "medication": "x"}]


def test_excel_text_cells_keep_their_zeros(tmp_path):
    pd = pytest.importorskip("pandas")
    pytest.importorskip("openpyxl")
    pd.DataFrame({"mrn": ["000123"], "primary_diagnosis": ["flu"]}).to_excel(tmp_path / "clin.xlsx", index=False)
    src = DatasetHISDataSource(tmp_path, enforce_handling=False)
    assert list(src.fetch(HISLayer.CLINICAL_EHR)) == [{"mrn": "000123", "primary_diagnosis": "flu"}]


def test_the_billed_amount_is_still_a_number(tmp_path):
    _write(tmp_path / "bill.csv", ["mrn", "invoice_id", "billed_amount"],
           ["000123", "INV-01", "1,250.50"], ["000123", "INV-02", "pending"])
    src = DatasetHISDataSource(tmp_path, enforce_handling=False)
    first, second = src.fetch(HISLayer.ADMINISTRATIVE_FINANCIAL)
    assert first["billed_amount"] == 1250.5 and first["invoice_id"] == "INV-01"
    assert second["billed_amount"] == "pending"                         # left as written, and counted
    assert src.unparsed_numbers == {"bill.csv": {"billed_amount": 1}}
    assert "numbers left as written" in src.describe()


# ------------------------------------- 3. a blank in the map means "drop it"

def test_blanked_headers_do_not_count_against_the_file(tmp_path):
    _write(tmp_path / "patients.csv", WIDE_HEADERS, _wide_row("p-1"))
    without_blanks = DatasetHISDataSource(tmp_path, enforce_handling=False, column_map=WIDE_MAP)
    assert without_blanks.layers() == ()
    assert "the adapter needs 50%" in without_blanks.unclassified_reason["patients.csv"]

    blanks = {h: "" for h in WIDE_HEADERS if h not in WIDE_MAP}
    src = DatasetHISDataSource(tmp_path, enforce_handling=False, column_map={**WIDE_MAP, **blanks})
    assert src.layers() == (HISLayer.PATIENT_ADMINISTRATION,)
    assert src.confidence[HISLayer.PATIENT_ADMINISTRATION] == 1.0
    assert src.blanked_columns["patients.csv"] == list(blanks)
    (row,) = src.fetch(HISLayer.PATIENT_ADMINISTRATION)
    assert set(row) == {"mrn", "date_of_birth", "sex", "street_address"}  # SSN, passport etc. never enter
    assert "dropped by the column map" in src.describe()


def test_a_per_file_blank_overrides_a_global_mapping(tmp_path):
    _write(tmp_path / "conditions.csv", ["PATIENT", "DESCRIPTION"], ["p-1", "flu"])
    _write(tmp_path / "careplans.csv", ["PATIENT", "DESCRIPTION", "START"], ["p-1", "diet", "2020-01-01"])
    src = DatasetHISDataSource(tmp_path, enforce_handling=False, column_map={"PATIENT": "mrn"},
                               file_maps={"conditions.csv": {"DESCRIPTION": "primary_diagnosis"},
                                          "careplans.csv": {"PATIENT": ""}})
    assert src.layers() == (HISLayer.CLINICAL_EHR,)
    assert "careplans.csv" in src.unclassified                          # its patient key was dropped for it


def test_a_file_known_only_by_its_patient_key_is_not_given_a_layer(tmp_path):
    # mrn is on four layers; a care-plan file must not be read as registration.
    _write(tmp_path / "careplans.csv", ["PATIENT", "DESCRIPTION"], ["p-1", "diet"])
    src = DatasetHISDataSource(tmp_path, enforce_handling=False, column_map={"PATIENT": "mrn", "DESCRIPTION": ""})
    assert src.layers() == ()
    assert "only the patient key" in src.unclassified_reason["careplans.csv"]
    # The audit trail's key is on one layer only, so it does tell the layer.
    assert read_columns(["subject_mrn", "x"], {"x": ""}).accepted


def test_check_source_prints_the_adapters_verdict(tmp_path, capsys):
    from scripts.check_source import check_directory
    _write(tmp_path / "patients.csv", WIDE_HEADERS, _wide_row("p-1"))
    _mark_synthetic(tmp_path)
    check_directory(tmp_path, dict(WIDE_MAP), None)
    out = capsys.readouterr().out
    assert "NOT READ" in out and "the adapter will read 0 of 1" in out

    blanks = {h: "" for h in WIDE_HEADERS if h not in WIDE_MAP}
    check_directory(tmp_path, {**WIDE_MAP, **blanks}, None)
    out = capsys.readouterr().out
    assert "reads it as patient_administration" in out and "the adapter will read 1 of 1" in out
    assert "dropped by map" in out


def test_the_column_map_loader_keeps_blanks_and_reads_a_bare_map(tmp_path):
    template = tmp_path / "t.json"
    template.write_text(json.dumps({"_about": "...", "map": {"SSN": "", "Id": "mrn"},
                                    "files": {"a.csv": {"Id": ""}}, "_catalogue": {}}), encoding="utf-8")
    assert load_column_map(template) == ({"SSN": "", "Id": "mrn"}, {"a.csv": {"Id": ""}})
    bare = tmp_path / "b.json"
    bare.write_text(json.dumps({"Patient ID": "mrn"}), encoding="utf-8")
    assert load_column_map(bare) == ({"Patient ID": "mrn"}, {})
    assert load_column_map(None) == ({}, {})


# ----------------------------------- 2. nothing understood -> no benchmark

TASK = ExtractionTask(
    task_id="patient-summary", purpose=Purpose.CARE_COORDINATION,
    needed=[LayerFields(layer=HISLayer.PATIENT_ADMINISTRATION, fields=["mrn", "date_of_birth", "sex"])],
)


def test_an_empty_source_gets_no_headline_gap(tmp_path):
    _write(tmp_path / "patients.csv", WIDE_HEADERS, _wide_row("p-1"))     # unmapped: nothing understood
    src = DatasetHISDataSource(tmp_path, enforce_handling=False)
    result = run_benchmark([CompliantExtractionTechnique(), UnconstrainedExtractionTechnique()], [TASK], src)
    assert result._takeaway().startswith("No comparison")


def test_the_pipeline_shortfall_check(tmp_path):
    from scripts.run_pipeline import TASKS, dataset_shortfall
    _write(tmp_path / "patients.csv", WIDE_HEADERS, _wide_row("p-1"))
    assert "none of the files" in dataset_shortfall(DatasetHISDataSource(tmp_path, enforce_handling=False), TASKS)
    # Understood (the audit trail), but carrying none of the fields any task needs.
    _write(tmp_path / "patients.csv", ["subject_mrn", "action"], ["p-1", "read"])
    assert "none of the" in dataset_shortfall(DatasetHISDataSource(tmp_path, enforce_handling=False), TASKS)
    _write(tmp_path / "patients.csv", ["mrn", "sex"], ["p-1", "M"])
    assert dataset_shortfall(DatasetHISDataSource(tmp_path, enforce_handling=False), TASKS) is None


def test_the_pipeline_stops_before_benchmarking_what_it_did_not_understand(tmp_path):
    _write(tmp_path / "patients.csv", WIDE_HEADERS, _wide_row("p-1"))
    _mark_synthetic(tmp_path)
    artefact = ROOT / "docs" / "benchmark_results" / "benchmark-dataset.json"
    before = artefact.stat().st_mtime if artefact.exists() else None
    proc = subprocess.run([sys.executable, "scripts/run_pipeline.py", "--dataset", str(tmp_path)],
                          cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=300)
    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert "STOPPED" in proc.stdout and "[3] BENCHMARK" not in proc.stdout
    assert (artefact.stat().st_mtime if artefact.exists() else None) == before


# ------------------------- 4. one file per concept -> the layer is stacked

def _per_concept_export(directory: Path) -> None:
    # How most HIS dumps look: a table per concept, many rows per patient.
    _write(directory / "patients.csv", ["mrn", "date_of_birth", "sex"],
           ["000123", "1978-01-16", "M"], ["000456", "2001-02-11", "F"])
    _write(directory / "conditions.csv", ["mrn", "primary_diagnosis"],
           ["000123", "hypertension"], ["000123", "asthma"], ["000456", "flu"])
    _write(directory / "medications.csv", ["mrn", "medication"], ["000123", "amlodipine"], ["000456", "oseltamivir"])
    _write(directory / "allergies.csv", ["mrn", "allergy"], ["000123", "penicillin"])
    _write(directory / "observations.csv", ["mrn", "lab_result"], *[["000123", str(i)] for i in range(20)])


def test_files_with_different_columns_for_one_layer_are_stacked_not_dropped(tmp_path):
    _per_concept_export(tmp_path)
    src = DatasetHISDataSource(tmp_path, enforce_handling=False)
    assert src.stacked == {HISLayer.CLINICAL_EHR}
    assert src.merged[HISLayer.CLINICAL_EHR] == ["allergies.csv", "conditions.csv", "medications.csv",
                                                  "observations.csv"]
    assert set(src.fields(HISLayer.CLINICAL_EHR)) == {"mrn", "allergy", "primary_diagnosis", "medication",
                                                      "lab_result"}
    assert "files stacked" in src.describe()
    # Every fact is its own record, carrying only its own file's fields; none is lost.
    rows = list(src.fetch(HISLayer.CLINICAL_EHR, fields=["mrn", "primary_diagnosis", "medication", "allergy"],
                          where={"mrn": "000123"}))
    assert sorted(tuple(sorted(r.items())) for r in rows) == sorted([
        (("allergy", "penicillin"), ("mrn", "000123")),
        (("mrn", "000123"), ("primary_diagnosis", "hypertension")),
        (("mrn", "000123"), ("primary_diagnosis", "asthma")),
        (("medication", "amlodipine"), ("mrn", "000123")),
    ])


def test_a_fetch_reads_only_the_files_that_carry_what_was_asked(tmp_path):
    _per_concept_export(tmp_path)
    src = DatasetHISDataSource(tmp_path, enforce_handling=False)
    assert list(src.fetch(HISLayer.CLINICAL_EHR, fields=["mrn", "allergy"])) == [
        {"mrn": "000123", "allergy": "penicillin"}]                      # not 20 observation rows of bare mrn
    # Asked for the key alone (how the harness counts a patient's own records), every file counts.
    assert len(list(src.fetch(HISLayer.CLINICAL_EHR, fields=["mrn"], where={"mrn": "000123"}))) == 24
    # Asked for everything (the baseline), every row comes back.
    assert len(list(src.fetch(HISLayer.CLINICAL_EHR))) == 26


def test_the_patient_summary_is_complete_on_a_per_concept_export(tmp_path):
    from compliance.benchmark import bind_subject
    _per_concept_export(tmp_path)
    src = DatasetHISDataSource(tmp_path, enforce_handling=False)
    task = ExtractionTask(
        task_id="patient-summary", purpose=Purpose.CARE_COORDINATION, single_subject=True,
        needed=[LayerFields(layer=HISLayer.PATIENT_ADMINISTRATION, fields=["mrn", "date_of_birth", "sex"]),
                LayerFields(layer=HISLayer.CLINICAL_EHR, fields=["primary_diagnosis", "medication", "allergy"])],
    )
    result = run_benchmark([CompliantExtractionTechnique(), UnconstrainedExtractionTechnique()],
                           bind_subject([task], src), src)
    ours = next(s for s in result.scores if s.short == "compliance-aware")
    assert ours.cost.coverage == 1.0 and ours.mean_compliance_score == 1.0


# --------------- 5. the coverage ceiling is measured from the source, per task

SUMMARY = ExtractionTask(
    task_id="patient-summary", purpose=Purpose.CARE_COORDINATION, single_subject=True,
    needed=[LayerFields(layer=HISLayer.PATIENT_ADMINISTRATION, fields=["mrn", "date_of_birth", "sex"]),
            LayerFields(layer=HISLayer.CLINICAL_EHR, fields=["primary_diagnosis", "medication", "allergy"])],
)


def test_the_ceiling_counts_what_the_patient_has_not_what_anyone_has(tmp_path):
    from compliance.benchmark import bind_subject, reachable_fields
    _per_concept_export(tmp_path)
    src = DatasetHISDataSource(tmp_path, enforce_handling=False)
    # 000456 has a diagnosis and a medication but no allergy on record.
    [task] = bind_subject([SUMMARY], src, subject="000456")
    assert reachable_fields(task, src) == (6, 6, 5)
    [task] = bind_subject([SUMMARY], src, subject="000123")
    assert reachable_fields(task, src) == (6, 6, 6)


def test_the_headline_does_not_hold_the_patients_missing_records_against_anyone(tmp_path):
    from compliance.benchmark import bind_subject
    _per_concept_export(tmp_path)
    src = DatasetHISDataSource(tmp_path, enforce_handling=False)
    result = run_benchmark([CompliantExtractionTechnique(), UnconstrainedExtractionTechnique()],
                           bind_subject([SUMMARY], src, subject="000456"), src)
    ours, baseline = (next(s for s in result.scores if s.short == k) for k in ("compliance-aware", "unconstrained"))
    assert result.source_ceiling() == 0.833 == ours.cost.coverage      # ours reached everything the patient has
    assert baseline.cost.coverage == 1.0                               # by reading someone else's allergy
    text = result._takeaway()
    assert "1 are in the source but not in the records of the patient" in text
    assert "unconstrained (baseline) shows 100% only because it read other patients' records" in text
    assert "not directly comparable" not in text and "Every technique obtained the same" not in text


def test_the_ceiling_never_asks_a_source_for_a_field_it_lacks_and_stops_early():
    # A portal asked for a field its module lacks would open every detail page.
    from compliance.benchmark import reachable_fields
    from extraction.base import HISDataSource

    class Recording(HISDataSource):
        asked: list[list[str]] = []
        rows_served = 0

        def layers(self):
            return (HISLayer.PATIENT_ADMINISTRATION,)

        def fields(self, layer):
            return ["mrn", "sex"]

        def fetch(self, layer, *, fields=None, where=None, **_):
            self.asked.append(list(fields))
            for i in range(1000):
                Recording.rows_served += 1
                yield {"mrn": f"P{i}", "sex": "F"}

    task = ExtractionTask(task_id="t", purpose=Purpose.CARE_COORDINATION,
                          needed=[LayerFields(layer=HISLayer.PATIENT_ADMINISTRATION,
                                              fields=["mrn", "sex", "full_name"])])
    src = Recording()
    assert reachable_fields(task, src) == (3, 2, 2)
    assert all("full_name" not in asked for asked in src.asked)
    assert Recording.rows_served == 1
