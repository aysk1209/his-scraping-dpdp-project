"""Minimising-but-undocumented extraction technique.

Pulls only the fields the task needs -- so data minimisation is satisfied -- but
does no compliance paperwork: consent asserted without a reference, no deletion
mechanism, only partial security safeguards. A realistic "means well, cuts
corners" middle point between the compliance-aware method and the unconstrained
baseline.
"""

from __future__ import annotations

from compliance.models import (
    ExtractedRecord,
    ExtractionRun,
    LawfulBasis,
    LawfulBasisType,
    SecurityPosture,
)
from compliance.policy import policy_for
from data_synthetic.catalogue import categories_for_fields
from extraction.base import HISDataSource
from extraction.technique import ExtractionTask, ExtractionTechnique, TechniqueOutput


class MinimisingUndocumentedTechnique(ExtractionTechnique):
    name = "minimising, undocumented"

    def extract(self, source: HISDataSource, task: ExtractionTask) -> TechniqueOutput:
        records: list[ExtractedRecord] = []
        for item in task.needed:
            for row in source.fetch(item.layer, fields=item.fields):
                records.append(
                    ExtractedRecord(
                        source_layer=item.layer.value,
                        field_categories=categories_for_fields(item.layer, row.keys()),
                    )
                )

        policy = policy_for(task.purpose)
        # A specific purpose is declared, but notice and governance are left
        # unset -- the "means well, no paperwork" failure mode.
        run = ExtractionRun(
            run_id=f"{task.task_id}--minimising",
            purpose=task.purpose,
            purpose_specified=True,
            lawful_basis=LawfulBasis(type=LawfulBasisType.CONSENT, reference=None),
            retention_days=min(45, policy.max_retention_days),
            deletion_mechanism=None,
            security=SecurityPosture(transport_encrypted=True, at_rest_encrypted=True),
        )
        return TechniqueOutput(run=run, records=records)
