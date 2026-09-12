"""PL-01 -- Purpose limitation."""

from __future__ import annotations

from compliance.models import ExtractedRecord, ExtractionRun, FieldCategory, Purpose
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
            return self._assess_secondary_uses(run, records)

        return self._result(
            RuleStatus.PASS, 1.0,
            [f"Processing is confined to the single specified purpose "
             f"'{run.purpose.value}'."],
        )

    def _assess_secondary_uses(
        self, run: ExtractionRun, records: list[ExtractedRecord]
    ) -> RuleResult:
        """Score declared onward uses by whether the data would fit them.

        An onward use naming a purpose the policy recognises can be assessed
        rather than merely flagged: if the data already pulled sits inside that
        purpose's envelope too, the further processing is at least *compatible*
        and the finding is a paperwork gap. If it does not, the onward use would
        put data outside its own purpose's scope, which is the harder failure.
        An unrecognised onward use cannot be assessed at all, and is treated as
        the harder failure by default -- an unassessable use is not a safe one.
        """

        extracted: set[FieldCategory] = set()
        for record in records:
            extracted |= record.field_categories

        findings = [
            f"{len(run.secondary_uses)} onward use(s) declared beyond the "
            f"specified purpose '{run.purpose.value}': "
            + ", ".join(run.secondary_uses) + "."
        ]

        incompatible = False
        for use in run.secondary_uses:
            other = _recognised_purpose(use)
            if other is None:
                incompatible = True
                findings.append(
                    f"'{use}' is not a recognised processing purpose, so its "
                    f"compatibility cannot be assessed."
                )
                continue

            excess = extracted - PURPOSE_POLICY[other].allowed_categories
            if excess:
                incompatible = True
                listed = ", ".join(sorted(c.value for c in excess))
                findings.append(
                    f"'{use}' would process {listed} data, which falls outside "
                    f"its own purpose scope."
                )
            else:
                findings.append(
                    f"'{use}' is a recognised purpose and the extracted "
                    f"categories sit within its scope -- compatible, but it still "
                    f"needs its own declared basis and notice."
                )

        score = 0.25 if incompatible else 0.5
        findings.append(
            "Each onward use needs its own compatibility assessment and basis."
        )
        return self._result(RuleStatus.FAIL, score, findings)


def _recognised_purpose(name: str) -> Purpose | None:
    """Match a free-text onward use against the recognised purpose taxonomy."""

    try:
        return Purpose(name)
    except ValueError:
        return None
