"""The morality model: privacy by intuition, not by law.

The middle technique in the benchmark, and a different *kind* of thing from the
other two. The compliance-aware technique asks "what does this purpose make
necessary?" and reads the answer from the policy table. The baseline asks nothing.
The morality model asks "does this feel private?" -- the judgement a general-
purpose AI model, or a well-meaning engineer, would make from the field's name
alone, with no concept of purpose behind it.

It is named honestly: it is not DPDP-compliant and does not try to be. It
follows base intuitions about what is private. Those intuitions get some things
right and are wrong in both directions at once:

- **Over-collects** what does not feel private -- date of birth, sex, pincode,
  ward -- though together they re-identify, and MRN, "just an ID", the strongest
  identifier in the record.
- **Under-delivers** what does feel private -- a phone number, an address --
  even when the purpose lawfully needs it (a registration desk cannot confirm an
  appointment without one). Coverage drops below 1.0 on those tasks; the
  compliance-aware technique pulls the same field lawfully.
- **Declares by instinct.** It knows why it is doing the work (purpose specified),
  assumes consent without recording any, intends to delete without a mechanism,
  logs what it does because that seems right, and never issues a notice, because
  a notice is not something intuition thinks of.

The intuition table below is the whole model. It is what a general model treats as
private when it reads a column header; it is not a legal standard and the point of
the benchmark is that the two differ. Keep it explicit and inspectable so the
comparison stays fair.
"""

from __future__ import annotations

from compliance.models import (
    ExtractedRecord,
    ExtractionRun,
    Governance,
    LawfulBasis,
    LawfulBasisType,
    SecurityPosture,
)
from data_synthetic.catalogue import categories_for_fields
from extraction.base import HISDataSource
from extraction.technique import ExtractionTask, ExtractionTechnique, TechniqueOutput

# What "feels private" to a model reading field names. Names, ways to reach a
# person, and money -- the things people readily call private -- are refused
# regardless of purpose. Identifiers that look like codes, demographics that look
# like statistics, and clinical facts "the doctor asked for" are all pulled.
FEELS_PRIVATE: frozenset[str] = frozenset({
    "full_name",
    "phone",
    "email",
    "street_address",
    "insurance_policy_no",
    "billed_amount",
    "payer_name",
})

# Retained for the reader of the benchmark: what the model considers harmless and
# pulls freely. Listed rather than computed so the judgement is visible.
FEELS_HARMLESS: frozenset[str] = frozenset({
    "mrn", "date_of_birth", "sex", "pincode", "admission_ward", "admission_datetime",
    "encounter_datetime", "attending_clinician", "order_id", "invoice_id",
    "subject_mrn", "audit_event_id",
})


class MoralityTechnique(ExtractionTechnique):
    name = "morality (privacy by instinct)"

    def extract(self, source: HISDataSource, task: ExtractionTask) -> TechniqueOutput:
        records: list[ExtractedRecord] = []
        rows: dict[str, list[dict]] = {}
        for item in task.needed:
            # The intuition filter: refuse what feels private, even if the purpose
            # needs it; take the rest, even where the purpose would not.
            wanted = [f for f in item.fields if f not in FEELS_PRIVATE]
            if not wanted:
                continue
            for row in source.fetch(item.layer, fields=wanted):
                rows.setdefault(item.layer.value, []).append(row)
                records.append(
                    ExtractedRecord(
                        source_layer=item.layer.value,
                        field_categories=categories_for_fields(item.layer, row.keys()),
                    )
                )

        run = ExtractionRun(
            run_id=f"{task.task_id}--morality",
            purpose=task.purpose,
            purpose_specified=True,          # it knows why it is doing this
            # "They came to the hospital, so they consented" -- a basis asserted,
            # never recorded.
            lawful_basis=LawfulBasis(type=LawfulBasisType.CONSENT, reference=None),
            retention_days=None,             # "we'll delete it when we're done"
            deletion_mechanism=None,
            # Encrypt everything -- that much intuition gets right. Access control
            # and pseudonymisation are not things a privacy instinct reaches for;
            # the MRN is "just a number".
            security=SecurityPosture(transport_encrypted=True, at_rest_encrypted=True),
            notice=None,                     # a notice is a legal artefact, not an instinct
            # Logging feels responsible; a named owner and a processing record do not
            # occur to it.
            governance=Governance(audit_log_enabled=True),
        )
        return TechniqueOutput(run=run, records=records, rows=rows)
