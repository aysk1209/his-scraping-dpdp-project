"""Tests for the extraction summary that enriches a ComplianceReport."""

from __future__ import annotations

from compliance.checkers import run_all
from compliance.models import ExtractedRecord, ExtractionRun, FieldCategory, Purpose
from compliance.summary import merge, summarise


def _run() -> ExtractionRun:
    return ExtractionRun(run_id="s", purpose=Purpose.CARE_COORDINATION)


def test_summarise_counts_records_layers_and_categories():
    records = [
        ExtractedRecord(
            source_layer="patient_administration",
            field_categories={FieldCategory.DIRECT_IDENTIFIER, FieldCategory.QUASI_IDENTIFIER},
        ),
        ExtractedRecord(source_layer="clinical_ehr", field_categories={FieldCategory.CLINICAL}),
        ExtractedRecord(source_layer="clinical_ehr", field_categories={FieldCategory.CLINICAL}),
    ]
    summary = summarise(_run(), records)
    assert summary.record_count == 3
    assert summary.layers == ["patient_administration", "clinical_ehr"]
    assert summary.category_counts["clinical"] == 2
    assert summary.field_slots == 4
    assert summary.out_of_scope_categories == []


def test_summarise_flags_out_of_scope_categories():
    records = [
        ExtractedRecord(
            source_layer="administrative_financial",
            field_categories={FieldCategory.FINANCIAL},
        ),
        ExtractedRecord(
            source_layer="patient_administration",
            field_categories={FieldCategory.CONTACT, FieldCategory.DIRECT_IDENTIFIER},
        ),
    ]
    summary = summarise(_run(), records)
    assert set(summary.out_of_scope_categories) == {"financial", "contact"}


def test_empty_records_summary_reads_cleanly():
    summary = summarise(_run(), [])
    assert summary.record_count == 0
    assert summary.one_line() == "no records"


def test_merge_combines_per_task_summaries():
    first = summarise(
        _run(),
        [ExtractedRecord(source_layer="clinical_ehr", field_categories={FieldCategory.CLINICAL})],
    )
    second = summarise(
        _run(),
        [
            ExtractedRecord(source_layer="clinical_ehr", field_categories={FieldCategory.CLINICAL}),
            ExtractedRecord(
                source_layer="administrative_financial",
                field_categories={FieldCategory.FINANCIAL},
            ),
        ],
    )
    merged = merge([first, second])
    assert merged.record_count == 3
    assert merged.category_counts["clinical"] == 2
    assert "financial" in merged.out_of_scope_categories


def test_run_all_attaches_the_summary_to_the_report():
    records = [
        ExtractedRecord(source_layer="clinical_ehr", field_categories={FieldCategory.CLINICAL})
    ]
    report = run_all(_run(), records)
    assert report.extraction is not None
    assert report.extraction.record_count == 1
    assert report.rules_passed <= len(report.results)
