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
from compliance.capabilities import DEFAULT_REGISTER, CapabilityRegister
from compliance.policy import policy_for
from data_synthetic.catalogue import categories_for_fields
from extraction.base import HISDataSource
from extraction.technique import ExtractionTask, ExtractionTechnique, TechniqueOutput


class CompliantExtractionTechnique(ExtractionTechnique):
    name = "compliance-aware (ours)"

    def __init__(self, register: CapabilityRegister | None = None) -> None:
        self.register = register or DEFAULT_REGISTER

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
        reg = self.register
        basis = reg.lawful_bases.get(task.purpose)
        # Every declaration below is a control the register actually provides,
        # cited by its identifier -- the technique cannot declare a safeguard the
        # deployment lacks, because it has no other source to declare from.
        # DPDP Act 2023 -- accountability: declare only what can be demonstrated.
        run = ExtractionRun(
            run_id=f"{task.task_id}--compliance-aware",
            purpose=task.purpose,
            purpose_specified=True,
            secondary_uses=[],
            lawful_basis=LawfulBasis(
                type=LawfulBasisType.LEGITIMATE_USE,
                # The basis is a property of the purpose, read from the register
                # (whose descriptions are the policy's legitimate-use notes). A
                # deployment with no basis on record gets none cited -- LB-01
                # then scores it as asserted, not referenced, which is the truth.
                reference=f"{basis.id} -- {basis.description}" if basis else None,
            ),
            retention_days=min(30, policy.max_retention_days),
            deletion_mechanism=f"{reg.deletion_mechanism.id} -- {reg.deletion_mechanism.description}"
            if reg.deletion_mechanism else None,
            security=SecurityPosture(
                transport_encrypted=reg.transport_encrypted is not None,
                at_rest_encrypted=reg.at_rest_encrypted is not None,
                access_controlled=reg.access_controlled is not None,
                identifiers_pseudonymised=reg.pseudonymisation is not None,
            ),
            notice=Notice(
                reference=f"{reg.notice.id} -- {reg.notice.description}",
                covers_purpose=True,
                machine_readable=reg.notice_machine_readable,
            ) if reg.notice else None,
            governance=Governance(
                audit_log_enabled=reg.audit_log is not None,
                accountable_party=f"{reg.accountable_party.id} -- {reg.accountable_party.description}"
                if reg.accountable_party else None,
                processing_record_kept=reg.processing_record is not None,
            ),
        )
        return TechniqueOutput(run=run, records=records, rows=rows)
