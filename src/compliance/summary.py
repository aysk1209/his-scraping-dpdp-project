"""A concrete summary of what an extraction run actually pulled.

The compliance rules score *categories*; this adds the human-facing detail --
how many records, which layers, how many fields of each category, and how many
of them fall outside the purpose policy. It turns an abstract 0-1 score into a
report a reviewer can read.
"""

from __future__ import annotations

from collections import Counter

from pydantic import BaseModel

from compliance.models import ExtractedRecord, ExtractionRun
from compliance.policy import PURPOSE_POLICY


class ExtractionSummary(BaseModel):
    record_count: int
    layers: list[str]
    category_counts: dict[str, int]        # FieldCategory value -> field occurrences
    field_slots: int                       # total tagged field occurrences
    out_of_scope_categories: list[str]     # categories outside the purpose policy

    def one_line(self) -> str:
        if not self.record_count:
            return "no records"
        cats = ", ".join(f"{name} ({count})" for name, count in self.category_counts.items())
        oos = ", ".join(self.out_of_scope_categories) or "none"
        return (
            f"{self.record_count} records across {len(self.layers)} layer(s); "
            f"fields by category: {cats}; out-of-scope: {oos}"
        )


def summarise(run: ExtractionRun, records: list[ExtractedRecord]) -> ExtractionSummary:
    counter: Counter[str] = Counter()
    layers: list[str] = []
    for record in records:
        if record.source_layer not in layers:
            layers.append(record.source_layer)
        for category in record.field_categories:
            counter[category.value] += 1

    policy = PURPOSE_POLICY.get(run.purpose)
    allowed = {c.value for c in policy.allowed_categories} if policy else set()
    out_of_scope = sorted(name for name in counter if name not in allowed)

    return ExtractionSummary(
        record_count=len(records),
        layers=layers,
        category_counts=dict(sorted(counter.items())),
        field_slots=sum(counter.values()),
        out_of_scope_categories=out_of_scope,
    )


def merge(summaries: list[ExtractionSummary]) -> ExtractionSummary:
    """Combine per-task summaries into one (used by the benchmark)."""

    counter: Counter[str] = Counter()
    layers: list[str] = []
    records = 0
    oos: set[str] = set()
    for summary in summaries:
        records += summary.record_count
        for layer in summary.layers:
            if layer not in layers:
                layers.append(layer)
        counter.update(summary.category_counts)
        oos.update(summary.out_of_scope_categories)

    return ExtractionSummary(
        record_count=records,
        layers=layers,
        category_counts=dict(sorted(counter.items())),
        field_slots=sum(counter.values()),
        out_of_scope_categories=sorted(oos),
    )
