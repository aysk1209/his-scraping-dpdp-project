"""SL-01 -- Storage limitation."""

from __future__ import annotations

from compliance.models import ExtractedRecord, ExtractionRun
from compliance.policy import policy_for
from compliance.rules.base import Rule, RuleResult, RuleStatus


class StorageLimitationRule(Rule):
    rule_id = "SL-01"
    title = "Storage limitation"
    # DPDP Act 2023, s.8(7) -- a Data Fiduciary shall erase personal data on
    # withdrawal of consent or once the specified purpose is no longer being
    # served, whichever is earlier. TODO: verify section number against Act text.
    provision = "DPDP Act 2023, s.8(7)"

    def evaluate(self, run: ExtractionRun, records: list[ExtractedRecord]) -> RuleResult:
        max_days = policy_for(run.purpose).max_retention_days
        findings: list[str] = []
        score = 1.0

        if run.retention_days is None:
            findings.append("No retention period declared for the extracted data.")
            score -= 0.5
        elif run.retention_days > max_days:
            findings.append(
                f"Declared retention {run.retention_days}d exceeds the policy "
                f"maximum {max_days}d for '{run.purpose.value}'."
            )
            score -= 0.5
        else:
            findings.append(
                f"Declared retention {run.retention_days}d is within the "
                f"{max_days}d policy limit."
            )

        if not run.deletion_mechanism:
            findings.append("No deletion mechanism declared.")
            score -= 0.5
        else:
            findings.append(f"Deletion mechanism: {run.deletion_mechanism}.")

        score = max(0.0, score)
        status = RuleStatus.PASS if score == 1.0 else RuleStatus.FAIL
        return self._result(status, score, findings)
