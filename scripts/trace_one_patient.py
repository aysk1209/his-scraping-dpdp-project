"""Walkthrough demo: one synthetic patient, followed through the whole pipeline.

    python scripts/trace_one_patient.py

The benchmark (``scripts/run_benchmark.py``) is the aggregate result: three
techniques, three tasks, one comparison table. This script is the opposite view
-- a single record, shown at every stage, so the score can be checked by hand:

    source record -> task -> field selection -> DPDP categorisation
                  -> compliance manifest -> seven rules -> score

The same patient is put through every technique -- ours, each publicly
available AI agent with a recorded decision, and the coverage-optimised
baseline -- so the difference between 1.000 and the rest is visible field by
field rather than asserted. For an AI agent the walkthrough also replays every
recorded decision for the same brief, so the reader sees whether "just AI"
gives the same answer twice. Ours does, by construction.

Note on the synthetic set: layers are generated independently and carry no
cross-layer patient key yet, so "one patient" here means the first record of
each layer, presented together. That is a property of the synthetic generator,
not of the compliance pipeline -- the scoring path is identical either way.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import _present as present
from compliance.checkers import run_all
from compliance.models import ExtractionRun, Purpose
from compliance.policy import policy_for
from data_synthetic.catalogue import FIELD_CATALOGUE
from extraction.adapters.mock_his import MockHISDataSource
from extraction.technique import ExtractionTask, ExtractionTechnique, LayerFields
from extraction.techniques import (
    CompliantExtractionTechnique,
    UnconstrainedExtractionTechnique,
)
from extraction.techniques.ai_agent import AIAgentTechnique, available_agents
from interop.layers import HISLayer

TASK = ExtractionTask(
    task_id="patient-summary",
    purpose=Purpose.CARE_COORDINATION,
    description="Prepare a clinical summary of a patient for the care team",
    needed=[
        LayerFields(
            layer=HISLayer.PATIENT_ADMINISTRATION,
            fields=["mrn", "date_of_birth", "sex"],
        ),
        LayerFields(
            layer=HISLayer.CLINICAL_EHR,
            fields=["primary_diagnosis", "medication", "allergy"],
        ),
    ],
)


def _needed_map(task: ExtractionTask) -> dict[HISLayer, list[str]]:
    return {item.layer: item.fields for item in task.needed}


def step_1_source(source: MockHISDataSource) -> None:
    print(present.banner("STEP 1  the HIS record  (what the source holds)"))
    print("One synthetic patient, as the data source exposes it. Every value is")
    print("Faker-generated -- no real person, no real hospital.\n")
    for layer in source.layers():
        row = next(iter(source.fetch(layer)))
        print(f"  layer: {layer.value}   ({len(row)} fields)")
        for name, value in row.items():
            print(f"      {name:<22} {value}")
        print()


def step_2_task() -> None:
    print(present.banner("STEP 2  the task  (what the job actually needs)"))
    print("A care-coordination assistant asks for a patient summary. The task")
    print("declares its minimum necessary field set up front -- this declaration")
    print("is what makes 'necessary for the purpose' machine-checkable.\n")
    print(f"  task_id : {TASK.task_id}")
    print(f"  purpose : {TASK.purpose.value}")
    for item in TASK.needed:
        print(f"  needs   : {item.layer.value:<24} {', '.join(item.fields)}")
    policy = policy_for(TASK.purpose)
    allowed = ", ".join(sorted(c.value for c in policy.allowed_categories))
    print(f"\n  purpose policy (src/compliance/policy.py):")
    print(f"      allowed categories : {allowed}")
    print(f"      max retention      : {policy.max_retention_days} days")
    print(f"      pseudonymisation   : required={policy.requires_pseudonymised_identifiers}")


def _col(agent: AIAgentTechnique) -> str:
    return f"{agent.provider_name[:6]}-{'inf' if agent.briefing == 'informed' else 'un'}"


def step_3_selection(source: MockHISDataSource, agents: list[AIAgentTechnique]) -> None:
    print(present.banner("STEP 3  field selection + DPDP categorisation"))
    print("Each technique picks fields off the same record. The field catalogue")
    print("(src/data_synthetic/catalogue.py) maps every field name to a DPDP")
    print("category; the purpose policy says which categories are in scope.")
    if agents:
        print("An AI agent's column is its first recorded decision for this brief;")
        print("'un' = unaided, 'inf' = told the Act. Ours is read off the purpose policy.")
    print()

    needed = _needed_map(TASK)
    allowed = policy_for(TASK.purpose).allowed_categories
    picks: dict[str, dict[HISLayer, list[str]]] = {}
    for agent in agents:
        agent.sample = 0
        picks[_col(agent)] = agent.decide(source, TASK).selection()

    cols = ["ours", *picks, "baseline"]
    header = (
        f"  {'field':<22} {'DPDP category':<19} {'in scope':<9} "
        + " ".join(f"{c:<10}" for c in cols)
    )
    for layer in source.layers():
        print(f"  layer: {layer.value}")
        print(header)
        print(f"  {'-' * 22} {'-' * 19} {'-' * 9} " + " ".join("-" * 10 for _ in cols))
        for name, category in FIELD_CATALOGUE[layer].items():
            scope = "yes" if category in allowed else "NO"
            cells = ["take" if name in needed.get(layer, []) else "."]
            for col in picks:
                cells.append("take" if name in picks[col].get(layer, []) else ".")
            cells.append("take")  # the baseline pulls every field of every layer
            print(
                f"  {name:<22} {category.value:<19} {scope:<9} "
                + " ".join(f"{c:<10}" for c in cells)
            )
        print()

    leaked = [
        (layer, name, cat.value)
        for layer in source.layers()
        for name, cat in FIELD_CATALOGUE[layer].items()
        if cat not in allowed
    ]
    print("  Fields the baseline takes that no care-coordination purpose permits:")
    for layer, name, cat in leaked:
        print(f"      {layer.value}.{name}  ->  {cat}")
    print(present.takeaway(
        "This table is the whole minimisation argument: 6 fields versus "
        f"{sum(len(FIELD_CATALOGUE[l]) for l in source.layers())}, "
        f"{len(leaked)} of them outside the purpose entirely."
    ))


def _manifest_lines(run: ExtractionRun) -> list[str]:
    basis = (
        f"{run.lawful_basis.type.value} (ref: {run.lawful_basis.reference})"
        if run.lawful_basis
        else "NONE DECLARED"
    )
    sec = run.security
    notice = run.notice.reference if run.notice else "NONE"
    gov = run.governance
    return [
        f"  purpose declared   : {run.purpose_specified}",
        f"  lawful basis       : {basis}",
        f"  retention          : {run.retention_days or 'NONE'} days",
        f"  deletion mechanism : {run.deletion_mechanism or 'NONE'}",
        f"  security           : transport={sec.transport_encrypted} "
        f"at_rest={sec.at_rest_encrypted} access_control={sec.access_controlled} "
        f"pseudonymised={sec.identifiers_pseudonymised}",
        f"  notice             : {notice}",
        f"  governance         : audit_log={gov.audit_log_enabled} "
        f"accountable={gov.accountable_party or 'NONE'} "
        f"record_kept={gov.processing_record_kept}",
    ]


def run_technique(technique: ExtractionTechnique, source: MockHISDataSource) -> float:
    if isinstance(technique, AIAgentTechnique):
        technique.sample = 0
    output = technique.extract(source, TASK)
    print(present.banner(f"STEPS 4-6  technique: {technique.name}"))

    if isinstance(technique, AIAgentTechnique) and technique.last_decision is not None:
        d = technique.last_decision
        print(f"The agent was briefed with the job, the purpose and the field names --")
        print(f"never a value -- and decided ({technique.last_source}):")
        for layer, names in d.selection().items():
            print(f"  {layer.value:<26} {', '.join(names)}")
        if d.unknown_fields():
            print(f"  (asked for fields that do not exist, dropped: {', '.join(d.unknown_fields())})")
        if d.rationale.strip():
            print(f"  its reason: \"{d.rationale.strip()}\"")
        print()

    print("STEP 4  the manifest this technique emits for its own run")
    print("        (the technique declares its own compliance posture -- that is")
    print("         why compliance is a property of the method, not a wrapper)\n")
    for line in _manifest_lines(output.run):
        print(line)

    print("\nSTEP 5  what actually came out")
    for record in output.records:
        cats = ", ".join(sorted(c.value for c in record.field_categories))
        print(f"  {record.source_layer:<26} categories: {cats}")

    print("\nSTEP 6  the seven DPDP rules score it, each with a stated reason\n")
    report = run_all(output.run, output.records)
    print(report.render_table())
    print(present.wrote(report.to_json_file()))
    print(present.wrote(report.to_markdown_file()))

    if isinstance(technique, AIAgentTechnique):
        _replay_other_samples(technique, source, report.compliance_score)
    return report.compliance_score


def _replay_other_samples(agent: AIAgentTechnique, source: MockHISDataSource, first: float) -> None:
    """Same brief, every recorded decision: does the agent agree with itself?"""

    samples = agent.recorded_samples(TASK.task_id)
    if len(samples) < 2:
        print("\n  (one recorded decision for this brief; record more with --repeats to see variance)")
        return
    print(f"\nSTEP 6b the same brief was put to {agent.provider_name} {len(samples)} times. Each answer:")
    base_fields = None
    base_manifest = None
    for i in range(len(samples)):
        agent.sample = i
        out = agent.extract(source, TASK)
        fields = {f"{l.value}/{n}" for l, names in agent.last_decision.selection().items() for n in names}
        manifest = out.run.model_dump(mode="json", exclude={"run_id", "created_at"})
        score = run_all(out.run, out.records).compliance_score
        if base_fields is None:
            base_fields, base_manifest = fields, manifest
            print(f"  run {i + 1}: {len(fields)} fields, score {score:.3f}   (the run above)")
            continue
        added, removed = sorted(fields - base_fields), sorted(base_fields - fields)
        diff = []
        if added:
            diff.append("+" + ", ".join(added))
        if removed:
            diff.append("-" + ", ".join(removed))
        if manifest != base_manifest:
            changed = sorted(k for k in manifest if manifest[k] != base_manifest.get(k))
            diff.append("manifest differs: " + ", ".join(changed))
        print(f"  run {i + 1}: {len(fields)} fields, score {score:.3f}   "
              + ("identical to run 1" if not diff else "; ".join(diff)))
    agent.sample = 0


def main() -> None:
    source = MockHISDataSource(records_per_layer=1, seed=42)

    print(present.banner("ONE PATIENT, END TO END: source -> rules -> score"))
    print("The benchmark shows the aggregate. This shows the mechanism, on a")
    print("single record, so every number can be checked by hand.")

    agents = available_agents(tasks=[TASK])

    step_1_source(source)
    step_2_task()
    step_3_selection(source, agents)

    techniques = [CompliantExtractionTechnique(), *agents, UnconstrainedExtractionTechnique()]
    scores: dict[str, float] = {}
    for technique in techniques:
        scores[technique.name] = run_technique(technique, source)

    print(present.banner("STEP 7  verdict on this one patient"))
    print(f"  {'technique':<40} {'score':>6}  reproduces its own decision?")
    for technique in techniques:
        name = technique.name
        if isinstance(technique, AIAgentTechnique):
            n = len(technique.recorded_samples(TASK.task_id))
            distinct = len({__import__('json').dumps(x, sort_keys=True)
                            for x in technique.recorded_samples(TASK.task_id)})
            repro = (f"{n - distinct + 1} of {n} runs agreed" if n > 1 else "one run recorded")
        else:
            repro = "yes -- rules, not sampling"
        print(f"  {name:<40} {scores[name]:>6.3f}  {repro}")
    gap = max(scores.values()) - min(scores.values())
    if not agents:
        print("\n  No AI-agent recordings yet: set a provider key and run scripts/record_ai_agents.py")
        print("  to put Claude / GPT / Gemini through this same patient.")
    print(present.takeaway(
        f"Same patient, same source, same seven rules -- a {gap:.3f} gap, "
        "traceable to specific fields taken and specific paperwork missing."
        + (" The rule-driven technique gives the same answer every time; an agent's is a sample."
           if agents else "")
    ))


if __name__ == "__main__":
    main()
