"""LB-01 -- Lawful basis for processing."""

from __future__ import annotations

from compliance.models import ExtractedRecord, ExtractionRun, LawfulBasisType
from compliance.rules.base import Rule, RuleResult, RuleStatus


class LawfulBasisRule(Rule):
    rule_id = "LB-01"
    title = "Lawful basis for processing"
    # DPDP Act 2023, s.4 -- personal data may be processed only for a lawful
    # purpose for which the Data Principal has given consent (s.6) or for a
    # legitimate use (s.7). TODO: verify section numbers against Act text.
    provision = "DPDP Act 2023, s.4"

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
