"""Compliance-aware extraction technique (our method).

Fulfils the task by pulling exactly the fields it declares as needed, and emits
a full compliance manifest: a stated lawful basis, retention within the purpose
policy, a deletion mechanism, and every security safeguard. This is what
"compliance constrains design from the start" looks like in code.

Five design choices make it what it is, and each can be switched off for the
ablation (``scripts/run_ablation.py``) -- one at a time, everything else held:

- ``scope``: a single-patient task reads that patient's records only;
- ``field_list``: the fields come from the purpose's necessary list, not the
  whole of each layer the task touches;
- ``manifest``: the lawful basis, notice and accountability are declared from
  the capability register;
- ``retention``: a retention within the purpose's ceiling is declared, so the
  export is scheduled for erasure;
- ``pseudonymise``: direct identifiers are replaced by tokens on export.

The defaults are the technique as benchmarked; an ablated variant names what it
lacks.
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
from data_synthetic.catalogue import FIELD_CATALOGUE, categories_for_fields
from extraction.base import HISDataSource
from extraction.technique import ExtractionTask, ExtractionTechnique, TechniqueOutput


ABLATIONS = ("scope", "field_list", "manifest", "retention", "pseudonymise")


class CompliantExtractionTechnique(ExtractionTechnique):
    name = "compliance-aware (ours)"

    def __init__(self, register: CapabilityRegister | None = None, *, without: str | None = None) -> None:
        if without is not None and without not in ABLATIONS:
            raise ValueError(f"unknown design choice '{without}'; choose from {', '.join(ABLATIONS)}")
        self.register = register or DEFAULT_REGISTER
        self.without = without
        if without:
            self.name = f"ours without {without.replace('_', ' ')}"

    def _has(self, choice: str) -> bool:
        return self.without != choice

    def extract(self, source: HISDataSource, task: ExtractionTask) -> TechniqueOutput:
        records: list[ExtractedRecord] = []
        rows: dict[str, list[dict]] = {}
        for item in task.needed:
            # The purpose's necessary fields -- or, ablated, everything the layer exposes.
            fields = item.fields if self._has("field_list") else (
                source.fields(item.layer) or list(FIELD_CATALOGUE.get(item.layer, {})) or item.fields)
            # A single-patient task reads that patient's records and no one
            # else's -- minimisation on the record axis, read off the task the
            # same way the field list is.
            where = task.subject_filter(item.layer) if self._has("scope") else {}
            for row in source.fetch(item.layer, fields=fields, where=where or None):
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
        manifest = self._has("manifest")
        run = ExtractionRun(
            run_id=f"{task.task_id}--compliance-aware" + (f"-without-{self.without}" if self.without else ""),
            purpose=task.purpose,
            purpose_specified=True,
            secondary_uses=[],
            lawful_basis=LawfulBasis(
                type=LawfulBasisType.LEGITIMATE_USE,
                # The basis is a property of the purpose, read from the register
                # (whose descriptions are the policy's legitimate-use notes). A
                # deployment with no basis on record gets none cited -- LB-01
                # then scores it as asserted, not referenced, which is the truth.
                reference=f"{basis.id} -- {basis.description}" if basis and manifest else None,
            ),
            retention_days=min(30, policy.max_retention_days) if self._has("retention") else None,
            deletion_mechanism=f"{reg.deletion_mechanism.id} -- {reg.deletion_mechanism.description}"
            if reg.deletion_mechanism and self._has("retention") else None,
            security=SecurityPosture(
                # Transport is the one safeguard the technique can see for itself:
                # the register may list TLS, but if the source was reached over
                # plain http this run was not encrypted in transit, and says so.
                transport_encrypted=reg.transport_encrypted is not None and source.transport_secure is not False,
                at_rest_encrypted=reg.at_rest_encrypted is not None,
                access_controlled=reg.access_controlled is not None,
                identifiers_pseudonymised=reg.pseudonymisation is not None and self._has("pseudonymise"),
            ),
            notice=Notice(
                reference=f"{reg.notice.id} -- {reg.notice.description}",
                covers_purpose=True,
                machine_readable=reg.notice_machine_readable,
            ) if reg.notice and manifest else None,
            governance=Governance(
                audit_log_enabled=reg.audit_log is not None,
                accountable_party=f"{reg.accountable_party.id} -- {reg.accountable_party.description}"
                if reg.accountable_party and manifest else None,
                processing_record_kept=reg.processing_record is not None and manifest,
            ),
        )
        return TechniqueOutput(run=run, records=records, rows=rows)
