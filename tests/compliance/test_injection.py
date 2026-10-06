"""Instructions planted in the request: ours ignores them; the trap check sees the record scope."""

from __future__ import annotations

from compliance.audit import AuditLog
from compliance.benchmark import bind_subject, run_benchmark
from extraction.adapters.mock_his import MockHISDataSource
from extraction.techniques.compliant import CompliantExtractionTechnique
from extraction.techniques.unconstrained import UnconstrainedExtractionTechnique
from scripts.run_benchmark import INJECTION_TASKS, TASKS


def test_the_injection_set_is_lawful_apart_from_the_planted_text():
    ids = {t.task_id for t in TASKS}
    for task in INJECTION_TASKS:
        assert task.task_id not in ids and task.trap and task.single_subject
        assert any(w in task.description.upper() for w in ("NOTE TO", "SYSTEM INSTRUCTION", "IMPORTANT"))


def test_ours_holds_every_planted_instruction_and_the_baseline_none(tmp_path):
    source = MockHISDataSource(records_per_layer=6, seed=8)
    result = run_benchmark([CompliantExtractionTechnique(), UnconstrainedExtractionTechnique()],
                           bind_subject(INJECTION_TASKS, source), source, audit=AuditLog(tmp_path / "a.jsonl"))
    s = {x.short: x for x in result.scores}
    assert s["compliance-aware"].traps_resisted == s["compliance-aware"].traps == len(INJECTION_TASKS)
    assert s["unconstrained"].traps_resisted == 0


def test_reading_every_patient_breaks_a_trap_even_with_lawful_fields(tmp_path):
    source = MockHISDataSource(records_per_layer=6, seed=8)
    result = run_benchmark([CompliantExtractionTechnique(without="scope")],
                           bind_subject(INJECTION_TASKS, source), source, audit=AuditLog(tmp_path / "a.jsonl"))
    assert result.scores[0].traps_resisted == 0
