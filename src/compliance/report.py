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
from compliance.summary import ExtractionSummary

_REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_DIR = _REPO_ROOT / "docs" / "benchmark_results"


class ComplianceReport(BaseModel):
    run_id: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    compliance_score: float
    pass_rate: float
    results: list[RuleResult]
    extraction: ExtractionSummary | None = None
    # The manifest facts a reader needs to interpret the score without opening
    # the findings: what the pull was for, on what basis, and for how long.
    purpose: str | None = None
    lawful_basis: str | None = None
    retention_days: int | None = None

    def _manifest_line(self) -> str:
        parts = [f"purpose {self.purpose or 'not declared'}"]
        parts.append(f"basis {self.lawful_basis or 'not declared'}")
        parts.append(
            f"retention {self.retention_days}d" if self.retention_days is not None
            else "retention not declared"
        )
        return "; ".join(parts)

    @property
    def rules_passed(self) -> int:
        return sum(1 for r in self.results if r.status == RuleStatus.PASS)

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
        total = len(self.results)
        lines = [
            f"Compliance report -- run '{self.run_id}'",
            f"  manifest  : {self._manifest_line()}",
        ]
        if self.extraction is not None:
            lines.append(f"  extracted : {self.extraction.one_line()}")
        lines += [
            f"  score     : {self.compliance_score:.3f}   "
            f"({self.rules_passed}/{total} rules pass, pass rate {self.pass_rate:.0%})",
            "",
            f"  {'rule':<7} {'status':<15} {'score':>6}  principle",
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
        total = len(self.results)
        lines = [
            f"### Compliance report -- `{self.run_id}`",
            "",
            f"**Overall score:** {self.compliance_score:.3f} &nbsp;&nbsp; "
            f"**Rules passed:** {self.rules_passed}/{total} &nbsp;&nbsp; "
            f"**Pass rate:** {self.pass_rate:.0%}",
            "",
            f"**Manifest:** {self._manifest_line()} &nbsp;&nbsp; "
            f"*generated {self.generated_at:%Y-%m-%d}*",
        ]
        if self.extraction is not None:
            lines += ["", f"**Extracted:** {self.extraction.one_line()}"]
        lines += [
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
