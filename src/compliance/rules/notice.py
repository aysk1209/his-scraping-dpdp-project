"""NT-01 -- Transparency / notice."""

from __future__ import annotations

from compliance.models import ExtractedRecord, ExtractionRun
from compliance.rules.base import Rule, RuleResult, RuleStatus


class NoticeRule(Rule):
    rule_id = "NT-01"
    title = "Transparency / notice"
    # DPDP Act 2023 -- transparency / notice principle: the Data Principal is
    # given notice of what personal data is processed and for what purpose.
    provision = "DPDP Act 2023 - transparency / notice"

    def evaluate(self, run: ExtractionRun, records: list[ExtractedRecord]) -> RuleResult:
        notice = run.notice
        if notice is None:
            return self._result(
                RuleStatus.FAIL, 0.0,
                ["No privacy notice reference recorded for the Data Principal."],
            )

        findings = [f"Notice reference: {notice.reference}."]
        score = 1.0
        if notice.covers_purpose:
            findings.append("Notice covers the stated processing purpose.")
        else:
            score -= 0.5
            findings.append("Notice does not cover the stated processing purpose.")

        if notice.machine_readable:
            findings.append("Notice is also available in machine-readable form.")

        status = RuleStatus.PASS if score == 1.0 else RuleStatus.FAIL
        return self._result(status, score, findings)
