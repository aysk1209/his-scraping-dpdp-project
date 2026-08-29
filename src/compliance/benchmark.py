"""Compliance benchmarking harness (build step 5).

Runs each extraction technique against each task, scores every run with the same
DPDP rule set, and aggregates per technique. The output table -- techniques
ranked by compliance score, with a per-principle breakdown -- is the project's
core piece of evidence: it shows compliance discriminating between *techniques*,
not just between careful and careless configurations of one.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

from pydantic import BaseModel, Field

from compliance.checkers import run_all
from compliance.rules import ALL_RULES
from compliance.rules.base import RuleStatus
from extraction.base import HISDataSource
from extraction.technique import ExtractionTask, ExtractionTechnique

_REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_DIR = _REPO_ROOT / "docs" / "benchmark_results"
_RULE_IDS = [rule.rule_id for rule in ALL_RULES]


class TechniqueScore(BaseModel):
    technique: str
    mean_compliance_score: float
    mean_pass_rate: float
    per_rule_mean: dict[str, float | None]
    per_task: dict[str, float]


class BenchmarkResult(BaseModel):
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    task_ids: list[str]
    rule_ids: list[str]
    scores: list[TechniqueScore]

    @staticmethod
    def _fmt(value: float | None) -> str:
        return "  n/a" if value is None else f"{value:.2f}"

    def render_table(self) -> str:
        head = (
            f"{'technique':<28} {'score':>7} {'pass':>6}  "
            + " ".join(f"{rid:>6}" for rid in self.rule_ids)
        )
        lines = [
            "Compliance benchmark -- techniques ranked by score",
            "",
            head,
            "-" * len(head),
        ]
        for score in self.scores:
            row = (
                f"{score.technique:<28} {score.mean_compliance_score:>7.3f} "
                f"{score.mean_pass_rate:>6.0%}  "
                + " ".join(f"{self._fmt(score.per_rule_mean.get(rid)):>6}" for rid in self.rule_ids)
            )
            lines.append(row)
        lines += ["", f"tasks: {', '.join(self.task_ids)}"]
        return "\n".join(lines)

    def render_markdown(self) -> str:
        header = "| Technique | Compliance score | Pass rate | " + " | ".join(self.rule_ids) + " |"
        sep = "|" + "---|" * (3 + len(self.rule_ids))
        lines = [
            "### Compliance benchmark",
            "",
            f"Techniques scored against {len(self.task_ids)} task(s): "
            + ", ".join(f"`{t}`" for t in self.task_ids)
            + ". Identical DPDP rule set for every technique.",
            "",
            header,
            sep,
        ]
        for score in self.scores:
            cells = " | ".join(self._fmt(score.per_rule_mean.get(rid)) for rid in self.rule_ids)
            lines.append(
                f"| {score.technique} | {score.mean_compliance_score:.3f} | "
                f"{score.mean_pass_rate:.0%} | {cells} |"
            )
        return "\n".join(lines)

    def to_json_file(self, directory: Path | None = None) -> Path:
        directory = directory or ARTIFACT_DIR
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / "benchmark.json"
        path.write_text(self.model_dump_json(indent=2), encoding="utf-8")
        return path

    def to_markdown_file(self, directory: Path | None = None) -> Path:
        directory = directory or ARTIFACT_DIR
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / "benchmark.md"
        path.write_text(self.render_markdown(), encoding="utf-8")
        return path


def run_benchmark(
    techniques: list[ExtractionTechnique],
    tasks: list[ExtractionTask],
    source: HISDataSource,
) -> BenchmarkResult:
    """Score every technique against every task; aggregate per technique."""

    scores: list[TechniqueScore] = []
    for technique in techniques:
        per_task: dict[str, float] = {}
        pass_rates: list[float] = []
        rule_scores: dict[str, list[float]] = {rid: [] for rid in _RULE_IDS}

        for task in tasks:
            output = technique.extract(source, task)
            report = run_all(output.run, output.records)
            per_task[task.task_id] = round(report.compliance_score, 3)
            pass_rates.append(report.pass_rate)
            for result in report.results:
                if result.status != RuleStatus.NOT_APPLICABLE:
                    rule_scores[result.rule_id].append(result.score)

        scores.append(
            TechniqueScore(
                technique=technique.name,
                mean_compliance_score=round(mean(per_task.values()), 3),
                mean_pass_rate=round(mean(pass_rates), 3),
                per_rule_mean={
                    rid: (round(mean(vals), 3) if vals else None)
                    for rid, vals in rule_scores.items()
                },
                per_task=per_task,
            )
        )

    scores.sort(key=lambda s: s.mean_compliance_score, reverse=True)
    return BenchmarkResult(
        task_ids=[t.task_id for t in tasks],
        rule_ids=list(_RULE_IDS),
        scores=scores,
    )
