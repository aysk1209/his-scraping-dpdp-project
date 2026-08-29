"""Base types for DPDP compliance rules.

Each rule maps to a specific DPDP Act 2023 provision (named on the rule and in a
code comment at the point of the check) and returns a ``RuleResult`` -- a status,
a 0.0-1.0 score, and human-readable findings. ``checkers.run_all`` aggregates
rule results into a ``ComplianceReport``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum

from pydantic import BaseModel, Field

from compliance.models import ExtractedRecord, ExtractionRun


class RuleStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    NOT_APPLICABLE = "not_applicable"


class RuleResult(BaseModel):
    rule_id: str
    title: str
    provision: str
    status: RuleStatus
    score: float = Field(ge=0.0, le=1.0)
    findings: list[str] = Field(default_factory=list)


class Rule(ABC):
    """A single DPDP compliance check."""

    rule_id: str = ""
    title: str = ""
    provision: str = ""
    weight: float = 1.0

    @abstractmethod
    def evaluate(self, run: ExtractionRun, records: list[ExtractedRecord]) -> RuleResult:
        raise NotImplementedError

    def _result(
        self,
        status: RuleStatus,
        score: float,
        findings: list[str] | None = None,
    ) -> RuleResult:
        return RuleResult(
            rule_id=self.rule_id,
            title=self.title,
            provision=self.provision,
            status=status,
            score=score,
            findings=findings or [],
        )
