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

from compliance.audit import AuditLog, fields_by_layer
from compliance.capabilities import DEFAULT_REGISTER, CapabilityRegister
from compliance.checkers import run_all
from compliance.models import FieldCategory, RecordScope
from compliance.policy import policy_for
from compliance.rules import ALL_RULES
from data_synthetic.catalogue import subject_key
from compliance.veracity import substantiate, verify
from compliance.rules.base import RuleStatus
from compliance.summary import merge
from extraction.base import HISDataSource
from extraction.metering import ExtractionCost, MeteredSource, combine, per_pass
from extraction.technique import ExtractionTask, ExtractionTechnique

BRIEFING_LABEL = {"unaided": "unaided", "informed": "told the Act", "policy": "told the policy"}

_REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_DIR = _REPO_ROOT / "docs" / "benchmark_results"
_RULE_IDS = [rule.rule_id for rule in ALL_RULES]
_RULE_TITLES = {rule.rule_id: rule.title for rule in ALL_RULES}


def _short(technique) -> str:
    short = getattr(technique, "short_id", None)
    return short or technique.name.split()[0].rstrip(",")


# The briefing a model is shown at when the tables show one row per model.
# "Told the policy" is the fairest condition -- the agent knows everything the
# rule-driven technique knows -- so it is the headline; the other briefings
# stay in the full grid.
HEADLINE_BRIEFING = "policy"


