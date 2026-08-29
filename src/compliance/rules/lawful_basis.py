"""LB-01 -- Lawful basis for processing."""

from __future__ import annotations

from compliance.models import ExtractedRecord, ExtractionRun, LawfulBasisType
from compliance.rules.base import Rule, RuleResult, RuleStatus


class LawfulBasisRule(Rule):
    rule_id = "LB-01"
    title = "Lawful basis for processing"
    # DPDP Act 2023 -- lawful basis principle: personal data is processed only on
    # a recognised basis, i.e. the Data Principal's consent or a legitimate use.
    provision = "DPDP Act 2023 - lawful basis for processing"

    def evaluate(self, run: ExtractionRun, records: list[ExtractedRecord]) -> RuleResult:
        basis = run.lawful_basis

        if basis is None:
            return self._result(
                RuleStatus.FAIL, 0.0,
                ["No lawful basis declared for the extraction run."],
            )

        if not basis.reference:
            missing = (
                "consent reference" if basis.type == LawfulBasisType.CONSENT
                else "the specific s.7 legitimate use"
            )
            return self._result(
                RuleStatus.FAIL, 0.5,
                [f"Declared basis is '{basis.type.value}' but {missing} is not recorded."],
            )

        return self._result(
            RuleStatus.PASS, 1.0,
            [f"Declared basis: {basis.type.value} ({basis.reference})."],
        )
