"""Demo: score three extraction runs -- compliant, partial, careless -- against
the DPDP rules.

    python scripts/score_extraction_run.py

Prints each compliance report and writes JSON + Markdown artifacts to
docs/benchmark_results/. The spread of scores is the "compliance is a measurable
property of an extraction technique" thesis shown rather than asserted -- and
this is the exact harness a baseline technique (e.g. AutoScraper) will later be
run through for comparison.

No real personal data is involved: sample records carry only field *categories*.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import _present as present
from compliance.checkers import run_all
from compliance.models import (
    ExtractedRecord,
    ExtractionRun,
    FieldCategory,
    Governance,
    LawfulBasis,
    LawfulBasisType,
    Notice,
    Purpose,
    SecurityPosture,
)


def compliant_run() -> tuple[ExtractionRun, list[ExtractedRecord]]:
    """An extraction run designed to satisfy the DPDP rule set."""

    run = ExtractionRun(
        run_id="care-coordination-compliant",
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
    records = [
        ExtractedRecord(
            source_layer="patient_administration",
            field_categories={
                FieldCategory.DIRECT_IDENTIFIER,
                FieldCategory.QUASI_IDENTIFIER,
            },
        ),
        ExtractedRecord(
            source_layer="clinical_ehr",
            field_categories={FieldCategory.CLINICAL, FieldCategory.ADMINISTRATIVE},
        ),
    ]
    return run, records


def partial_run() -> tuple[ExtractionRun, list[ExtractedRecord]]:
    """A run that keeps field scope tight but cuts corners on paperwork and security.

    Only in-scope categories are extracted (DM-01 passes) and a purpose is
    declared (PL-01 passes), but the lawful basis has no reference, there is no
    deletion mechanism, only half the security safeguards are in place, and no
    notice or governance is recorded -- so LB-01, SL-01, SS-01 land around 0.5
    and NT-01, AC-01 fail.
    """

    run = ExtractionRun(
        run_id="care-coordination-partial",
        purpose=Purpose.CARE_COORDINATION,
        lawful_basis=LawfulBasis(type=LawfulBasisType.CONSENT, reference=None),
        retention_days=45,
        deletion_mechanism=None,
        security=SecurityPosture(
            transport_encrypted=True,
            at_rest_encrypted=True,
            access_controlled=False,
            identifiers_pseudonymised=False,
        ),
    )
    records = [
        ExtractedRecord(
            source_layer="patient_administration",
            field_categories={
                FieldCategory.DIRECT_IDENTIFIER,
                FieldCategory.QUASI_IDENTIFIER,
            },
        ),
        ExtractedRecord(
            source_layer="clinical_ehr",
            field_categories={FieldCategory.CLINICAL, FieldCategory.ADMINISTRATIVE},
        ),
    ]
    return run, records


def careless_run() -> tuple[ExtractionRun, list[ExtractedRecord]]:
    """A 'grab everything, declare nothing' run -- the shape of an unconstrained scraper."""

    run = ExtractionRun(
        run_id="care-coordination-careless",
        purpose=Purpose.CARE_COORDINATION,
        purpose_specified=False,
        lawful_basis=None,
        retention_days=None,
        deletion_mechanism=None,
        security=SecurityPosture(transport_encrypted=True),
    )
    records = [
        ExtractedRecord(
            source_layer="patient_administration",
            field_categories={FieldCategory.DIRECT_IDENTIFIER, FieldCategory.CONTACT},
        ),
        ExtractedRecord(
            source_layer="clinical_ehr",
            field_categories={FieldCategory.CLINICAL},
        ),
        ExtractedRecord(
            source_layer="administrative_financial",
            field_categories={FieldCategory.FINANCIAL},
        ),
    ]
    return run, records


def main() -> None:
    scores: dict[str, float] = {}
    for builder in (compliant_run, partial_run, careless_run):
        run, records = builder()
        report = run_all(run, records)
        scores[run.run_id] = report.compliance_score

        print(present.banner(f"Run: {run.run_id}"))
        print(report.render_table())
        print(present.wrote(report.to_json_file()))
        print(present.wrote(report.to_markdown_file()))

    print(present.banner("Comparison"))
    for run_id, score in scores.items():
        print(f"  {run_id:<32} {score:.3f}")
    print(present.takeaway(
        "The seven rules resolve to a single 0-1 score per run, with a stated "
        "reason for every deduction."
    ))


if __name__ == "__main__":
    main()
