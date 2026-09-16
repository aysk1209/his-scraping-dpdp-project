"""Compliance benchmarking harness (build step 5).

Runs each extraction technique against each task, scores every run with the same
DPDP rule set, and aggregates per technique. The output -- techniques ranked by
compliance score, a per-principle breakdown, a per-task breakdown, a note of what
each technique actually pulled, and what each one cost -- is the project's core
piece of evidence: it shows compliance discriminating between *techniques*, not
just between careful and careless configurations of one.

The comparison runs on two axes. Compliance comes from the rule set; cost comes
from ``extraction.metering``, which meters every technique identically at the
adapter boundary. The two are not independent: ``excess_ratio`` (fields pulled
over fields the purpose requires) is both a cost measure and a restatement of the
data-minimisation principle, so the table can say how compliance and cost move
relative to each other instead of asserting that compliance is affordable.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median
from typing import Any

from pydantic import BaseModel, Field

from compliance.checkers import run_all
from compliance.rules import ALL_RULES
from compliance.rules.base import RuleStatus
from compliance.summary import merge
from extraction.base import HISDataSource
from extraction.metering import ExtractionCost, MeteredSource, combine
from extraction.technique import ExtractionTask, ExtractionTechnique

_REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_DIR = _REPO_ROOT / "docs" / "benchmark_results"
_RULE_IDS = [rule.rule_id for rule in ALL_RULES]
_RULE_TITLES = {rule.rule_id: rule.title for rule in ALL_RULES}


def _short(technique) -> str:
    short = getattr(technique, "short_id", None)
    return short or technique.name.split()[0].rstrip(",")


class TechniqueScore(BaseModel):
    technique: str
    short: str
    mean_compliance_score: float
    mean_pass_rate: float
    rules_passed: str                       # e.g. "7/7" (worst-case across tasks)
    record_count: int
    pulled_note: str                        # ExtractionSummary.one_line() across all tasks
    per_rule_mean: dict[str, float | None]
    per_task: dict[str, float]
    cost: ExtractionCost = Field(default_factory=ExtractionCost)
    # Over ``repeats`` identical runs, how many reproduced the first run's
    # decision -- the same fields pulled and the same manifest declared. A
    # rule-driven technique is stable by construction; an AI agent's decision
    # can change on identical input, and this is where that shows.
    repeats: int = 1
    stable_runs: int = 1          # same fields *and* same manifest structure
    stable_fields: int = 1        # same fields, whatever the manifest said

    @property
    def determinism(self) -> float:
        return self.stable_runs / self.repeats if self.repeats else 1.0


class TaskDetail(BaseModel):
    task_id: str
    purpose: str
    needs: list[str]                        # "field, field @ layer" strings


class BenchmarkResult(BaseModel):
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    dataset_note: str = ""
    elapsed_ms: float | None = None
    task_ids: list[str]
    task_details: list[TaskDetail] = Field(default_factory=list)
    rule_ids: list[str]
    scores: list[TechniqueScore]

    @staticmethod
    def _fmt(value: float | None) -> str:
        return "  n/a" if value is None else f"{value:.2f}"

    def _takeaway(self) -> str:
        """State the compliance gap, then what it cost -- measured, not assumed."""

        best, worst = self.scores[0], self.scores[-1]
        gap = round(best.mean_compliance_score - worst.mean_compliance_score, 3)
        line = (
            f"{best.technique} scores {best.mean_compliance_score:.3f}; "
            f"{worst.technique} scores {worst.mean_compliance_score:.3f} on the "
            f"same {len(self.rule_ids)} rules -- a {gap:.3f} gap."
        )

        cheap, dear = best.cost.excess_ratio, worst.cost.excess_ratio
        if cheap is None or dear is None:
            return line

        # Coverage first. Two different things put coverage below 1.0 and they
        # must not be confused: a technique that *left out* fields the task needs
        # (an agent deciding for itself what a job requires), and a source that simply
        # does not carry them -- a hospital export missing a column caps every
        # technique at the same ceiling, and that is a fact about the data, not
        # about any technique's compliance.
        ceiling = self.source_ceiling()
        at_ceiling = " at full coverage" if ceiling is None else ""
        if ceiling is not None:
            missing = best.cost.needed_fields - best.cost.matched_fields
            line += (
                f" Every technique obtained the same {ceiling:.0%} of the fields the "
                f"tasks require -- the source itself lacks {missing} of the "
                f"{best.cost.needed_fields}, so coverage is a property of this "
                f"dataset and the comparison holds on what it does carry."
            )
        elif best.cost.coverage is not None and best.cost.coverage < 1.0:
            return (
                f"{line} Note that it obtained only {best.cost.coverage:.0%} of the "
                f"fields the tasks require, so its score is not directly comparable "
                f"-- under-coverage, not efficiency."
            )

        if dear > cheap:
            line += (
                f" It also pulls {cheap:.2f}x the fields the purpose requires, "
                f"against {dear:.2f}x for {worst.technique}{at_ceiling}. That surplus "
                f"is exactly what the data-minimisation rule penalises, so on this "
                f"workload compliance and extraction cost move together rather than "
                f"trading off against each other."
            )
        else:
            line += (
                f" It pulls {cheap:.2f}x the fields the purpose requires against "
                f"{dear:.2f}x for {worst.technique} -- a measured compliance premium on "
                f"this workload, not an assumed one."
            )

        # A technique that did not obtain what the tasks need -- below the
        # source's ceiling, if there is one -- has a different failure from
        # over-collection, and the line should name it.
        floor = ceiling if ceiling is not None else 1.0
        short = [
            s for s in self.scores[1:]
            if s.cost.coverage is not None and s.cost.coverage < floor
        ]
        if short:
            s = short[0]
            line += (
                f" {s.technique} obtained only {s.cost.coverage:.0%} of the fields the "
                f"tasks require: it left out data the purpose lawfully needed, so its "
                f"low cost is a shortfall, not efficiency."
            )

        unstable = [
            s for s in self.scores if s.repeats > 1 and s.stable_runs < s.repeats
        ]
        if unstable:
            s = unstable[0]
            line += (
                f" Over {s.repeats} identical runs, {s.technique} reproduced its own "
                f"decision {s.stable_runs} time(s) -- its field selection alone "
                f"{s.stable_fields} time(s); {best.technique} reproduced it "
                f"{best.stable_runs} of {best.repeats}. A rule-driven technique is "
                f"deterministic by construction; an agent's compliance is a sample."
            )
        return line

    def source_ceiling(self) -> float | None:
        """Coverage the source caps every technique at, or None when it caps none.

        When the best-covering technique still misses needed fields *and* the
        widest-pulling technique (the one that takes everything it can see)
        covers no more, the fields are absent from the source, not withheld by
        a technique.
        """

        covered = [s for s in self.scores if s.cost.coverage is not None]
        if not covered:
            return None
        top = max(covered, key=lambda s: s.cost.coverage)
        if top.cost.coverage >= 1.0:
            return None
        widest = max(covered, key=lambda s: s.cost.excess_ratio or 0.0)
        return top.cost.coverage if widest.cost.coverage == top.cost.coverage else None

    def render_table(self) -> str:
        lines: list[str] = []
        meta = []
        if self.dataset_note:
            meta.append(self.dataset_note)
        meta.append(f"{len(self.task_ids)} tasks")
        if self.elapsed_ms is not None:
            meta.append(f"{self.elapsed_ms:.0f} ms")
        lines.append("dataset: " + " - ".join(meta))
        lines.append("")

        head = (
            f"{'technique':<32} {'score':>6} {'pass':>7}  "
            + " ".join(f"{rid:>6}" for rid in self.rule_ids)
        )
        lines += [head, "-" * len(head)]
        for score in self.scores:
            row = (
                f"{score.technique:<32} {score.mean_compliance_score:>6.3f} "
                f"{score.rules_passed:>7}  "
                + " ".join(f"{self._fmt(score.per_rule_mean.get(rid)):>6}" for rid in self.rule_ids)
            )
            lines.append(row)

        lines += ["", "cost profile (deterministic metrics lead; wall-clock is hardware-dependent):"]
        show_loads = any(s.cost.page_loads is not None for s in self.scores)
        show_stable = any(s.repeats > 1 for s in self.scores)
        cost_head = (
            f"  {'technique':<30} {'excess':>7} {'cover':>6} {'distinct':>9} {'fields':>8} "
            f"{'fetches':>8}" + (f" {'pages':>7}" if show_loads else "")
            + f" {'records':>8} {'ms':>8}" + (f" {'stable':>8}" if show_stable else "")
        )
        lines += [cost_head, "  " + "-" * (len(cost_head) - 2)]
        for score in self.scores:
            cost = score.cost
            loads = f" {cost.page_loads if cost.page_loads is not None else '-':>7}" if show_loads else ""
            distinct = f"{cost.distinct_fields}/{cost.needed_fields}"
            stable = f" {f'{score.stable_runs}/{score.repeats}':>8}" if show_stable else ""
            lines.append(
                f"  {score.technique:<30} {self._fmt(cost.excess_ratio):>7} "
                f"{self._fmt(cost.coverage):>6} {distinct:>9} {cost.fields_pulled:>8} "
                f"{cost.fetches:>8}{loads} {cost.records:>8} {cost.elapsed_ms:>8.1f}{stable}"
            )
        lines.append(
            "  distinct = distinct fields pulled / fields the purpose requires "
            "(excess is that ratio); cover = how much of the requirement was met"
            + ("; stable = runs that reproduced the first run's decision." if show_stable else ".")
        )

        lines += ["", "per task (scores key on data category and manifest, not record volume):"]
        task_head = f"  {'task':<22}" + "".join(f"{s.short:>16}" for s in self.scores)
        lines += [task_head, "  " + "-" * (len(task_head) - 2)]
        for task_id in self.task_ids:
            row = f"  {task_id:<22}" + "".join(
                f"{s.per_task.get(task_id, float('nan')):>16.3f}" for s in self.scores
            )
            lines.append(row)

        lines += ["", f"what each technique pulled (total over the {len(self.task_ids)}-task workload):"]
        for score in self.scores:
            lines.append(f"  {score.short:<17} {score.pulled_note}")

        lines += ["", self._takeaway()]
        return "\n".join(lines)

    def render_markdown(self) -> str:
        header = "| Technique | Compliance score | Rules passed | " + " | ".join(self.rule_ids) + " |"
        sep = "|" + "---|" * (3 + len(self.rule_ids))
        lines = [
            "### Compliance benchmark",
            "",
            f"_{self._takeaway()}_",
            "",
            f"Source: {self.dataset_note or 'n/a'}. "
            f"{len(self.task_ids)} extraction tasks, identical DPDP rule set for every "
            f"technique. Generated {self.generated_at:%Y-%m-%d}"
            + (f" in {self.elapsed_ms:.0f} ms" if self.elapsed_ms is not None else "")
            + " (wall-clock, hardware-dependent).",
            "",
            header,
            sep,
        ]
        for score in self.scores:
            cells = " | ".join(self._fmt(score.per_rule_mean.get(rid)) for rid in self.rule_ids)
            lines.append(
                f"| {score.technique} | {score.mean_compliance_score:.3f} | "
                f"{score.rules_passed} | {cells} |"
            )

        lines += [
            "",
            "**Compliance versus cost**",
            "",
            "`excess ratio` is distinct fields pulled divided by the fields the task's "
            "purpose requires. It is a cost measure and a compliance measure at once: "
            "fields pulled beyond the purpose are precisely the overreach the "
            "data-minimisation rule penalises. `coverage` is the guard rail -- it stops a "
            "technique scoring well by pulling nothing. Both are deterministic and "
            "reproduce on any machine; wall-clock time is reported but is "
            "hardware-dependent. `stable runs` is how many of the repeated runs "
            "reproduced the first run's decision -- the same fields, the same "
            "manifest -- on identical input.",
            "",
            "| Technique | Compliance | Excess ratio | Coverage | Distinct fields / needed | Fields pulled | Fetches | Pages loaded | Records | Wall-clock (ms) | Stable runs |",
            "|---|---|---|---|---|---|---|---|---|---|---|",
        ]
        for score in self.scores:
            cost = score.cost
            loads = cost.page_loads if cost.page_loads is not None else "n/a"
            stable = f"{score.stable_runs} / {score.repeats}" if score.repeats > 1 else "n/a"
            lines.append(
                f"| {score.technique} | {score.mean_compliance_score:.3f} | "
                f"{self._fmt(cost.excess_ratio)} | {self._fmt(cost.coverage)} | "
                f"{cost.distinct_fields} / {cost.needed_fields} | "
                f"{cost.fields_pulled} | {cost.fetches} | {loads} | {cost.records} | "
                f"{cost.elapsed_ms:.1f} | {stable} |"
            )

        lines += ["", "**Per task**", "",
                  "| Task | " + " | ".join(s.short for s in self.scores) + " |",
                  "|" + "---|" * (1 + len(self.scores))]
        for task_id in self.task_ids:
            cells = " | ".join(f"{s.per_task.get(task_id, float('nan')):.3f}" for s in self.scores)
            lines.append(f"| `{task_id}` | {cells} |")

        if self.task_details:
            lines += ["", "**What each task needs**", ""]
            for detail in self.task_details:
                lines.append(
                    f"- `{detail.task_id}` (*{detail.purpose}*): "
                    + "; ".join(detail.needs)
                )

        lines += ["", f"**What each technique pulled** (total over the {len(self.task_ids)}-task workload)", ""]
        for score in self.scores:
            lines.append(f"- **{score.short}** — {score.pulled_note}")

        lines += ["", "**Rules** (each scores 0–1 per run; the table shows the mean over tasks)", ""]
        for rid in self.rule_ids:
            lines.append(f"- `{rid}` — {_RULE_TITLES.get(rid, rid)}")
        return "\n".join(lines)

    def to_json_file(self, directory: Path | None = None, *, name: str = "benchmark") -> Path:
        directory = directory or ARTIFACT_DIR
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{name}.json"
        path.write_text(self.model_dump_json(indent=2), encoding="utf-8")
        return path

    def to_markdown_file(self, directory: Path | None = None, *, name: str = "benchmark") -> Path:
        directory = directory or ARTIFACT_DIR
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{name}.md"
        path.write_text(self.render_markdown(), encoding="utf-8")
        return path


def _task_detail(task: ExtractionTask) -> TaskDetail:
    needs = [
        f"{', '.join(item.fields)} @ {item.layer.value}" for item in task.needed
    ]
    return TaskDetail(task_id=task.task_id, purpose=task.purpose.value, needs=needs)


def _run_task(
    technique: ExtractionTechnique,
    task: ExtractionTask,
    source: HISDataSource,
    repeats: int,
):
    """Run one technique against one task, metered. Returns (output, cost).

    With ``repeats`` above 1 the run is repeated and the *median* wall-clock is
    kept, which is the only way a hardware-dependent number is worth reporting.
    The deterministic counts are identical across repeats, so the last run's
    meter is used for them.
    """

    elapsed: list[float] = []
    decisions: list[tuple] = []
    for i in range(max(1, repeats)):
        if hasattr(technique, "sample"):
            technique.sample = i               # a recorded agent replays its i-th decision
        metered = MeteredSource(source)
        started = time.perf_counter()
        output = technique.extract(metered, task)
        elapsed.append((time.perf_counter() - started) * 1000)
        decisions.append(_decision_key(output, metered))
    stable = sum(1 for d in decisions if d == decisions[0])
    stable_fields = sum(1 for d in decisions if d[0] == decisions[0][0])
    return output, metered.cost(task.field_refs(), median(elapsed)), stable, stable_fields


def manifest_structure(run) -> dict[str, Any]:
    """A manifest reduced to the decisions it embodies, for comparing runs.

    Whether a basis, a notice, a deletion mechanism or an accountable party was
    declared -- not how the declaration was worded. Two runs that cite the same
    section in different words made the same decision; two runs that disagree
    on whether identifiers are pseudonymised did not.
    """

    return {
        "purpose_specified": run.purpose_specified,
        "secondary_uses": tuple(sorted(run.secondary_uses)),
        "lawful_basis": run.lawful_basis.type.value if run.lawful_basis else None,
        "basis_referenced": bool(run.lawful_basis and run.lawful_basis.reference),
        "retention_days": run.retention_days,
        "deletion_mechanism": bool(run.deletion_mechanism),
        "transport_encrypted": run.security.transport_encrypted,
        "at_rest_encrypted": run.security.at_rest_encrypted,
        "access_controlled": run.security.access_controlled,
        "identifiers_pseudonymised": run.security.identifiers_pseudonymised,
        "notice": bool(run.notice),
        "notice_covers_purpose": bool(run.notice and run.notice.covers_purpose),
        "notice_machine_readable": bool(run.notice and run.notice.machine_readable),
        "audit_log": run.governance.audit_log_enabled,
        "accountable_party": bool(run.governance.accountable_party),
        "processing_record": run.governance.processing_record_kept,
    }


def _decision_key(output, metered: MeteredSource) -> tuple:
    """What a run decided, for comparing repeats: fields pulled + manifest structure."""

    return (tuple(sorted(metered.pulled)), tuple(sorted(manifest_structure(output.run).items())))


def run_benchmark(
    techniques: list[ExtractionTechnique],
    tasks: list[ExtractionTask],
    source: HISDataSource,
    *,
    dataset_note: str = "",
    repeats: int = 1,
) -> BenchmarkResult:
    """Score every technique against every task; aggregate per technique."""

    started = time.perf_counter()
    scores: list[TechniqueScore] = []
    for technique in techniques:
        per_task: dict[str, float] = {}
        pass_rates: list[float] = []
        passed_counts: list[int] = []
        rule_scores: dict[str, list[float]] = {rid: [] for rid in _RULE_IDS}
        summaries = []
        costs: list[ExtractionCost] = []
        stable_total = 0
        stable_fields_total = 0

        for task in tasks:
            output, cost, stable, stable_fields = _run_task(technique, task, source, repeats)
            costs.append(cost)
            stable_total += stable
            stable_fields_total += stable_fields
            report = run_all(output.run, output.records)
            per_task[task.task_id] = round(report.compliance_score, 3)
            pass_rates.append(report.pass_rate)
            passed_counts.append(report.rules_passed)
            if report.extraction is not None:
                summaries.append(report.extraction)
            for result in report.results:
                if result.status != RuleStatus.NOT_APPLICABLE:
                    rule_scores[result.rule_id].append(result.score)

        pulled = merge(summaries) if summaries else None
        scores.append(
            TechniqueScore(
                technique=technique.name,
                short=_short(technique),
                mean_compliance_score=round(mean(per_task.values()), 3),
                mean_pass_rate=round(mean(pass_rates), 3),
                rules_passed=f"{min(passed_counts)}/{len(_RULE_IDS)}",
                record_count=pulled.record_count if pulled else 0,
                pulled_note=pulled.one_line() if pulled else "no records",
                per_rule_mean={
                    rid: (round(mean(vals), 3) if vals else None)
                    for rid, vals in rule_scores.items()
                },
                per_task=per_task,
                cost=combine(costs),
                repeats=max(1, repeats),
                stable_runs=round(stable_total / max(1, len(tasks))),
                stable_fields=round(stable_fields_total / max(1, len(tasks))),
            )
        )

    scores.sort(key=lambda s: s.mean_compliance_score, reverse=True)
    return BenchmarkResult(
        dataset_note=dataset_note,
        elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
        task_ids=[t.task_id for t in tasks],
        task_details=[_task_detail(t) for t in tasks],
        rule_ids=list(_RULE_IDS),
        scores=scores,
    )