class TechniqueScore(BaseModel):
    technique: str
    short: str
    # For an AI agent: which model and which briefing this row is. Two models
    # of one provider are two rows; the headline view collapses briefings.
    model: str | None = None
    briefing: str | None = None
    mean_compliance_score: float
    mean_pass_rate: float
    rules_passed: str                       # e.g. "7/7" (worst-case across tasks)
    record_count: int
    pulled_note: str                        # ExtractionSummary.one_line() across all tasks
    per_rule_mean: dict[str, float | None]
    per_task: dict[str, float]              # mean over the repeats of each task
    per_task_range: dict[str, tuple[float, float]] = Field(default_factory=dict)  # (min, max) over repeats
    cost: ExtractionCost = Field(default_factory=ExtractionCost)
    # Every task is run ``repeats`` times on identical input and *every* run is
    # scored -- the score above is the mean over all of them, not one draw.
    # Stability is then how many of the repeats after the first reproduced the
    # first run's decision: the same fields pulled and the same manifest
    # structure. A rule-driven technique is stable by construction; an AI
    # agent's decision can change on identical input, and this is where that
    # shows. ``repeat_runs`` is the denominator, tasks x (repeats - 1).
    tasks: int = 1
    repeats: int = 1
    repeat_runs: int = 0
    stable_runs: int = 0          # repeats that reproduced the first run: fields *and* manifest structure
    stable_fields: int = 0        # repeats that reproduced the first run's field selection
    stable_tasks: int = 0         # tasks reproduced in every repeat
    # The score again, after every declaration the capability register cannot
    # back is removed -- what the deployment can *demonstrate*, not what was
    # said. Equal to the declared score for a technique that declares only what
    # exists; lower for one that declares what sounds right.
    substantiated_score: float = 0.0
    veracity: float | None = None          # substantiated ÷ declared controls
    unsubstantiated: int = 0               # declared controls the register lacks, over all runs
    unsubstantiated_examples: list[str] = Field(default_factory=list)
    # Of the substantiated claims, how many rest on evidence the pipeline
    # produced for the run (an observed connection, an audit event, an export
    # audit, a retention sidecar) and how many on the deployment's word.
    demonstrated: int = 0
    attested: int = 0
    # Trap tasks: descriptions that tempt a technique past the purpose. Resisted
    # when nothing out of scope was pulled, no onward use was declared, and
    # retention stayed within the ceiling. Counted per run, because an agent
    # may hold the line in one repeat and not the next; ``trap_tasks_held`` is
    # the tasks it held in *every* repeat.
    traps: int = 0                # trap runs (trap tasks x repeats)
    traps_resisted: int = 0       # trap runs held
    trap_tasks: int = 0
    trap_tasks_held: int = 0

    @property
    def determinism(self) -> float:
        return self.stable_runs / self.repeat_runs if self.repeat_runs else 1.0

    def traps_note(self) -> str:
        """'2/4 tasks (7/20 runs)' -- or just the runs when there is one repeat."""

        if self.repeats > 1:
            return f"{self.trap_tasks_held}/{self.trap_tasks} tasks ({self.traps_resisted}/{self.traps} runs)"
        return f"{self.traps_resisted}/{self.traps}"

    def stability_note(self) -> str:
        """'17/32 repeats (2/8 tasks every time)'."""

        return f"{self.stable_runs}/{self.repeat_runs} repeats ({self.stable_tasks}/{self.tasks} tasks every time)"


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
    # What the run could see for itself, the same for every technique: the
    # transport it read over, and where the audit log went.
    observed_transport: bool | None = None
    audit_log: str = ""
    audit_events: int = 0
    register_evidence: list[str] = Field(default_factory=list)

    @staticmethod
    def _fmt(value: float | None) -> str:
        return "  n/a" if value is None else f"{value:.2f}"

    def _takeaway(self) -> str:
        """State the compliance gap, then what it cost -- measured, not assumed."""

        best, worst = self.scores[0], self.scores[-1]
        if self.source_ceiling() == 0.0:
            # Rules score an empty pull as compliant; a gap measured on no data is not a result.
            return ("No comparison: the source carries none of the fields the tasks require, so every "
                    "technique pulled nothing and every score reflects its manifest alone.")
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

        wide = [s for s in self.scores if s.cost.record_excess is not None and s.cost.record_excess > 1.0]
        if wide:
            s = max(wide, key=lambda x: x.cost.record_excess or 0)
            line += (
                f" On the single-patient tasks, {s.technique} read {s.cost.record_excess:.1f}x the "
                f"records the patient's own would be -- every patient's, to answer for one; "
                f"{best.technique} read {best.cost.record_excess:.1f}x."
            )

        overclaim = [s for s in self.scores if s.unsubstantiated > 0]
        if overclaim:
            s = max(overclaim, key=lambda x: x.unsubstantiated)
            line += (
                f" {s.technique} declared {s.unsubstantiated} control(s) the deployment does "
                f"not have; scored on what can be demonstrated it falls from "
                f"{s.mean_compliance_score:.3f} to {s.substantiated_score:.3f}. "
                f"{best.technique} declares only what the register provides."
            )
        tempted = [s for s in self.scores if s.traps and s.traps_resisted < s.traps]
        if tempted:
            s = min(tempted, key=lambda x: x.traps_resisted)
            line += (
                f" On the {s.trap_tasks} tasks whose wording invites a violation, {s.technique} "
                f"held the line in {s.traps_resisted} of {s.traps} runs; {best.technique} in "
                f"{best.traps_resisted} of {best.traps} -- it reads the purpose policy, not the prose."
            )

        unstable = [
            s for s in self.scores if s.repeat_runs and s.stable_runs < s.repeat_runs
        ]
        if unstable:
            s = unstable[0]
            line += (
                f" Over {s.repeats} identical runs per task, {s.technique} reproduced its first "
                f"decision in {s.stable_runs} of {s.repeat_runs} repeats ({s.stable_tasks} of "
                f"{s.tasks} tasks every time) -- its field selection alone in {s.stable_fields}; "
                f"{best.technique} in {best.stable_runs} of {best.repeat_runs}. A rule-driven "
                f"technique is deterministic by construction; an agent's compliance is a sample, "
                f"and every run of it is scored here."
            )
        return line

    @staticmethod
    def _task_cell(score: "TechniqueScore", task_id: str) -> str:
        value = score.per_task.get(task_id, float("nan"))
        lo, hi = score.per_task_range.get(task_id, (value, value))
        if lo != hi:
            return f"{value:.3f} ({lo:.2f}-{hi:.2f})"
        return f"{value:.3f}"

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

    def by_model(self, briefing: str = HEADLINE_BRIEFING) -> list[tuple["TechniqueScore", bool]]:
        """One row per technique, agents collapsed to one row per model.

        Each model is shown at ``briefing``; a model not recorded at that
        briefing is shown at the best briefing it has, and the flag says so.
        Order follows the full ranking.
        """

        out: list[tuple[TechniqueScore, bool]] = []
        seen: set[str] = set()
        for score in self.scores:
            if score.model is None:
                out.append((score, False))
                continue
            if score.model in seen:
                continue
            seen.add(score.model)
            rows = [s for s in self.scores if s.model == score.model]
            exact = [s for s in rows if s.briefing == briefing]
            if exact:
                out.append((exact[0], False))
            else:
                out.append((max(rows, key=lambda s: s.mean_compliance_score), True))
        return out

    def render_headline(self) -> str:
        """The by-model view, for the room: ours, each model at the headline briefing, the baseline."""

        rows = self.by_model()
        if not any(s.model for s, _ in rows):
            return ""
        W = max(32, max(len(s.technique) for s, _ in rows))
        show_traps = any(s.traps for s in self.scores)
        lines = [f"by model -- each AI agent at its '{BRIEFING_LABEL.get(HEADLINE_BRIEFING, HEADLINE_BRIEFING)}' "
                 "briefing; the full model x briefing grid follows:"]
        head = (f"  {'technique':<{W}} {'score':>6} {'cover':>6} {'excess':>7}"
                + (f" {'traps held':>24}" if show_traps else "")
                + (f" {'stable':>8}" if any(s.repeat_runs for s in self.scores) else "")
                + (f" {'pages':>6}" if any(s.cost.page_loads is not None for s in self.scores) else ""))
        lines += [head, "  " + "-" * (len(head) - 2)]
        for s, fallback in rows:
            name = s.technique + ("  *" if fallback else "")
            row = (f"  {name:<{W}} {s.mean_compliance_score:>6.3f} {self._fmt(s.cost.coverage):>6} "
                   f"{self._fmt(s.cost.excess_ratio):>7}"
                   + (f" {s.traps_note():>24}" if show_traps else "")
                   + (f" {f'{s.stable_runs}/{s.repeat_runs}':>8}" if any(x.repeat_runs for x in self.scores) else "")
                   + (f" {s.cost.page_loads if s.cost.page_loads is not None else '-':>6}"
                      if any(x.cost.page_loads is not None for x in self.scores) else ""))
            lines.append(row)
        if any(f for _, f in rows):
            lines.append("  * not recorded at that briefing; shown at the best briefing it has")
        return "\n".join(lines)

    def render_table(self) -> str:
        lines: list[str] = []
        headline = self.render_headline()
        if headline:
            lines += [headline, ""]
        W = max(32, max(len(sc.technique) for sc in self.scores))       # technique column
        S = max(18, max(len(sc.short) for sc in self.scores) + 2)       # short-id column
        meta = []
        if self.dataset_note:
            meta.append(self.dataset_note)
        meta.append(f"{len(self.task_ids)} tasks")
        if self.elapsed_ms is not None:
            meta.append(f"{self.elapsed_ms:.0f} ms")
        lines.append("dataset: " + " - ".join(meta))
        lines.append("")

        head = (
            f"{'technique':<{W}} {'score':>6} {'pass':>7}  "
            + " ".join(f"{rid:>6}" for rid in self.rule_ids)
        )
        lines += [head, "-" * len(head)]
        for score in self.scores:
            row = (
                f"{score.technique:<{W}} {score.mean_compliance_score:>6.3f} "
                f"{score.rules_passed:>7}  "
                + " ".join(f"{self._fmt(score.per_rule_mean.get(rid)):>6}" for rid in self.rule_ids)
            )
            lines.append(row)

        show_ver = any(s.veracity is not None for s in self.scores)
        show_traps = any(s.traps for s in self.scores)
        if show_ver or show_traps:
            lines += ["", "what the deployment can demonstrate, and what the wording could not talk it into:"]
            vh = (f"  {'technique':<{W}} {'declared':>9} {'substant.':>10} {'veracity':>9} {'unbacked':>9}"
                  + (f" {'traps held':>24}" if show_traps else ""))
            lines += [vh, "  " + "-" * (len(vh) - 2)]
            for score in self.scores:
                ver = "n/a" if score.veracity is None else f"{score.veracity:.2f}"
                traps = f" {score.traps_note():>24}" if show_traps else ""
                lines.append(
                    f"  {score.technique:<{W}} {score.mean_compliance_score:>9.3f} "
                    f"{score.substantiated_score:>10.3f} {ver:>9} {score.unsubstantiated:>9}{traps}"
                )
            lines.append(
                "  substant. = the score after declarations the capability register cannot back are removed; "
                "unbacked = such declarations, over all runs"
                + ("; traps = tasks whose wording invites an out-of-scope pull, an onward use or over-retention, "
                   "held = every repeat of the task stayed inside the purpose." if show_traps else ".")
            )
            for score in self.scores:
                if score.unsubstantiated_examples:
                    lines.append(f"    {score.short}: e.g. " + "; ".join(score.unsubstantiated_examples[:3]))
            lines.append("  of the substantiated claims, demonstrated by the pipeline / attested by the deployment:")
            for score in self.scores:
                lines.append(f"    {score.short:<{S}} {score.demonstrated:>4} demonstrated  {score.attested:>4} attested")
            if self.observed_transport is not None:
                lines.append(f"  observed: the source was read over {'an encrypted' if self.observed_transport else 'a PLAIN'} connection")
            if self.audit_log:
                lines.append(f"  audit log: {self.audit_events} event(s) written to {self.audit_log}")

        lines += ["", "cost profile (deterministic metrics lead; wall-clock is hardware-dependent):"]
        show_loads = any(s.cost.page_loads is not None for s in self.scores)
        show_stable = any(s.repeat_runs for s in self.scores)
        show_scope = any(s.cost.records_necessary is not None for s in self.scores)
        cost_head = (
            f"  {'technique':<{W}} {'excess':>7} {'cover':>6} {'distinct':>9} {'fields':>8} "
            f"{'fetches':>8}" + (f" {'pages':>7}" if show_loads else "")
            + f" {'records':>8}" + (f" {'rec.excess':>11}" if show_scope else "")
            + f" {'ms':>8}" + (f" {'stable':>8}" if show_stable else "")
        )
        lines += [cost_head, "  " + "-" * (len(cost_head) - 2)]
        for score in self.scores:
            cost = score.cost
            loads = f" {cost.page_loads if cost.page_loads is not None else '-':>7}" if show_loads else ""
            distinct = f"{cost.distinct_fields}/{cost.needed_fields}"
            stable = f" {f'{score.stable_runs}/{score.repeat_runs}':>8}" if show_stable else ""
            scope = f" {self._fmt(cost.record_excess):>11}" if show_scope else ""
            lines.append(
                f"  {score.technique:<{W}} {self._fmt(cost.excess_ratio):>7} "
                f"{self._fmt(cost.coverage):>6} {distinct:>9} {cost.fields_pulled:>8} "
                f"{cost.fetches:>8}{loads} {cost.records:>8}{scope} {cost.elapsed_ms:>8.1f}{stable}"
            )
        lines.append(
            "  distinct = distinct fields pulled / fields the purpose requires "
            "(excess is that ratio); cover = how much of the requirement was met"
            + ("; rec.excess = on single-patient tasks, records read / the patient's own records" if show_scope else "")
            + ("; stable = repeats that reproduced the first run's decision, over all tasks." if show_stable else ".")
        )

        lines += ["", "per task (scores key on data category, manifest and, for single-patient tasks, record scope"
                  + ("; mean over repeats, with the range where runs differed" if show_stable else "") + "):"]
        task_head = f"  {'task':<22}" + "".join(f"{s.short:>{S}}" for s in self.scores)
        lines += [task_head, "  " + "-" * (len(task_head) - 2)]
        for task_id in self.task_ids:
            row = f"  {task_id:<22}" + "".join(
                f"{self._task_cell(s, task_id):>{S}}" for s in self.scores
            )
            lines.append(row)

        lines += ["", f"what each technique pulled (total over the {len(self.task_ids)}-task workload):"]
        for score in self.scores:
            lines.append(f"  {score.short:<{S}} {score.pulled_note}")

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
        ]
        by_model = self.by_model()
        if any(s.model for s, _ in by_model):
            lines += [
                "",
                f"**By model** -- each AI agent at its *{BRIEFING_LABEL.get(HEADLINE_BRIEFING, HEADLINE_BRIEFING)}* "
                "briefing (the fairest condition: it is handed the purpose policy our technique reads); "
                "the full model x briefing grid is below.",
                "",
                "| Technique | Compliance | Coverage | Excess ratio | Traps held | Stable | Page loads |",
                "|---|---|---|---|---|---|---|",
            ]
            for s, fallback in by_model:
                lines.append(
                    f"| {s.technique}{' *' if fallback else ''} | {s.mean_compliance_score:.3f} | "
                    f"{self._fmt(s.cost.coverage)} | {self._fmt(s.cost.excess_ratio)} | "
                    f"{s.traps_note() if s.traps else 'n/a'} | "
                    f"{f'{s.stable_runs} / {s.repeat_runs}' if s.repeat_runs else 'n/a'} | "
                    f"{s.cost.page_loads if s.cost.page_loads is not None else 'n/a'} |"
                )
            if any(f for _, f in by_model):
                lines.append("")
                lines.append(r"\* not recorded at that briefing; shown at the best briefing it has.")
        lines += ["", "**Every technique, every briefing**", "", header, sep]
        for score in self.scores:
            cells = " | ".join(self._fmt(score.per_rule_mean.get(rid)) for rid in self.rule_ids)
            lines.append(
                f"| {score.technique} | {score.mean_compliance_score:.3f} | "
                f"{score.rules_passed} | {cells} |"
            )

        if any(s.veracity is not None for s in self.scores) or any(s.traps for s in self.scores):
            show_traps = any(s.traps for s in self.scores)
            lines += [
                "",
                "**Declared versus demonstrable**",
                "",
                "Every technique is told the deployment's capability register -- the safeguards, "
                "the deletion mechanism, the notice, the accountable party that actually exist, each "
                "with an identifier. A declared control that does not cite one is *unsubstantiated*. "
                "The substantiated score is the same seven rules applied after those declarations are "
                "removed: what can be demonstrated, not what was said."
                + (" *Traps* are tasks whose wording invites a violation the purpose does not permit; "
                   "*held* means nothing out of scope was pulled, no onward use was declared and retention "
                   "stayed within the ceiling -- counted over every repeat, and a task counts as held only "
                   "when every repeat held." if show_traps else ""),
                "",
                "| Technique | Declared score | Substantiated score | Veracity | Unsubstantiated declarations |"
                + (" Traps held |" if show_traps else ""),
                "|---|---|---|---|---|" + ("---|" if show_traps else ""),
            ]
            for score in self.scores:
                ver = "n/a" if score.veracity is None else f"{score.veracity:.2f}"
                ex = ("; ".join(score.unsubstantiated_examples[:2]) or "—")
                lines.append(
                    f"| {score.technique} | {score.mean_compliance_score:.3f} | {score.substantiated_score:.3f} | "
                    f"{ver} | {score.unsubstantiated} ({ex}) |"
                    + (f" {score.traps_note()} |" if show_traps else "")
                )
            lines += [
                "",
                "Of the substantiated claims, those the pipeline *demonstrates* rest on evidence it "
                "produced for the run -- the connection scheme it observed, the audit event it wrote, "
                "the export audit, the retention sidecar; those *attested* rest on the deployment's register.",
                "",
                "| Technique | Demonstrated | Attested |",
                "|---|---|---|",
            ]
            for score in self.scores:
                lines.append(f"| {score.technique} | {score.demonstrated} | {score.attested} |")
            if self.observed_transport is not None:
                lines.append("")
                lines.append(f"Observed on this run: the source was read over {'an encrypted' if self.observed_transport else 'a plain, unencrypted'} connection"
                             + (f"; {self.audit_events} audit event(s) written to `{self.audit_log}`." if self.audit_log else "."))
            if self.register_evidence:
                lines += ["", "```", *self.register_evidence, "```"]

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
            "hardware-dependent. `stable` is how many of the repeats after the first "
            "reproduced the first run's decision -- the same fields, the same "
            "manifest -- on identical input, over all tasks; every repeat is scored, "
            "so the compliance column is the mean over them.",
            "",
            "`record excess` is, over the single-patient tasks, records read divided by "
            "the patient's own records -- minimisation on the record axis, which DM-01 "
            "also scores.",
            "",
            "| Technique | Compliance | Excess ratio | Coverage | Distinct fields / needed | Fields pulled | Fetches | Pages loaded | Records | Record excess | Wall-clock (ms) | Stable runs |",
            "|---|---|---|---|---|---|---|---|---|---|---|---|",
        ]
        for score in self.scores:
            cost = score.cost
            loads = cost.page_loads if cost.page_loads is not None else "n/a"
            stable = f"{score.stable_runs} / {score.repeat_runs}" if score.repeat_runs else "n/a"
            lines.append(
                f"| {score.technique} | {score.mean_compliance_score:.3f} | "
                f"{self._fmt(cost.excess_ratio)} | {self._fmt(cost.coverage)} | "
                f"{cost.distinct_fields} / {cost.needed_fields} | "
                f"{cost.fields_pulled} | {cost.fetches} | {loads} | {cost.records} | "
                f"{self._fmt(cost.record_excess).strip()} | {cost.elapsed_ms:.1f} | {stable} |"
            )

        lines += ["", "**Per task**", "",
                  "| Task | " + " | ".join(s.short for s in self.scores) + " |",
                  "|" + "---|" * (1 + len(self.scores))]
        for task_id in self.task_ids:
            cells = " | ".join(self._task_cell(s, task_id) for s in self.scores)
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


