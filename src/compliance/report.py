"""ComplianceReport -- the scored artifact a benchmark run produces.

This is the object that gets written to docs/benchmark_results/ and, later,
placed side by side with a baseline technique's report. It is the paper's core
evidence: compliance expressed as a number plus a per-principle breakdown, not a
paragraph.

Three renderings: ``render_table`` (console), ``model_dump_json`` /
``to_json_file`` (machine-readable), ``render_markdown`` / ``to_markdown_file``
(paste into slides or the report).
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field

from compliance.rules.base import RuleResult, RuleStatus

_REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_DIR = _REPO_ROOT / "docs" / "benchmark_results"


class ComplianceReport(BaseModel):
    run_id: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    compliance_score: float
    pass_rate: float
    results: list[RuleResult]

    @classmethod
    def from_results(
        cls,
        run_id: str,
        results: list[RuleResult],
        weights: dict[str, float],
    ) -> "ComplianceReport":
        applicable = [r for r in results if r.status != RuleStatus.NOT_APPLICABLE]
        if applicable:
            weight_sum = sum(weights[r.rule_id] for r in applicable)
            score = sum(r.score * weights[r.rule_id] for r in applicable) / weight_sum
            pass_rate = (
                sum(1 for r in applicable if r.status == RuleStatus.PASS)
                / len(applicable)
            )
        else:
            score = 1.0
            pass_rate = 1.0
        return cls(
            run_id=run_id,
            compliance_score=round(score, 3),
            pass_rate=round(pass_rate, 3),
            results=results,
        )

    def to_json_file(self, directory: Path | None = None) -> Path:
        directory = directory or ARTIFACT_DIR
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{self.run_id}.json"
        path.write_text(self.model_dump_json(indent=2), encoding="utf-8")
        return path

    def render_table(self) -> str:
        lines = [
            f"Compliance report -- run '{self.run_id}'",
            f"  overall score : {self.compliance_score:.3f}",
            f"  pass rate     : {self.pass_rate:.0%}",
            "",
            f"  {'rule':<7} {'status':<15} {'score':>6}  provision",
            f"  {'-' * 7} {'-' * 15} {'-' * 6}  {'-' * 34}",
        ]
        for result in self.results:
            lines.append(
                f"  {result.rule_id:<7} {result.status.value:<15} "
                f"{result.score:>6.2f}  {result.provision}"
            )
            for finding in result.findings:
                lines.append(f"            - {finding}")
        return "\n".join(lines)

    def render_markdown(self) -> str:
        lines = [
            f"### Compliance report -- `{self.run_id}`",
            "",
            f"**Overall score:** {self.compliance_score:.3f} &nbsp;&nbsp; "
            f"**Pass rate:** {self.pass_rate:.0%}",
            "",
            "| Rule | DPDP principle | Status | Score |",
            "|------|----------------|--------|-------|",
        ]
        for result in self.results:
            lines.append(
                f"| {result.rule_id} | {result.provision} "
                f"| {result.status.value} | {result.score:.2f} |"
            )
        lines += ["", "**Findings**", ""]
        for result in self.results:
            lines.append(f"- **{result.rule_id}**")
            for finding in result.findings:
                lines.append(f"  - {finding}")
        return "\n".join(lines)

    def to_markdown_file(self, directory: Path | None = None) -> Path:
        directory = directory or ARTIFACT_DIR
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{self.run_id}.md"
        path.write_text(self.render_markdown(), encoding="utf-8")
        return path
