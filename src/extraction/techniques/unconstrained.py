"""Unconstrained extraction technique (coverage-optimised baseline).

Represents a scraper tuned purely for coverage and speed -- the way baseline
techniques in the literature (cf. AutoScraper, EMNLP 2024) are evaluated. It
ignores the task's ``needed`` list and pulls every field of every layer the
source exposes, and declares no compliance manifest beyond the transport being
encrypted.

Named generically -- no vendor name in core logic (project convention).
"""

from __future__ import annotations

from compliance.models import ExtractedRecord, ExtractionRun, SecurityPosture
from data_synthetic.catalogue import categories_for_fields, fields_for
from extraction.base import HISDataSource
from extraction.technique import ExtractionTask, ExtractionTechnique, TechniqueOutput


class UnconstrainedExtractionTechnique(ExtractionTechnique):
    name = "unconstrained (baseline)"

    def extract(self, source: HISDataSource, task: ExtractionTask) -> TechniqueOutput:
        records: list[ExtractedRecord] = []
        for layer in source.layers():
            all_fields = fields_for(layer)
            for row in source.fetch(layer, fields=all_fields):
                records.append(
                    ExtractedRecord(
                        source_layer=layer.value,
                        field_categories=categories_for_fields(layer, row.keys()),
                    )
                )

        run = ExtractionRun(
            run_id=f"{task.task_id}--unconstrained",
            purpose=task.purpose,
            security=SecurityPosture(transport_encrypted=True),
        )
        return TechniqueOutput(run=run, records=records)
