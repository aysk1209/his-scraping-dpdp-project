"""Headline demo: compare extraction techniques on DPDP compliance.

    python scripts/run_benchmark.py

Runs three techniques -- a compliance-aware method (ours), a minimising-but-
undocumented method, and an unconstrained coverage-optimised baseline -- against
a set of extraction tasks over synthetic HIS data, scoring every run with the
same DPDP rule set. Prints the comparison table and writes
docs/benchmark_results/benchmark.{json,md}.

The table is the project's core evidence: compliance distinguishes techniques,
not just careful vs careless configurations of one.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import _present as present
from compliance.benchmark import run_benchmark
from compliance.models import Purpose
from extraction.adapters.mock_his import MockHISDataSource
from extraction.technique import ExtractionTask, LayerFields
from extraction.techniques import DEFAULT_TECHNIQUES
from interop.layers import HISLayer

TASKS = [
    ExtractionTask(
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
    ),
    ExtractionTask(
        task_id="ward-census",
        purpose=Purpose.CARE_COORDINATION,
        needed=[
            LayerFields(
                layer=HISLayer.PATIENT_ADMINISTRATION,
                fields=["mrn", "admission_ward", "admission_datetime"],
            ),
            LayerFields(layer=HISLayer.CLINICAL_EHR, fields=["encounter_datetime"]),
        ],
    ),
    ExtractionTask(
        task_id="medication-review",
        purpose=Purpose.CARE_COORDINATION,
        needed=[
            LayerFields(
                layer=HISLayer.PATIENT_ADMINISTRATION,
                fields=["mrn", "date_of_birth"],
            ),
            LayerFields(
                layer=HISLayer.CLINICAL_EHR,
                fields=["primary_diagnosis", "medication", "allergy"],
            ),
        ],
    ),
]

_SCENARIO = """\
Scenario: a care-coordination assistant reads patient data from the HIS.
Three extraction tasks are defined; three techniques attempt them:
  - compliance-aware (ours)  : pulls only what a task needs, files a full manifest
  - minimising, undocumented : pulls only what a task needs, files no paperwork
  - unconstrained (baseline)  : ignores the task, scrapes every field it can reach
Each run is scored against the same seven DPDP Act 2023 rules."""


def main() -> None:
    records_per_layer, seed = 50, 42
    source = MockHISDataSource(records_per_layer=records_per_layer, seed=seed)
    result = run_benchmark(
        DEFAULT_TECHNIQUES,
        TASKS,
        source,
        dataset_note=f"{records_per_layer} records/layer x 4 layers, seed {seed}",
    )

    print(present.banner("DPDP compliance benchmark - extraction techniques compared"))
    print(_SCENARIO)
    print()
    print(present.sample_records(
        source, [HISLayer.PATIENT_ADMINISTRATION, HISLayer.CLINICAL_EHR]
    ))
    print(present.rule())
    print(result.render_table())
    print(present.rule())
    print(present.wrote(result.to_json_file()))
    print(present.wrote(result.to_markdown_file()))


if __name__ == "__main__":
    main()
