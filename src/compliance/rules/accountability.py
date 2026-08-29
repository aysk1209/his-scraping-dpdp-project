"""AC-01 -- Accountability."""

from __future__ import annotations

from compliance.models import ExtractedRecord, ExtractionRun
from compliance.rules.base import Rule, RuleResult, RuleStatus


class AccountabilityRule(Rule):
    rule_id = "AC-01"
    title = "Accountability"
    # DPDP Act 2023 -- accountability principle: the Data Fiduciary can
    # demonstrate compliance (audit trail, named responsibility, records).
    provision = "DPDP Act 2023 - accountability"

    def evaluate(self, run: ExtractionRun, records: list[ExtractedRecord]) -> RuleResult:
        gov = run.governance
        checks: dict[str, bool] = {
            "extraction run is audit-logged": gov.audit_log_enabled,
            "named accountable party recorded": gov.accountable_party is not None,
            "record of processing retained": gov.processing_record_kept,
        }

        satisfied = sum(1 for ok in checks.values() if ok)
        total = len(checks)
        score = satisfied / total

        findings = [
            f"[{'x' if ok else ' '}] {name}"
            for name, ok in checks.items()
        ]
        if gov.accountable_party:
            findings.append(f"Accountable party: {gov.accountable_party}.")
        findings.append(f"{satisfied}/{total} accountability controls in place.")

        status = RuleStatus.PASS if score == 1.0 else RuleStatus.FAIL
        return self._result(status, score, findings)
