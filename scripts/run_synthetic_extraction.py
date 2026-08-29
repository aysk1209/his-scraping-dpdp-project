"""End-to-end demo: synthetic HIS records -> field-selective extraction ->
DPDP compliance score.

    python scripts/run_synthetic_extraction.py

Same compliant / partial / careless spread as ``scripts/score_extraction_run.py``,
but the extracted records now come from the synthetic generator via
``MockHISDataSource``, and field categories are derived from the catalogue
rather than hand-written. Writes JSON + Markdown artifacts to
docs/benchmark_results/.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from compliance.checkers import run_all
from compliance.models import (
    ExtractedRecord,
    ExtractionRun,
    Governance,
    LawfulBasis,
    LawfulBasisType,
    Notice,
    Purpose,
    SecurityPosture,
)
from data_synthetic.catalogue import categories_for_fields, fields_for
from extraction.adapters.mock_his import MockHISDataSource
from interop.layers import HISLayer

# Fields a care-coordination purpose actually needs -- all within policy scope.
IN_SCOPE_SELECTION: dict[HISLayer, list[str]] = {
    HISLayer.PATIENT_ADMINISTRATION: [
        "mrn",
        "date_of_birth",
        "sex",
        "admission_ward",
        "admission_datetime",
    ],
    HISLayer.CLINICAL_EHR: [
        "primary_diagnosis",
        "medication",
        "lab_result",
        "allergy",
        "encounter_datetime",
    ],
}


def _extract(source: MockHISDataSource, selection: dict[HISLayer, list[str]]) -> list[ExtractedRecord]:
    records: list[ExtractedRecord] = []
    for layer, fields in selection.items():
        for row in source.fetch(layer, fields=fields):
            records.append(
                ExtractedRecord(
                    source_layer=layer.value,
                    field_categories=categories_for_fields(layer, row.keys()),
                )
            )
    return records


def compliant(source: MockHISDataSource) -> tuple[ExtractionRun, list[ExtractedRecord]]:
    run = ExtractionRun(
        run_id="synthetic-compliant",
        purpose=Purpose.CARE_COORDINATION,
        lawful_basis=LawfulBasis(
            type=LawfulBasisType.LEGITIMATE_USE,
            reference="s.7 legitimate use -- provision of medical services",
        ),
        retention_days=60,
        deletion_mechanism="scheduled purge job (daily), audited",
        security=SecurityPosture(
            transport_encrypted=True,
            at_rest_encrypted=True,
            access_controlled=True,
            identifiers_pseudonymised=True,
        ),
        notice=Notice(
            reference="patient privacy notice, acknowledged at registration",
            covers_purpose=True,
            machine_readable=True,
        ),
        governance=Governance(
            audit_log_enabled=True,
            accountable_party="hospital Data Protection Officer",
            processing_record_kept=True,
        ),
    )
    return run, _extract(source, IN_SCOPE_SELECTION)


def partial(source: MockHISDataSource) -> tuple[ExtractionRun, list[ExtractedRecord]]:
    """Same tight field selection as the compliant run, but a sloppy manifest:
    consent with no reference, no deletion mechanism, half the safeguards, and
    no notice or governance recorded."""

    run = ExtractionRun(
        run_id="synthetic-partial",
        purpose=Purpose.CARE_COORDINATION,
        lawful_basis=LawfulBasis(type=LawfulBasisType.CONSENT, reference=None),
        retention_days=45,
        deletion_mechanism=None,
        security=SecurityPosture(transport_encrypted=True, at_rest_encrypted=True),
    )
    return run, _extract(source, IN_SCOPE_SELECTION)


def careless(source: MockHISDataSource) -> tuple[ExtractionRun, list[ExtractedRecord]]:
    everything = {layer: fields_for(layer) for layer in source.layers()}
    run = ExtractionRun(
        run_id="synthetic-careless",
        purpose=Purpose.CARE_COORDINATION,
        purpose_specified=False,
        security=SecurityPosture(transport_encrypted=True),
    )
    return run, _extract(source, everything)


def main() -> None:
    source = MockHISDataSource(records_per_layer=4, seed=42)
    scores: dict[str, float] = {}
    for builder in (compliant, partial, careless):
        run, records = builder(source)
        report = run_all(run, records)
        scores[run.run_id] = report.compliance_score
        print(report.render_table())
        print(f"\n  -> wrote {report.to_json_file()}")
        print(f"  -> wrote {report.to_markdown_file()}")
        print("=" * 72)

    print("\nComparison")
    for run_id, score in scores.items():
        print(f"  {run_id:<24} {score:.3f}")


if __name__ == "__main__":
    main()
