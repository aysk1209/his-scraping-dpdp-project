"""The day-one procedure on a hospital-shaped export, and the invariant that
nothing printed or written carries a raw identifier.

The export is what ``scripts/rehearse_day_one.py`` builds: the hospital's own
column names, a column we do not model, an Excel file, day-first dates, and a
layer split across two files. Every defect here was found by that rehearsal
before any real data existed; these tests keep them fixed.
"""

from __future__ import annotations

import json

import pytest

from scripts.rehearse_day_one import HOSPITAL_HEADERS, UNKNOWN_COLUMN, build_export  # noqa: E402
from compliance.audit import AuditLog
from compliance.benchmark import bind_subject, run_benchmark
from compliance.models import Purpose
from extraction.adapters.dataset_his import DatasetHISDataSource, normalise_dates
from extraction.technique import ExtractionTask, LayerFields
from extraction.techniques import CompliantExtractionTechnique, UnconstrainedExtractionTechnique
from interop.layers import HISLayer
from interop.normalise import audit, normalise

pytest.importorskip("openpyxl")

TASK = ExtractionTask(
    task_id="patient-summary", purpose=Purpose.CARE_COORDINATION, single_subject=True,
    needed=[LayerFields(layer=HISLayer.PATIENT_ADMINISTRATION, fields=["mrn", "date_of_birth", "sex"]),
            LayerFields(layer=HISLayer.CLINICAL_EHR, fields=["primary_diagnosis", "medication", "allergy"])],
)


def _maps():
    global_map: dict[str, str] = {}
    for layer, names in HOSPITAL_HEADERS.items():
        if layer is not HISLayer.INFRASTRUCTURE_INTEGRATION:
            global_map.update({theirs: ours for ours, theirs in names.items()})
    global_map.update({theirs: ours for ours, theirs in HOSPITAL_HEADERS[HISLayer.INFRASTRUCTURE_INTEGRATION].items()
                       if theirs != "Patient ID"})
    return global_map, {"audit_trail.csv": {"Patient ID": "subject_mrn"}}


def _source(tmp_path):
    ids = build_export(tmp_path / "export", records=12, seed=3)
    global_map, file_maps = _maps()
    src = DatasetHISDataSource(tmp_path / "export", column_map=global_map, file_maps=file_maps, enforce_handling=False)
    return src, ids


def test_a_header_can_mean_different_fields_in_different_files(tmp_path):
    src, _ = _source(tmp_path)
    # 'Patient ID' is mrn on four layers and subject_mrn on the audit trail.
    assert "mrn" in src._frames[HISLayer.CLINICAL_EHR].columns
    assert "subject_mrn" in src._frames[HISLayer.INFRASTRUCTURE_INTEGRATION].columns
    assert src.confidence[HISLayer.ADMINISTRATIVE_FINANCIAL] == 1.0
    assert src.dropped_columns == {"registration_feb.csv": [UNKNOWN_COLUMN], "registration_jan.csv": [UNKNOWN_COLUMN]}


def test_a_layer_split_across_files_is_concatenated_not_truncated(tmp_path):
    src, _ = _source(tmp_path)
    rows = list(src.fetch(HISLayer.PATIENT_ADMINISTRATION, fields=["mrn"]))
    assert len(rows) == 12                                   # 6 + 6, not 6
    assert src.merged[HISLayer.PATIENT_ADMINISTRATION] == ["registration_feb.csv", "registration_jan.csv"]
    assert "concatenated" in src.describe()


def test_day_first_dates_are_emitted_in_iso_form_for_the_shapers(tmp_path):
    src, _ = _source(tmp_path)
    row = next(iter(src.fetch(HISLayer.PATIENT_ADMINISTRATION, fields=["date_of_birth", "admission_datetime"])))
    assert len(row["date_of_birth"]) == 10 and row["date_of_birth"][4] == "-"
    assert "T" in row["admission_datetime"]
    import pandas as pd
    frame, unparsed = normalise_dates(pd.DataFrame({"date_of_birth": ["14/03/1988", "1988-03-14", "not a date", None]}))
    assert list(frame["date_of_birth"][:2]) == ["1988-03-14", "1988-03-14"]
    assert frame["date_of_birth"][2] == "not a date" and unparsed == {"date_of_birth": 1}
    # And the HL7 PID-7 that comes out is eight digits, not a slashed string.
    out = CompliantExtractionTechnique().extract(src, bind_subject([TASK], src)[0])
    shaped = normalise(out, key="k")
    pid = next(seg for seg in shaped.hl7["patient_administration"][0].split("\r") if seg.startswith("PID"))
    assert pid.split("|")[7].isdigit() and len(pid.split("|")[7]) == 8


def test_nothing_printed_or_written_on_the_dataset_path_carries_a_raw_identifier(tmp_path, capsys):
    src, ids = _source(tmp_path)
    tasks = bind_subject([TASK], src)
    log = AuditLog(tmp_path / "audit.jsonl")
    result = run_benchmark([CompliantExtractionTechnique(), UnconstrainedExtractionTechnique()], tasks, src,
                           dataset_note="rehearsal", audit=log)
    print(result.render_table())
    print(src.describe())
    out = CompliantExtractionTechnique().extract(src, tasks[0])
    shaped = normalise(out, key="k")
    print(shaped.render_summary()); print(audit(out, shaped).one_line())
    print(shaped.sample(HISLayer.PATIENT_ADMINISTRATION))
    written = shaped.to_files(tmp_path / "exports", audit=log)
    print(log.render_tail(5))
    result.to_json_file(tmp_path / "exports", name="benchmark-dataset")
    result.to_markdown_file(tmp_path / "exports", name="benchmark-dataset")

    text = capsys.readouterr().out
    corpus = {p.name: p.read_text(encoding="utf-8", errors="replace") for p in (tmp_path / "exports").iterdir()}
    corpus["audit.jsonl"] = (tmp_path / "audit.jsonl").read_text(encoding="utf-8")
    for what, value in ids.items():
        assert value not in text, f"{what} printed"
        for name, body in corpus.items():
            assert value not in body, f"{what} written to {name}"
    assert written and json.loads((tmp_path / "audit.jsonl").read_text(encoding="utf-8").splitlines()[0])["event"] == "extraction"
