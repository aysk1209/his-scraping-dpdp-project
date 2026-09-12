"""The file-backed adapter against a synthetic export of the right shape."""

from __future__ import annotations

import csv

import pytest

from compliance.benchmark import run_benchmark
from compliance.models import Purpose
from data_synthetic.export import read_manifest, write_export
from extraction.adapters.dataset_his import DatasetHISDataSource
from extraction.technique import ExtractionTask, LayerFields
from extraction.techniques import DEFAULT_TECHNIQUES
from interop.layers import HISLayer

RECORDS = 12


@pytest.fixture(scope="module")
def export_dir(tmp_path_factory):
    return write_export(tmp_path_factory.mktemp("export"), records_per_layer=RECORDS, seed=9)


@pytest.fixture(scope="module")
def source(export_dir):
    return DatasetHISDataSource(export_dir)


def test_export_writes_one_file_per_layer_and_a_manifest(export_dir):
    manifest = read_manifest(export_dir)
    assert manifest["kind"] == "synthetic" and manifest["seed"] == 9
    assert set(manifest["files"]) == {f"{l.value}.csv" for l in HISLayer}


def test_every_file_is_classified_by_its_columns_not_its_name(source):
    assert set(source.layers()) == set(HISLayer)
    assert all(c == 1.0 for c in source.confidence.values())
    assert source.unclassified == [] and source.dropped_columns == {}


def test_fetch_projects_and_paginates_nothing_it_is_all_local(source):
    rows = list(source.fetch(HISLayer.PATIENT_ADMINISTRATION, fields=["mrn", "sex"]))
    assert len(rows) == RECORDS
    assert all(set(r) == {"mrn", "sex"} for r in rows)


def test_missing_fields_are_simply_absent(source):
    rows = list(source.fetch(HISLayer.CLINICAL_EHR, fields=["primary_diagnosis", "no_such"]))
    assert all(set(r) == {"primary_diagnosis"} for r in rows)


def test_a_hospital_named_file_with_hospital_named_columns_needs_only_a_column_map(tmp_path):
    # What the real export will look like: a file called whatever, columns called
    # whatever. The mapping is the entire integration.
    path = tmp_path / "PatientMaster_2026.csv"
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Patient ID", "Patient Name", "DOB", "Gender", "Ward", "Internal Flag"])
        w.writerow(["H001", "A Person", "1990-01-01", "F", "Ward A", "x"])
    src = DatasetHISDataSource(tmp_path, enforce_handling=False, column_map={
        "Patient ID": "mrn", "Patient Name": "full_name", "DOB": "date_of_birth",
        "Gender": "sex", "Ward": "admission_ward",
    })   # throwaway test file, not real data -- hence enforce_handling=False
    assert src.layers() == (HISLayer.PATIENT_ADMINISTRATION,)
    (row,) = src.fetch(HISLayer.PATIENT_ADMINISTRATION)
    assert row == {"mrn": "H001", "full_name": "A Person", "date_of_birth": "1990-01-01",
                   "sex": "F", "admission_ward": "Ward A"}
    assert src.dropped_columns == {"PatientMaster_2026.csv": ["Internal Flag"]}
    assert "not understood and dropped" in src.describe()


def test_unrecognisable_file_is_skipped_and_reported(tmp_path):
    (tmp_path / "notes.csv").write_text("colour,shape\nred,round\n", encoding="utf-8")
    src = DatasetHISDataSource(tmp_path, enforce_handling=False)
    assert src.layers() == ()
    assert src.unclassified == ["notes.csv"]


def test_missing_directory_is_an_error(tmp_path):
    with pytest.raises(FileNotFoundError):
        DatasetHISDataSource(tmp_path / "nowhere", enforce_handling=False)


def test_real_looking_data_outside_data_dir_is_refused(tmp_path):
    from compliance.handling import UnsafeDataset
    (tmp_path / "PatientMaster.csv").write_text("mrn,sex\nH1,F\n", encoding="utf-8")
    with pytest.raises(UnsafeDataset) as exc:
        DatasetHISDataSource(tmp_path)
    assert "under data/" in str(exc.value) and "provenance" in str(exc.value)


def test_techniques_and_benchmark_run_unchanged_against_the_export(source):
    task = ExtractionTask(
        task_id="export-summary", purpose=Purpose.CARE_COORDINATION,
        needed=[LayerFields(layer=HISLayer.PATIENT_ADMINISTRATION, fields=["mrn", "sex"]),
                LayerFields(layer=HISLayer.CLINICAL_EHR, fields=["primary_diagnosis"])],
    )
    result = run_benchmark(DEFAULT_TECHNIQUES, [task], source)
    scores = {s.short: s for s in result.scores}
    assert scores["compliance-aware"].mean_compliance_score == 1.0
    assert scores["unconstrained"].cost.excess_ratio > 1.0
    assert scores["compliance-aware"].cost.records == 2 * RECORDS
