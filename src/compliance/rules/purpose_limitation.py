"""PL-01 -- Purpose limitation."""

from __future__ import annotations

from compliance.models import ExtractedRecord, ExtractionRun
from compliance.policy import PURPOSE_POLICY
from compliance.rules.base import Rule, RuleResult, RuleStatus


class PurposeLimitationRule(Rule):
    rule_id = "PL-01"
    title = "Purpose limitation"
    # DPDP Act 2023 -- purpose limitation principle: personal data is processed
    # only for the specified purpose; onward uses require their own basis.
    provision = "DPDP Act 2023 - purpose limitation"

    def evaluate(self, run: ExtractionRun, records: list[ExtractedRecord]) -> RuleResult:
        if not run.purpose_specified:
            return self._result(
                RuleStatus.FAIL, 0.0,
                ["No specific processing purpose declared for this extraction."],
            )

        if run.purpose not in PURPOSE_POLICY:
            return self._result(
                RuleStatus.FAIL, 0.0,
                [f"Declared purpose '{run.purpose.value}' is not a recognised "
                 "processing purpose."],
            )

        if run.secondary_uses:
            listed = ", ".join(run.secondary_uses)
            return self._result(
                RuleStatus.FAIL, 0.5,
                [f"{len(run.secondary_uses)} onward use(s) declared beyond the "
                 f"specified purpose: {listed}.",
                 "Each onward use needs its own compatibility assessment and basis."],
            )

        return self._result(
            RuleStatus.PASS, 1.0,
            [f"Processing is confined to the single specified purpose "
             f"'{run.purpose.value}'."],
        )
