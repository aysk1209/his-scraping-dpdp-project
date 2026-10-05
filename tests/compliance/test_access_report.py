"""A patient's access request, answered from the audit log.

The log names whom each run read, as keyed tokens; the answer is built from the
log and the export sidecars; neither ever holds a record number or a value.
"""

from __future__ import annotations

import pytest

from compliance.access_report import access_summary, mask
from compliance.audit import AuditLog, subject_token
from compliance.benchmark import bind_subject, first_subject, run_benchmark
from extraction.adapters.mock_his import MockHISDataSource
from extraction.techniques.compliant import CompliantExtractionTechnique
from extraction.techniques.unconstrained import UnconstrainedExtractionTechnique
from interop.layers import HISLayer
from interop.normalise import normalise
from scripts.run_benchmark import TASKS


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("access")
    source = MockHISDataSource(records_per_layer=12, seed=9)
    log = AuditLog(tmp / "audit.jsonl")
    ours, baseline = CompliantExtractionTechnique(), UnconstrainedExtractionTechnique()
    tasks = bind_subject(TASKS, source)
    run_benchmark([ours, baseline], tasks, source, audit=log)
    summary = next(t for t in tasks if t.task_id == "patient-summary")
    normalise(ours.extract(source, summary)).to_files(tmp / "exports", audit=log)
    mrns = [r["mrn"] for r in source.fetch(HISLayer.PATIENT_ADMINISTRATION, fields=["mrn"])]
    return {"log": log, "exports": tmp / "exports", "patient": first_subject(source),
            "other": mrns[5], "ours": ours.name, "baseline": baseline.name}


def test_the_log_names_patients_only_as_tokens(world):
    text = world["log"].path.read_text(encoding="utf-8")
    assert world["patient"] not in text and world["other"] not in text
    assert subject_token(world["patient"]) in text


def test_the_patient_a_task_was_about_gets_every_run_that_read_them(world):
    s = access_summary(world["patient"], log=world["log"], export_dirs=[world["exports"]])
    ours = [a for a in s.activities if a.technique == world["ours"]]
    assert {a.purpose for a in ours} == {"care_coordination", "billing_settlement", "patient_registration"}
    exported = [a for a in ours if a.exported]
    assert exported and exported[0].pseudonymised and exported[0].erase_after is not None
    text = s.render()
    assert world["patient"] not in text and mask(world["patient"]) in text


def test_ours_reads_a_bystander_only_for_whole_ward_tasks_the_baseline_for_all(world):
    s = access_summary(world["other"], log=world["log"])
    ours = {a.run_id for a in s.activities if a.technique == world["ours"]}
    base = {a.run_id for a in s.activities if a.technique == world["baseline"]}
    assert 0 < len(ours) < len(base) == len(TASKS)


def test_a_stranger_gets_an_honest_nothing(world):
    s = access_summary("MRN0000000", log=world["log"])
    assert s.activities == []
    assert "records no extraction" in s.render()


def test_mask_keeps_enough_to_match_a_slip_and_no_more():
    assert mask("MRN2867825") == "MRN*****25"
    assert mask("1234") == "****"
