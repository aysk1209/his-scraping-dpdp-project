"""A leaked export, assessed from the audit log: whose data, what kind, in what form."""

from __future__ import annotations

from datetime import timedelta

import pytest

from compliance.audit import AuditLog, fields_by_layer
from compliance.benchmark import bind_subject
from compliance.breach import assess, resolve
from extraction.adapters.mock_his import MockHISDataSource
from extraction.metering import MeteredSource
from extraction.techniques.compliant import CompliantExtractionTechnique
from extraction.techniques.unconstrained import UnconstrainedExtractionTechnique
from interop.layers import HISLayer
from interop.normalise import normalise
from scripts.run_benchmark import TASKS

LEAK = "an export folder was copied to a lost drive"


@pytest.fixture(scope="module")
def leaked(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("breach")
    source = MockHISDataSource(records_per_layer=10, seed=4)
    [task] = bind_subject([next(t for t in TASKS if t.task_id == "patient-summary")], source)
    log, exports, runs = AuditLog(tmp / "audit.jsonl"), tmp / "exports", {}
    for label, technique in (("ours", CompliantExtractionTechnique()), ("base", UnconstrainedExtractionTechnique())):
        meter = MeteredSource(source)
        out = technique.extract(meter, task)
        log.extraction(out.run, technique=technique.name, records=len(out.records),
                       fields=fields_by_layer({(lv, f) for lv, rows in out.rows.items() for r in rows for f in r}),
                       rows=out.rows, scoped_to=meter.subject_scope())
        normalise(out).to_files(exports, audit=log)
        runs[label] = out.run.run_id
    register = [r["mrn"] for r in source.fetch(HISLayer.PATIENT_ADMINISTRATION, fields=["mrn"])]
    return {"log": log, "exports": exports, "runs": runs, "register": register, "subject": task.subject}


def _assess(w, label, **kw):
    return assess([w["runs"][label]], description=LEAK, log=w["log"], export_dirs=[w["exports"]], **kw)


def test_ours_exposes_one_patient_as_tokens_the_baseline_everyone_raw(leaked):
    ours, base = _assess(leaked, "ours"), _assess(leaked, "base")
    assert len(ours.affected) == 1 and ours.unattributed == 0
    assert not ours.raw_identifiers() and ours.severity().startswith("moderate")
    assert len(base.affected) == len(leaked["register"])
    assert base.raw_identifiers() and base.severity().startswith("high")
    assert set(ours.categories()) < set(base.categories())


def test_only_the_key_holder_turns_tokens_into_patients(leaked):
    assert resolve(_assess(leaked, "ours"), leaked["register"]) == [leaked["subject"]]


def test_the_notices_name_no_one_and_do_not_contradict_the_pseudonymisation(leaked):
    ours = _assess(leaked, "ours")
    for text in (ours.to_board(), ours.to_patient()):
        assert not any(mrn in text for mrn in leaked["register"])
    assert "details that identify you" not in ours.to_patient()
    assert "details that identify you" in _assess(leaked, "base").to_patient()


def test_an_export_past_its_erasure_date_is_a_finding(leaked):
    now = _assess(leaked, "ours")
    late = _assess(leaked, "ours", now=now.discovered_at + timedelta(days=31))
    assert not any(e.overdue for e in now.exports)
    assert all(e.overdue for e in late.exports) and "past their erasure date" in late.to_board()


def test_a_file_the_log_never_saw_is_reported_not_ignored(leaked):
    a = assess(["no-such-run"], description=LEAK, log=leaked["log"])
    assert a.unknown == ["no-such-run"] and "no record of" in a.to_board()


def test_the_meter_sees_a_scoped_run_and_an_unscoped_one():
    source = MockHISDataSource(records_per_layer=5, seed=1)
    meter = MeteredSource(source)
    list(meter.fetch(HISLayer.CLINICAL_EHR, fields=["medication"], where={"mrn": "X"}))
    assert meter.subject_scope() == "X"
    list(meter.fetch(HISLayer.CLINICAL_EHR, fields=["medication"]))
    assert meter.subject_scope() is None
