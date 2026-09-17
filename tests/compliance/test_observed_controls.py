"""The controls the pipeline demonstrates rather than declares.

An audit log written by the harness, an export scheduled for erasure and
purged, a transport observed rather than asserted -- and a register that says
which of its controls rest on such evidence and which on the deployment's word.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from compliance.audit import AuditLog
from compliance.benchmark import run_benchmark
from compliance.capabilities import DEFAULT_REGISTER
from compliance.checkers import run_all
from compliance.models import Purpose
from compliance.retention import purge_expired, schedules
from compliance.veracity import substantiate, verify
from extraction.adapters.mock_his import MockHISDataSource
from extraction.technique import ExtractionTask, LayerFields
from extraction.techniques import CompliantExtractionTechnique, UnconstrainedExtractionTechnique
from interop.layers import HISLayer
from interop.normalise import normalise

TASK = ExtractionTask(
    task_id="t", purpose=Purpose.CARE_COORDINATION,
    needed=[LayerFields(layer=HISLayer.PATIENT_ADMINISTRATION, fields=["mrn", "date_of_birth"]),
            LayerFields(layer=HISLayer.CLINICAL_EHR, fields=["primary_diagnosis"])],
)


class _PlainHttpSource(MockHISDataSource):
    """An in-memory source pretending to have been read over plain http."""

    @property
    def transport_secure(self) -> bool | None:
        return False


def test_the_register_separates_demonstrated_from_attested():
    ids = {c.id for c in DEFAULT_REGISTER.demonstrated()}
    assert ids == {"TLS", "PSEUDO-EXPORT", "PURGE-01", "AUDIT-LOG"}
    assert {c.id for c in DEFAULT_REGISTER.attested()} >= {"ENC-REST", "ACL-STORE", "DPO", "ROPA", "NOTICE-REG-2026"}
    text = "\n".join(DEFAULT_REGISTER.evidence_lines())
    assert "demonstrated by the pipeline" in text and "attested by the deployment" in text


def test_every_run_is_audit_logged_by_the_harness_not_the_technique(tmp_path):
    audit = AuditLog(tmp_path / "audit.jsonl")
    source = MockHISDataSource(records_per_layer=3, seed=1)
    result = run_benchmark([CompliantExtractionTechnique(), UnconstrainedExtractionTechnique()],
                           [TASK], source, repeats=2, audit=audit)
    events = audit.entries()
    assert len(events) == 4 and all(e.event == "extraction" for e in events)
    ours = [e for e in events if e.run_id == "t--compliance-aware"]
    assert ours and ours[0].fields == {"patient_administration": ["date_of_birth", "mrn"],
                                       "clinical_ehr": ["primary_diagnosis"]}
    assert ours[0].records == 6 and len(ours[0].manifest_sha256) == 16
    assert audit.logged("t--compliance-aware") and not audit.logged("never-ran")
    assert result.audit_events == 4 and result.audit_log.endswith("audit.jsonl")
    # No value in the log: field names and counts only.
    text = (tmp_path / "audit.jsonl").read_text(encoding="utf-8")
    for row in source.fetch(HISLayer.PATIENT_ADMINISTRATION):
        assert row["mrn"] not in text
        break


def test_substantiated_claims_are_split_into_demonstrated_and_attested():
    source = MockHISDataSource(records_per_layer=3, seed=1)
    out = CompliantExtractionTechnique().extract(source, TASK)
    report = verify(out.run, DEFAULT_REGISTER)
    assert report.unsubstantiated == []
    # TLS, pseudonymisation, PURGE-01 and AUDIT-LOG are demonstrated; the rest attested.
    assert report.demonstrated == 4
    assert report.attested == report.declared - 4
    scores = {s.short: s for s in run_benchmark([CompliantExtractionTechnique()], [TASK], source).scores}
    assert scores["compliance-aware"].demonstrated == 4 and scores["compliance-aware"].attested > 0
    assert "demonstrated by the pipeline" in run_benchmark([CompliantExtractionTechnique()], [TASK], source).render_table()


def test_a_transport_claim_is_checked_against_what_was_observed():
    plain = _PlainHttpSource(records_per_layer=3, seed=1)
    # The compliant technique reads the observation and does not claim TLS.
    out = CompliantExtractionTechnique().extract(plain, TASK)
    assert out.run.security.transport_encrypted is False
    assert run_all(out.run, out.records).compliance_score < 1.0
    assert UnconstrainedExtractionTechnique().extract(plain, TASK).run.security.transport_encrypted is False
    # A manifest that claims it anyway is unsubstantiated, register or no register.
    claimed = out.run.model_copy(update={"security": out.run.security.model_copy(update={"transport_encrypted": True})})
    report = verify(claimed, DEFAULT_REGISTER, {"transport_encrypted": False})
    bad = {c.control: c.note for c in report.unsubstantiated}
    assert "transport encryption" in bad and "observed otherwise" in bad["transport encryption"]
    assert substantiate(claimed, DEFAULT_REGISTER, {"transport_encrypted": False}).security.transport_encrypted is False
    result = run_benchmark([CompliantExtractionTechnique()], [TASK], plain)
    assert result.observed_transport is False and "PLAIN" in result.render_table()
    # In memory there is no transport to observe, and nothing is claimed either way.
    assert MockHISDataSource(records_per_layer=1).transport_secure is None
    assert run_benchmark([CompliantExtractionTechnique()], [TASK], MockHISDataSource(records_per_layer=1)).observed_transport is None


def test_exports_are_scheduled_for_erasure_and_purged_when_due(tmp_path):
    audit = AuditLog(tmp_path / "audit.jsonl")
    source = MockHISDataSource(records_per_layer=3, seed=1)
    out = CompliantExtractionTechnique().extract(source, TASK)
    shaped = normalise(out, key="k")
    written = shaped.to_files(tmp_path / "exports", audit=audit)
    assert any(p.name.endswith(".retention.json") for p in written)
    [sched] = schedules(tmp_path / "exports")
    assert sched.retention_days == 30 and sched.delete_after is not None
    assert sched.delete_after - sched.written_at == timedelta(days=30)
    assert [e.event for e in audit.entries()] == ["export"]

    # Not yet due: nothing goes. Due: everything goes, and the purge is logged.
    assert purge_expired(tmp_path / "exports", audit=audit) == []
    later = datetime.now(timezone.utc) + timedelta(days=31)
    would = purge_expired(tmp_path / "exports", now=later, audit=audit, dry_run=True)
    assert len(would) == 3 and all(p.exists() for p in would)
    erased = purge_expired(tmp_path / "exports", now=later, audit=audit)
    assert len(erased) == 3 and not any(p.exists() for p in erased)
    assert schedules(tmp_path / "exports") == []
    assert [e.event for e in audit.entries()] == ["export", "purge"]
    assert "erased 3 file(s) after 30 d" in audit.entries()[-1].note


def test_an_export_without_a_declared_retention_cannot_be_scheduled(tmp_path):
    source = MockHISDataSource(records_per_layer=3, seed=1)
    out = UnconstrainedExtractionTechnique().extract(source, TASK)      # declares no retention
    shaped = normalise(out, key="k")
    shaped.to_files(tmp_path, audit=AuditLog(tmp_path / "a.jsonl"))
    [sched] = schedules(tmp_path)
    assert sched.delete_after is None and "cannot be scheduled" in sched.one_line()
    assert purge_expired(tmp_path, now=datetime.now(timezone.utc) + timedelta(days=10_000)) == []
