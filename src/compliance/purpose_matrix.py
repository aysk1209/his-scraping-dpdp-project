"""Score one extraction under every recognised purpose.

The benchmark (``compliance.benchmark``) varies the *technique* and holds the
purpose fixed. This varies the *purpose* and holds the extraction fixed, which
isolates a claim the benchmark cannot make on its own:

    compliance is not a property of a data pull. It is a property of a data pull
    together with the purpose it is pulled for.

The same records, the same manifest, the same seven rules -- and a different
verdict, because the purpose changed. That is the DPDP purpose-limitation
principle stated as an experiment rather than as a sentence.

# DPDP Act 2023 -- purpose limitation principle: personal data is processed only
# for the purpose specified to the Data Principal. Lawfulness is relative to that
# purpose, which is precisely what this matrix measures.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field

from compliance.checkers import run_all
from compliance.models import ExtractedRecord, ExtractionRun, FieldCategory, Purpose
from compliance.policy import PURPOSE_POLICY
from compliance.rules.base import RuleStatus

_REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_DIR = _REPO_ROOT / "docs" / "benchmark_results"


class PurposeVerdict(BaseModel):
    """How one extraction scores when judged against one purpose."""

    purpose: str
    is_declared_purpose: bool
    compliance_score: float
    rules_passed: int
    rules_total: int
    failed_rules: list[str]
    out_of_scope_categories: list[str]
    retention_limit_days: int

    def verdict(self) -> str:
        """Why this purpose reached this score, in the reader's terms.

        Notice coverage is left out deliberately: it fails for every purpose
        other than the declared one by construction, so repeating it on every
        row would bury the reasons that actually differ.
        """

        if self.compliance_score == 1.0:
            return "lawful for this purpose"

        reasons: list[str] = []
        if self.out_of_scope_categories:
            reasons.append("out of scope: " + ", ".join(self.out_of_scope_categories))
        if "SL-01" in self.failed_rules:
            reasons.append(f"retention exceeds {self.retention_limit_days}d limit")
        if not reasons:
            reasons.append(", ".join(self.failed_rules) + " fail")
        return "; ".join(reasons)


class PurposeMatrix(BaseModel):
    """One extraction, scored against every purpose in the policy."""

    run_id: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    declared_purpose: str
    record_count: int
    extracted_categories: list[str]
    retention_days: int | None
    verdicts: list[PurposeVerdict]

    def _takeaway(self) -> str:
        declared = next(v for v in self.verdicts if v.is_declared_purpose)
        others = [v for v in self.verdicts if not v.is_declared_purpose]
        worst = min(others, key=lambda v: v.compliance_score) if others else None
        if worst is None:
            return (
                f"Only one purpose is modelled, so this extraction cannot yet be "
                f"compared across purposes."
            )
        if worst.compliance_score >= declared.compliance_score:
            return (
                f"This extraction scores {declared.compliance_score:.3f} under its "
                f"declared purpose '{declared.purpose}' and no worse under any "
                f"other -- the data it pulled happens to sit inside every modelled "
                f"purpose's scope."
            )
        return (
            f"The same records, the same manifest, the same seven rules: "
            f"{declared.compliance_score:.3f} under '{declared.purpose}', "
            f"{worst.compliance_score:.3f} under '{worst.purpose}'. Nothing about "
            f"the extraction changed -- only what it was for. Compliance is a "
            f"property of the pull and its purpose together, not of the pull alone."
        )

    def render_table(self) -> str:
        lines = [
            f"Purpose matrix -- run '{self.run_id}'",
            f"  extracted : {self.record_count} records; "
            f"categories: {', '.join(self.extracted_categories)}",
            f"  retention : {self.retention_days}d declared",
            "",
        ]
        head = f"  {'purpose':<22} {'score':>6} {'rules':>7}  verdict"
        lines += [head, "  " + "-" * (len(head) - 2)]
        for verdict in self.verdicts:
            marker = "*" if verdict.is_declared_purpose else " "
            lines.append(
                f" {marker}{verdict.purpose:<22} {verdict.compliance_score:>6.3f} "
                f"{verdict.rules_passed}/{verdict.rules_total:<5}  {verdict.verdict()}"
            )
        lines += [
            "",
            "  * = the purpose this run actually declared. For every other purpose the",
            "      notice is treated as not covering it, since the notice given to the",
            "      Data Principal named the declared purpose and not that one.",
            "",
            self._takeaway(),
        ]
        return "\n".join(lines)

    def render_markdown(self) -> str:
        lines = [
            f"### Purpose matrix — `{self.run_id}`",
            "",
            f"_{self._takeaway()}_",
            "",
            f"One extraction ({self.record_count} records; categories "
            f"{', '.join(f'`{c}`' for c in self.extracted_categories)}; "
            f"{self.retention_days}d retention declared), scored against every "
            f"purpose in the policy with the same rule set.",
            "",
            "For any purpose other than the declared one, the privacy notice is "
            "treated as not covering it — the notice given to the Data Principal "
            "named the declared purpose. That is a consequence of changing the "
            "purpose, not an adjustment made to produce a result.",
            "",
            "| Purpose | Declared | Compliance | Rules passed | Verdict |",
            "|---|---|---|---|---|",
        ]
        for verdict in self.verdicts:
            lines.append(
                f"| `{verdict.purpose}` | {'yes' if verdict.is_declared_purpose else 'no'} | "
                f"{verdict.compliance_score:.3f} | "
                f"{verdict.rules_passed}/{verdict.rules_total} | {verdict.verdict()} |"
            )
        return "\n".join(lines)

    def to_json_file(self, directory: Path | None = None) -> Path:
        directory = directory or ARTIFACT_DIR
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{self.run_id}--purpose-matrix.json"
        path.write_text(self.model_dump_json(indent=2), encoding="utf-8")
        return path

    def to_markdown_file(self, directory: Path | None = None) -> Path:
        directory = directory or ARTIFACT_DIR
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{self.run_id}--purpose-matrix.md"
        path.write_text(self.render_markdown(), encoding="utf-8")
        return path


def score_across_purposes(
    run: ExtractionRun, records: list[ExtractedRecord]
) -> PurposeMatrix:
    """Re-score one extraction under each recognised purpose in turn.

    The records, the retention period, the safeguards and the governance
    declarations are left exactly as they were, so any difference in the result
    is attributable to the purpose alone.

    One declaration cannot survive the substitution, and it would be dishonest to
    pretend otherwise: **notice coverage**. A privacy notice describes a specific
    purpose to the Data Principal, so a notice given for care coordination does
    not cover billing. Carrying ``covers_purpose=True`` into a purpose the notice
    never mentioned would assert something false, so the flag is cleared for every
    purpose other than the declared one. This is stated in the rendered output
    too -- it is a consequence of changing the purpose, not a thumb on the scale.

    Known limitation: the lawful-basis *reference* is left as-is, so LB-01 still
    passes under a purpose whose legitimate use the reference does not actually
    support. LB-01 checks that a basis is recorded, not that it fits the purpose;
    tightening that is a separate change to the rule, not to this function.
    """

    extracted: set[FieldCategory] = set()
    for record in records:
        extracted |= record.field_categories

    verdicts: list[PurposeVerdict] = []
    for purpose, policy in PURPOSE_POLICY.items():
        update: dict = {"purpose": purpose}
        if purpose != run.purpose and run.notice is not None:
            # The notice named the original purpose; it cannot cover this one.
            update["notice"] = run.notice.model_copy(update={"covers_purpose": False})
        candidate = run.model_copy(update=update)
        report = run_all(candidate, records)
        failed = [
            result.rule_id
            for result in report.results
            if result.status == RuleStatus.FAIL
        ]
        verdicts.append(
            PurposeVerdict(
                purpose=purpose.value,
                is_declared_purpose=(purpose == run.purpose),
                compliance_score=report.compliance_score,
                rules_passed=report.rules_passed,
                rules_total=len(report.results),
                failed_rules=failed,
                out_of_scope_categories=sorted(
                    c.value for c in extracted - policy.allowed_categories
                ),
                retention_limit_days=policy.max_retention_days,
            )
        )

    verdicts.sort(key=lambda v: (not v.is_declared_purpose, v.purpose))
    return PurposeMatrix(
        run_id=run.run_id,
        declared_purpose=run.purpose.value,
        record_count=len(records),
        extracted_categories=sorted(c.value for c in extracted),
        retention_days=run.retention_days,
        verdicts=verdicts,
    )


__all__ = ["PurposeMatrix", "PurposeVerdict", "score_across_purposes", "Purpose"]
