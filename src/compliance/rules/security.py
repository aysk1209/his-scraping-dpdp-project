"""SS-01 -- Security safeguards."""

from __future__ import annotations

from compliance.models import ExtractedRecord, ExtractionRun, FieldCategory
from compliance.policy import policy_for
from compliance.rules.base import Rule, RuleResult, RuleStatus


class SecuritySafeguardsRule(Rule):
    rule_id = "SS-01"
    title = "Security safeguards"
    # DPDP Act 2023 -- security safeguards principle: reasonable technical and
    # organisational safeguards protect personal data against breach.
    provision = "DPDP Act 2023 - security safeguards"

    def evaluate(self, run: ExtractionRun, records: list[ExtractedRecord]) -> RuleResult:
        posture = run.security
        checks: dict[str, bool] = {
            "transport encryption (TLS)": posture.transport_encrypted,
            "encryption at rest": posture.at_rest_encrypted,
            "access control on extracted store": posture.access_controlled,
        }

        # Pseudonymisation is only a required safeguard when the purpose policy
        # calls for it AND direct identifiers were actually extracted.
        policy = policy_for(run.purpose)
        direct_ids_extracted = any(
            FieldCategory.DIRECT_IDENTIFIER in record.field_categories
            for record in records
        )
        if policy.requires_pseudonymised_identifiers and direct_ids_extracted:
            checks["direct identifiers pseudonymised on export"] = (
                posture.identifiers_pseudonymised
            )

        satisfied = sum(1 for ok in checks.values() if ok)
        total = len(checks)
        score = satisfied / total

        findings = [
            f"[{'x' if ok else ' '}] {name}"
            for name, ok in checks.items()
        ]
        findings.append(f"{satisfied}/{total} required safeguards in place.")

        status = RuleStatus.PASS if score == 1.0 else RuleStatus.FAIL
        return self._result(status, score, findings)
