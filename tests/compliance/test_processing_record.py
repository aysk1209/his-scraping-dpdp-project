"""The record of processing activities is derived from the audit log, so it cannot fall behind."""

from __future__ import annotations

from compliance.audit import AuditLog
from compliance.benchmark import bind_subject, run_benchmark
from compliance.capabilities import DEFAULT_REGISTER
from compliance.processing_record import build_record
from extraction.adapters.mock_his import MockHISDataSource
from extraction.techniques.compliant import CompliantExtractionTechnique
from scripts.run_benchmark import TASKS


def test_the_record_matches_what_ran_and_names_no_one(tmp_path):
    source = MockHISDataSource(records_per_layer=6, seed=2)
    log = AuditLog(tmp_path / "a.jsonl")
    run_benchmark([CompliantExtractionTechnique()], bind_subject(TASKS, source), source, audit=log)
    record = build_record(log)
    by = {a.purpose: a for a in record.activities}
    assert sum(a.runs for a in record.activities) == len(TASKS)
    assert by["billing_settlement"].categories.keys() <= {"direct_identifier", "financial"}
    assert "clinical" not in by["patient_registration"].categories
    assert all(a.lawful_basis.startswith("LU-") for a in record.activities)
    text = record.render_markdown()
    mrns = [r["mrn"] for r in source.fetch(next(iter(source.layers())), fields=["mrn"])]
    assert not any(m in text for m in mrns)


def test_the_register_now_demonstrates_the_record():
    assert DEFAULT_REGISTER.processing_record.demonstrated
    assert len(DEFAULT_REGISTER.demonstrated()) == 5
