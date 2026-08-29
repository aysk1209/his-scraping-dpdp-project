"""Compliance-aware extraction technique (our method).

Fulfils the task by pulling exactly the fields it declares as needed, and emits
a full compliance manifest: a stated lawful basis, retention within the purpose
policy, a deletion mechanism, and every security safeguard. This is what
"compliance constrains design from the start" looks like in code.
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


class CompliantExtractionTechnique(ExtractionTechnique):
    name = "compliance-aware (ours)"

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
        run = ExtractionRun(
            run_id=f"{task.task_id}--compliance-aware",
            purpose=task.purpose,
            lawful_basis=LawfulBasis(
                type=LawfulBasisType.LEGITIMATE_USE,
                reference="legitimate use -- provision of medical services",
            ),
            retention_days=min(30, policy.max_retention_days),
            deletion_mechanism="scheduled purge on purpose completion, audited",
            security=SecurityPosture(
                transport_encrypted=True,
                at_rest_encrypted=True,
                access_controlled=True,
                identifiers_pseudonymised=True,
            ),
        )
        return TechniqueOutput(run=run, records=records)
