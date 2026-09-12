"""Demo: the same extraction is lawful for one purpose and not for another.

    python scripts/compare_purposes.py

The benchmark demo (`run_benchmark.py`) varies the technique and holds the
purpose fixed. This one does the reverse: it takes a single, unchanged extraction
and scores it against every purpose the policy recognises.

Two pulls are shown, in opposite directions:

  - a care-coordination pull (identifiers + clinical), scored under billing;
  - a billing pull (identifiers + financial + contact), scored under care.

Each is fully compliant for its own purpose and non-compliant for the other, and
for *different* reasons. That is the point: the purposes are not ranked from
strict to lax, and "out of scope" does not mean "more sensitive" -- it means not
necessary for this purpose. A single-purpose policy could never show it.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import _present as present
from compliance.models import Purpose
from compliance.purpose_matrix import score_across_purposes
from extraction.adapters.mock_his import MockHISDataSource
from extraction.technique import ExtractionTask, LayerFields
from extraction.techniques.compliant import CompliantExtractionTechnique
from interop.layers import HISLayer

CARE_TASK = ExtractionTask(
    task_id="care-pull",
    purpose=Purpose.CARE_COORDINATION,
    needed=[
        LayerFields(
            layer=HISLayer.PATIENT_ADMINISTRATION,
            fields=["mrn", "date_of_birth", "admission_ward"],
        ),
        LayerFields(
            layer=HISLayer.CLINICAL_EHR,
            fields=["primary_diagnosis", "medication", "allergy"],
        ),
    ],
)

BILLING_TASK = ExtractionTask(
    task_id="billing-pull",
    purpose=Purpose.BILLING_SETTLEMENT,
    needed=[
        LayerFields(
            layer=HISLayer.PATIENT_ADMINISTRATION,
            fields=["mrn", "email", "street_address", "admission_ward"],
        ),
        LayerFields(
            layer=HISLayer.ADMINISTRATIVE_FINANCIAL,
            fields=["invoice_id", "billed_amount", "payer_name"],
        ),
    ],
)

_SCENARIO = """\
Scenario: one hospital, two entirely legitimate jobs.

  care coordination  - a clinician needs the patient's diagnosis and medication
  billing settlement - the accounts office needs the invoice and where to send it

Both pulls are performed by the SAME compliance-aware technique, which files a
full manifest each time. Each is then scored against BOTH purposes, changing
nothing but the purpose itself."""


def main() -> None:
    source = MockHISDataSource(records_per_layer=25, seed=42)
    technique = CompliantExtractionTechnique()

    print(present.banner("Purpose limitation - the same pull, judged two ways"))
    print(_SCENARIO)

    billing_output = None
    for task in (CARE_TASK, BILLING_TASK):
        output = technique.extract(source, task)
        if task is BILLING_TASK:
            billing_output = output
        matrix = score_across_purposes(output.run, output.records)
        print(present.rule())
        print(matrix.render_table())
        print()
        print(present.wrote(matrix.to_json_file()))
        print(present.wrote(matrix.to_markdown_file()))

    # Third case: scope is not the only thing a purpose fixes. Billing carries an
    # audit obligation, so a full year of retention is legitimate for it -- and
    # unlawful for care coordination, whose ceiling is 90 days. Same data, same
    # manifest, a different rule failing for a different reason.
    assert billing_output is not None
    long_hold = billing_output.run.model_copy(
        update={
            "run_id": "billing-pull--year-retention",
            "retention_days": 365,
            "deletion_mechanism": "purge at end of statutory audit retention",
        }
    )
    matrix = score_across_purposes(long_hold, billing_output.records)
    print(present.rule())
    print(matrix.render_table())
    print()
    print(present.wrote(matrix.to_json_file()))
    print(present.wrote(matrix.to_markdown_file()))

    print(present.rule())
    print(
        "Neither purpose is stricter than the other. Care coordination may see\n"
        "clinical data and not financial data; billing may see financial data and\n"
        "not clinical data, and may hold it four times as long. A technique cannot\n"
        "be 'compliant' in the abstract -- only compliant for a stated purpose."
    )


if __name__ == "__main__":
    main()
