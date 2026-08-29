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

        excess = extracted - allowed
        score = 1.0 - len(excess) / len(extracted)

        if not excess:
            return self._result(
                RuleStatus.PASS, 1.0,
                [f"All {len(extracted)} extracted field categories are within "
                 f"the '{run.purpose.value}' purpose scope."],
            )

        findings = [
            f"Out-of-scope category extracted: {category.value}"
            for category in sorted(excess, key=lambda c: c.value)
        ]
        findings.append(
            f"{len(excess)} of {len(extracted)} extracted categories exceed the "
            f"'{run.purpose.value}' purpose scope."
        )
        return self._result(RuleStatus.FAIL, score, findings)
