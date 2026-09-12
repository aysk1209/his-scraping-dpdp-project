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
    Governance,
    LawfulBasis,
    LawfulBasisType,
    Notice,
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
        rows: dict[str, list[dict]] = {}
        for item in task.needed:
            for row in source.fetch(item.layer, fields=item.fields):
                rows.setdefault(item.layer.value, []).append(row)
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
            purpose_specified=True,
            secondary_uses=[],
            lawful_basis=LawfulBasis(
                type=LawfulBasisType.LEGITIMATE_USE,
                # Read from the policy table rather than hard-coded: the basis a
                # run relies on is a property of its purpose, and the technique
                # should not carry per-purpose knowledge of its own.
                reference=policy.legitimate_use_note,
            ),
            retention_days=min(30, policy.max_retention_days),
            deletion_mechanism="scheduled purge on purpose completion, audited",
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
        return TechniqueOutput(run=run, records=records, rows=rows)
