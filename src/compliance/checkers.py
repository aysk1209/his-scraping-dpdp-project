"""Evaluate an extraction run against the DPDP rule set.

This is the entry point the compliance benchmarking harness (build step 5) and
the demo script both call. It stays deliberately thin: build the rule list, run
each rule, hand the results to ``ComplianceReport`` for scoring.
"""

from __future__ import annotations

from compliance.models import ExtractedRecord, ExtractionRun
from compliance.report import ComplianceReport
from compliance.rules import ALL_RULES


def run_all(run: ExtractionRun, records: list[ExtractedRecord]) -> ComplianceReport:
    """Score one extraction run against every registered DPDP rule."""

    results = [rule.evaluate(run, records) for rule in ALL_RULES]
    weights = {rule.rule_id: rule.weight for rule in ALL_RULES}
    return ComplianceReport.from_results(
        run_id=run.run_id, results=results, weights=weights
    )
