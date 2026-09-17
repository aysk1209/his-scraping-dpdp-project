"""Minimisation on the record axis: a task about one patient reads that
patient's records and no one else's -- scored by DM-01 on evidence the harness
supplies, metered as record excess, and executed through the source's own
means of scoping (a filter in memory, the search box on a portal)."""

from __future__ import annotations

from compliance.benchmark import bind_subject, first_subject, necessary_records, run_benchmark
from compliance.checkers import run_all
from compliance.models import Purpose, RecordScope
from extraction.adapters.mock_his import MockHISDataSource
from extraction.metering import MeteredSource
from extraction.technique import ExtractionTask, LayerFields
from extraction.techniques import CompliantExtractionTechnique, UnconstrainedExtractionTechnique
from extraction.techniques.ai_agent import AIAgentTechnique, build_user_prompt
from extraction.techniques.ai_providers import FakeProvider
from interop.layers import HISLayer

SUMMARY = ExtractionTask(
    task_id="patient-summary", purpose=Purpose.CARE_COORDINATION,
    description="Prepare a clinical summary of a patient for the care team", single_subject=True,
    needed=[LayerFields(layer=HISLayer.PATIENT_ADMINISTRATION, fields=["mrn", "date_of_birth"]),
            LayerFields(layer=HISLayer.CLINICAL_EHR, fields=["primary_diagnosis", "medication"])],
)
CENSUS = ExtractionTask(
    task_id="ward-census", purpose=Purpose.CARE_COORDINATION, description="List who is on each ward",
    needed=[LayerFields(layer=HISLayer.PATIENT_ADMINISTRATION, fields=["mrn", "admission_ward"])],
)


def test_the_subject_is_bound_from_the_source_not_the_task_definition():
    source = MockHISDataSource(records_per_layer=8, seed=5)
    assert SUMMARY.subject is None                      # a task definition never holds a record number
    [bound, census] = bind_subject([SUMMARY, CENSUS], source)
    assert bound.subject == first_subject(source) and bound.subject.startswith("MRN")
    assert census.subject is None                       # a cohort task is not scoped
    assert bound.subject_filter(HISLayer.CLINICAL_EHR) == {"mrn": bound.subject}
    assert bound.subject_filter(HISLayer.INFRASTRUCTURE_INTEGRATION) == {"subject_mrn": bound.subject}
    assert necessary_records(bound, source) == 2        # one record per needed layer is the patient's
    assert necessary_records(census, source) is None


def test_the_compliant_technique_reads_one_patient_and_the_baseline_reads_everyone():
    source = MockHISDataSource(records_per_layer=8, seed=5)
    [task] = bind_subject([SUMMARY], source)
    ours = CompliantExtractionTechnique().extract(source, task)
    assert len(ours.records) == 2
    assert {r["mrn"] for r in ours.rows["patient_administration"]} == {task.subject}
    everyone = UnconstrainedExtractionTechnique().extract(source, task)
    assert len(everyone.records) == 8 * 5


def test_dm01_scores_the_record_axis_from_the_harness_not_the_technique():
    source = MockHISDataSource(records_per_layer=8, seed=5)
    result = run_benchmark([CompliantExtractionTechnique(), UnconstrainedExtractionTechnique()],
                           [SUMMARY, CENSUS], source)
    scores = {s.short: s for s in result.scores}
    ours, base = scores["compliance-aware"], scores["unconstrained"]
    assert ours.per_rule_mean["DM-01"] == 1.0
    assert ours.cost.record_excess == 1.0 and ours.cost.records_necessary == 2
    # The baseline read 40 records for a 2-record job: DM-01 halves its category
    # score with the record score on that task, and the cost table says 20x.
    assert base.cost.record_excess == 20.0
    assert base.per_task["patient-summary"] < base.per_task["ward-census"]
    assert "read 20.0x the records" in result._takeaway()
    assert "rec.excess" in result.render_table() and "Record excess" in result.render_markdown()


def test_a_manifest_without_scope_is_scored_on_fields_alone():
    source = MockHISDataSource(records_per_layer=8, seed=5)
    out = UnconstrainedExtractionTechnique().extract(source, CENSUS)
    assert out.run.scope is None
    unscoped = run_all(out.run, out.records).results[0]
    out.run.scope = RecordScope(records_pulled=40, records_necessary=2)
    scoped = run_all(out.run, out.records).results[0]
    assert scoped.rule_id == "DM-01" and scoped.score < unscoped.score
    assert any("other patients' records" in f for f in scoped.findings)


def test_the_agent_is_told_there_is_a_subject_but_never_who(tmp_path):
    source = MockHISDataSource(records_per_layer=8, seed=5)
    [task] = bind_subject([SUMMARY], source)
    brief = build_user_prompt(task, {HISLayer.PATIENT_ADMINISTRATION: ["mrn"]})
    assert "one patient" in brief and "'subject'" in brief
    assert task.subject not in brief
    # And the brief is the same whichever patient it is: the recording stays valid.
    other = task.model_copy(update={"subject": "MRN0000000"})
    assert build_user_prompt(other, {HISLayer.PATIENT_ADMINISTRATION: ["mrn"]}) == brief

    decision = {
        "fields": ["patient_administration/mrn", "clinical_ehr/primary_diagnosis"], "scope": "all",
        "purpose_specified": True, "secondary_uses": [], "lawful_basis_type": "legitimate_use",
        "lawful_basis_reference": "LU-CARE", "retention_days": 30, "deletion_mechanism": "PURGE-01",
        "transport_encrypted": True, "at_rest_encrypted": True, "access_controlled": True,
        "identifiers_pseudonymised": True, "notice_reference": "NOTICE-REG-2026", "notice_covers_purpose": True,
        "notice_machine_readable": True, "audit_log_enabled": True, "accountable_party": "DPO",
        "processing_record_kept": True, "rationale": "t",
    }
    reads_all = AIAgentTechnique(FakeProvider([decision]), mode="live", recordings_dir=tmp_path / "a")
    assert len(reads_all.extract(source, task).records) == 16
    scoped = AIAgentTechnique(FakeProvider([dict(decision, scope="subject")]), mode="live", recordings_dir=tmp_path / "b")
    assert len(scoped.extract(source, task).records) == 2


def test_the_meter_sees_the_scoped_fetch():
    source = MockHISDataSource(records_per_layer=8, seed=5)
    [task] = bind_subject([SUMMARY], source)
    metered = MeteredSource(source)
    CompliantExtractionTechnique().extract(metered, task)
    assert metered.records == 2 and metered.fetches == 2
