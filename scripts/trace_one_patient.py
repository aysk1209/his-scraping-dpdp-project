"""Walkthrough demo: one synthetic patient, followed through the whole pipeline.

    python scripts/trace_one_patient.py

The benchmark (``scripts/run_benchmark.py``) is the aggregate result: three
techniques, three tasks, one comparison table. This script is the opposite view
-- a single record, shown at every stage, so the score can be checked by hand:

    source record -> task -> field selection -> DPDP categorisation
                  -> compliance manifest -> seven rules -> score

The same patient is put through two techniques (ours and the coverage-optimised
baseline) so the difference between 1.000 and ~0.13 is visible field by field
rather than asserted.

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
from interop.layers import HISLayer

TASK = ExtractionTask(
    task_id="patient-summary",
    purpose=Purpose.CARE_COORDINATION,
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


def step_3_selection(source: MockHISDataSource) -> None:
    print(present.banner("STEP 3  field selection + DPDP categorisation"))
    print("Each technique picks fields off the same record. The field catalogue")
    print("(src/data_synthetic/catalogue.py) maps every field name to a DPDP")
    print("category; the purpose policy says which categories are in scope.\n")

    needed = _needed_map(TASK)
    allowed = policy_for(TASK.purpose).allowed_categories

    header = (
        f"  {'field':<22} {'DPDP category':<19} {'in scope':<9} "
        f"{'ours':<6} {'baseline':<9}"
    )
    for layer in source.layers():
        print(f"  layer: {layer.value}")
        print(header)
        print(f"  {'-' * 22} {'-' * 19} {'-' * 9} {'-' * 6} {'-' * 9}")
        for name, category in FIELD_CATALOGUE[layer].items():
            ours = "take" if name in needed.get(layer, []) else "."
            base = "take"  # the baseline pulls every field of every layer
            scope = "yes" if category in allowed else "NO"
            print(
                f"  {name:<22} {category.value:<19} {scope:<9} "
                f"{ours:<6} {base:<9}"
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
    output = technique.extract(source, TASK)
    print(present.banner(f"STEPS 4-6  technique: {technique.name}"))

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
    return report.compliance_score


def main() -> None:
    source = MockHISDataSource(records_per_layer=1, seed=42)

    print(present.banner("ONE PATIENT, END TO END: source -> rules -> score"))
    print("The benchmark shows the aggregate. This shows the mechanism, on a")
    print("single record, so every number can be checked by hand.")

    step_1_source(source)
    step_2_task()
    step_3_selection(source)

    scores: dict[str, float] = {}
    for technique in (
        CompliantExtractionTechnique(),
        UnconstrainedExtractionTechnique(),
    ):
        scores[technique.name] = run_technique(technique, source)

    print(present.banner("STEP 7  verdict on this one patient"))
    for name, score in scores.items():
        print(f"  {name:<30} {score:.3f}")
    gap = max(scores.values()) - min(scores.values())
    print(present.takeaway(
        f"Same patient, same source, same seven rules -- a {gap:.3f} gap, "
        "traceable to specific fields taken and specific paperwork missing."
    ))


if __name__ == "__main__":
    main()