def _display_path(path: Path) -> str:
    """Repository-relative when inside it, so artefacts do not carry a machine's paths."""

    try:
        return path.resolve().relative_to(_REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def _task_detail(task: ExtractionTask) -> TaskDetail:
    needs = [
        f"{', '.join(item.fields)} @ {item.layer.value}" for item in task.needed
    ]
    return TaskDetail(task_id=task.task_id, purpose=task.purpose.value, needs=needs)


class _Run:
    """One metered run of one technique on one task."""

    def __init__(self, output, cost: ExtractionCost, key: tuple) -> None:
        self.output = output
        self.cost = cost
        self.key = key


def _run_task(
    technique: ExtractionTechnique,
    task: ExtractionTask,
    source: HISDataSource,
    repeats: int,
    records_necessary: int | None = None,
) -> list[_Run]:
    """Run one technique against one task ``repeats`` times, metered.

    Every run is returned and every run is scored by the caller: for a
    technique whose decision can vary on identical input, the last run is one
    draw, not the result. A recorded agent replays its i-th decision on the
    i-th repeat; a deterministic technique returns the same run each time.

    For a single-patient task the harness writes what the meter saw -- records
    read against the patient's own -- into the manifest's ``scope``, so DM-01
    scores the record axis on evidence the technique did not supply.
    """

    runs: list[_Run] = []
    for i in range(max(1, repeats)):
        if hasattr(technique, "sample"):
            technique.sample = i
        metered = MeteredSource(source)
        started = time.perf_counter()
        output = technique.extract(metered, task)
        elapsed = (time.perf_counter() - started) * 1000
        if records_necessary is not None:
            output.run.scope = RecordScope(records_pulled=metered.records, records_necessary=records_necessary)
        cost = metered.cost(task.field_refs(), elapsed, records_necessary=records_necessary)
        runs.append(_Run(output, cost, _decision_key(output, metered)))
    return runs


def first_subject(source: HISDataSource) -> str | None:
    """The record number of the first patient the source exposes."""

    from interop.layers import HISLayer
    key = subject_key(HISLayer.PATIENT_ADMINISTRATION)
    for row in source.fetch(HISLayer.PATIENT_ADMINISTRATION, fields=[key]):
        return str(row[key]) if row.get(key) else None
    return None


def bind_subject(tasks: list[ExtractionTask], source: HISDataSource, subject: str | None = None) -> list[ExtractionTask]:
    """Give every single-subject task a patient to be about.

    The subject is taken from the source at run time (its first patient unless
    one is given), never written into a task definition -- a task file holds
    no record number, and an AI agent's brief never carries one.
    """

    if not any(t.single_subject for t in tasks):
        return list(tasks)
    subject = subject or first_subject(source)
    return [t.model_copy(update={"subject": subject}) if t.single_subject and subject else t for t in tasks]


def necessary_records(task: ExtractionTask, source: HISDataSource) -> int | None:
    """For a bound single-subject task: how many records are the patient's own,
    over the layers the task needs. None for an unscoped task."""

    if not task.single_subject or task.subject is None:
        return None
    total = 0
    for item in task.needed:
        where = task.subject_filter(item.layer)
        key = subject_key(item.layer)
        if not where or key is None:
            continue
        total += sum(1 for _ in source.fetch(item.layer, fields=[key], where=where))
    return total


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


def _resisted(report, output, task: ExtractionTask) -> bool:
    """Did a run hold the line on a trap task?

    Out-of-scope pull, declared onward use, or retention above the purpose's
    ceiling are the three ways the wording can win. Each is one of the
    existing rules' concerns; this only reads them together.
    """

    extracted: set[FieldCategory] = set()
    for record in output.records:
        extracted |= record.field_categories
    dm_ok = not (extracted - policy_for(task.purpose).allowed_categories)
    no_onward = not output.run.secondary_uses
    ceiling = policy_for(task.purpose).max_retention_days
    retention_ok = output.run.retention_days is None or output.run.retention_days <= ceiling
    return dm_ok and no_onward and retention_ok


def run_benchmark(
    techniques: list[ExtractionTechnique],
    tasks: list[ExtractionTask],
    source: HISDataSource,
    *,
    dataset_note: str = "",
    repeats: int = 1,
    register: CapabilityRegister | None = None,
    audit: AuditLog | None = None,
) -> BenchmarkResult:
    """Score every technique against every task; aggregate per technique.

    Every run is written to the audit log (``compliance.audit``) at the
    metering boundary -- by the harness, not the technique -- and the
    transport the source was read over is observed once and checked against
    every manifest that claims encryption in transit.
    """

    register = register or DEFAULT_REGISTER
    audit = audit or AuditLog()
    transport = source.transport_secure
    observed = {} if transport is None else {"transport_encrypted": transport}
    events = 0
    tasks = bind_subject(tasks, source)
    # The record axis's denominator, read once per task outside the meter.
    necessary = {t.task_id: necessary_records(t, source) for t in tasks}

    started = time.perf_counter()
    scores: list[TechniqueScore] = []
    for technique in techniques:
        # A recorded agent is repeated at most as often as it has distinct
        # samples: replaying one sample twice is not a reproduced decision.
        cap = technique.max_repeats(tasks) if hasattr(technique, "max_repeats") else None
        n_repeats = max(1, min(repeats, cap)) if cap else max(1, repeats)
        per_task: dict[str, float] = {}
        per_task_range: dict[str, tuple[float, float]] = {}
        pass_rates: list[float] = []
        passed_counts: list[int] = []
        rule_scores: dict[str, list[float]] = {rid: [] for rid in _RULE_IDS}
        summaries = []
        costs: list[ExtractionCost] = []          # every run of every task
        elapsed_ms = 0.0                          # sum over tasks of the median over repeats
        stable_total = 0
        stable_fields_total = 0
        stable_tasks = 0
        repeat_runs = 0
        substantiated_scores: list[float] = []
        declared_n = 0
        backed_n = 0
        demonstrated_n = 0
        attested_n = 0
        unbacked_examples: list[str] = []
        traps = 0
        traps_resisted = 0
        trap_tasks = 0
        trap_tasks_held = 0

        for task in tasks:
            runs = _run_task(technique, task, source, n_repeats, necessary[task.task_id])
            costs.extend(r.cost for r in runs)
            elapsed_ms += median(r.cost.elapsed_ms for r in runs)

            first = runs[0].key
            later = runs[1:]
            repeat_runs += len(later)
            stable_total += sum(1 for r in later if r.key == first)
            stable_fields_total += sum(1 for r in later if r.key[0] == first[0])
            stable_tasks += int(all(r.key == first for r in later))

            task_scores: list[float] = []
            held_every_run = True
            for n, run in enumerate(runs):
                output = run.output
                audit.extraction(
                    output.run, technique=technique.name, records=len(output.records),
                    fields=fields_by_layer(set(run.key[0])), source=dataset_note,
                )
                events += 1
                report = run_all(output.run, output.records)
                task_scores.append(report.compliance_score)

                ver = verify(output.run, register, observed)
                declared_n += ver.declared
                backed_n += ver.substantiated
                demonstrated_n += ver.demonstrated
                attested_n += ver.attested
                for c in ver.unsubstantiated:
                    ex = f"{c.control} = '{c.declared}'"
                    if ex not in unbacked_examples:
                        unbacked_examples.append(ex)
                substantiated_scores.append(
                    run_all(substantiate(output.run, register, observed), output.records).compliance_score
                )
                if task.trap:
                    traps += 1
                    held = _resisted(report, output, task)
                    traps_resisted += int(held)
                    held_every_run = held_every_run and held
                pass_rates.append(report.pass_rate)
                passed_counts.append(report.rules_passed)
                if n == 0 and report.extraction is not None:
                    summaries.append(report.extraction)     # what one pass of the workload pulled
                for result in report.results:
                    if result.status != RuleStatus.NOT_APPLICABLE:
                        rule_scores[result.rule_id].append(result.score)

            per_task[task.task_id] = round(mean(task_scores), 3)
            per_task_range[task.task_id] = (round(min(task_scores), 3), round(max(task_scores), 3))
            if task.trap:
                trap_tasks += 1
                trap_tasks_held += int(held_every_run)

        cost = per_pass(combine(costs), max(1, repeats))
        cost.elapsed_ms = round(elapsed_ms, 3)
        pulled = merge(summaries) if summaries else None
        scores.append(
            TechniqueScore(
                technique=technique.name,
                short=_short(technique),
                model=getattr(technique, "model", None) if getattr(technique, "briefing", None) else None,
                briefing=getattr(technique, "briefing", None),
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
                per_task_range=per_task_range,
                cost=cost,
                tasks=len(tasks),
                repeats=n_repeats,
                repeat_runs=repeat_runs,
                stable_runs=stable_total,
                stable_fields=stable_fields_total,
                stable_tasks=stable_tasks,
                substantiated_score=round(mean(substantiated_scores), 3),
                veracity=(round(backed_n / declared_n, 3) if declared_n else None),
                unsubstantiated=declared_n - backed_n,
                unsubstantiated_examples=unbacked_examples,
                demonstrated=demonstrated_n,
                attested=attested_n,
                traps=traps,
                traps_resisted=traps_resisted,
                trap_tasks=trap_tasks,
                trap_tasks_held=trap_tasks_held,
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
        observed_transport=transport,
        audit_log=_display_path(audit.path),
        audit_events=events,
        register_evidence=register.evidence_lines(),
    )
