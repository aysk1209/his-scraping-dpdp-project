"""DM-01 -- Data minimisation."""

from __future__ import annotations

from compliance.models import ExtractedRecord, ExtractionRun, FieldCategory
from compliance.policy import policy_for
from compliance.rules.base import Rule, RuleResult, RuleStatus


class DataMinimisationRule(Rule):
    rule_id = "DM-01"
    title = "Data minimisation"
    # DPDP Act 2023 -- data minimisation principle: personal data is limited to
    # what is necessary for the stated processing purpose.
    provision = "DPDP Act 2023 - data minimisation"

    def evaluate(self, run: ExtractionRun, records: list[ExtractedRecord]) -> RuleResult:
        allowed = policy_for(run.purpose).allowed_categories

        extracted: set[FieldCategory] = set()
        for record in records:
            extracted |= record.field_categories

        if not extracted:
            return self._result(
                RuleStatus.NOT_APPLICABLE, 1.0,
                ["No extracted records supplied; nothing to assess."],
            )

        # Field axis: are the categories pulled within the purpose's scope?
        excess = extracted - allowed
        category_score = 1.0 - len(excess) / len(extracted)
        findings: list[str] = []
        if not excess:
            findings.append(
                f"All {len(extracted)} extracted field categories are within "
                f"the '{run.purpose.value}' purpose scope."
            )
        else:
            findings += [
                f"Out-of-scope category extracted: {category.value}"
                for category in sorted(excess, key=lambda c: c.value)
            ]
            findings.append(
                f"{len(excess)} of {len(extracted)} extracted categories exceed the "
                f"'{run.purpose.value}' purpose scope."
            )

        # Record axis: for a task about one patient, were only that patient's
        # records read? The harness records what was pulled against what the
        # subject needed; a run that read the whole module to answer for one
        # person over-collected on every record but one, whatever the fields.
        # DPDP Act 2023 -- data minimisation: necessary for the purpose means
        # necessary records as well as necessary fields.
        if run.scope is None:
            score = category_score
        else:
            pulled, needed = run.scope.records_pulled, run.scope.records_necessary
            record_score = 1.0 if pulled <= max(needed, 0) or pulled == 0 else needed / pulled
            if record_score >= 1.0:
                findings.append(
                    f"Single-patient task: {pulled} record(s) read, {needed} necessary."
                )
            else:
                findings.append(
                    f"Single-patient task: {pulled} records read where {needed} were necessary "
                    f"-- {pulled - needed} other patients' records taken."
                )
            score = (category_score + record_score) / 2

        status = RuleStatus.PASS if score >= 1.0 else RuleStatus.FAIL
        return self._result(status, round(score, 6), findings)
