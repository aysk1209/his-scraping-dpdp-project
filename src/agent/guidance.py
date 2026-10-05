"""The agent's answer: numbered steps, grounded, placed and annotated.

A ``StaffGuidance`` is what a staff member receives once the gate has passed and
the inputs are collected. Every step says where in the HIS it happens -- the
layer and artefact it touches and, when the portal has been crawled, the module,
path and screen as they are *today* -- and, where it matters, why the instruction
is shaped the way it is (the DPDP caution). A step the current HIS cannot be
matched to is **withheld** with its reason rather than given in out-of-date words.
The footer states the purpose the guidance was given for, the lawful basis that
purpose rests on, and the data categories the steps touch -- so the answer
carries its own compliance context rather than assuming it.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from compliance.models import FieldCategory, Purpose
from compliance.policy import policy_for
from compliance.roles import ARTEFACTS, StaffRole
from data_synthetic.catalogue import categories_for_fields
from agent.ui import Placement, ScreenMap, humanise
from interop.layers import HISLayer

WITHHELD_HEAD = "  Some steps are withheld: the HIS has changed in a way I cannot match yet. The rest is current."


class GuidanceStep(BaseModel):
    number: int
    text: str                       # slot values and screen words substituted
    layer: HISLayer
    artefact: str                   # key into ARTEFACTS
    artefact_name: str              # the standard's name for it, for the reader
    fields: list[str] = Field(default_factory=list)
    caution: str | None = None
    page: str | None = None         # the module's path, from the navigation map
    where: str | None = None        # "Front Office, /app/front-office/, record page"
    withheld: str | None = None     # why this step could not be placed, when it could not


class StaffGuidance(BaseModel):
    role: StaffRole
    function_id: str
    label: str
    purpose: Purpose
    inputs: dict[str, str]
    steps: list[GuidanceStep]
    screens_as_of: str | None = None    # the crawl the screen words come from

    def categories_touched(self) -> set[FieldCategory]:
        touched: set[FieldCategory] = set()
        for step in self.steps:
            touched |= categories_for_fields(step.layer, step.fields)
        return touched

    def withheld(self) -> list[GuidanceStep]:
        return [s for s in self.steps if s.withheld]

    def render(self) -> str:
        policy = policy_for(self.purpose)
        lines = [f"How to {self.label} -- for {self.role.value}", ""]
        if self.withheld():
            lines += [WITHHELD_HEAD, ""]
        for step in self.steps:
            where = f"[{step.layer.value} / {step.artefact_name}"
            if step.where:
                where += f" / {step.where}"
            where += "]"
            lines.append(f"  {step.number}. {step.text}")
            lines.append(f"     {where}")
            if step.caution:
                lines.append(f"     note: {step.caution}")
        touched = ", ".join(sorted(c.value for c in self.categories_touched())) or "none"
        lines += [
            "",
            f"  purpose      : {self.purpose.value} ({policy.legitimate_use_note})",
            f"  data touched : {touched}",
            f"  retain       : no longer than {policy.max_retention_days} days for this purpose",
        ]
        if self.screens_as_of:
            lines.append(f"  screens      : as found on {self.screens_as_of}")
        return "\n".join(lines)

    def render_markdown(self) -> str:
        policy = policy_for(self.purpose)
        lines = [f"**How to {self.label}** — for `{self.role.value}`", ""]
        if self.withheld():
            lines += [f"> {WITHHELD_HEAD.strip()}", ""]
        for step in self.steps:
            where = f"`{step.layer.value}` · {step.artefact_name}"
            if step.where:
                where += f" · {step.where}"
            lines.append(f"{step.number}. {step.text}  ")
            lines.append(f"   <sub>{where}</sub>")
            if step.caution:
                lines.append(f"   > {step.caution}")
        touched = ", ".join(f"`{c.value}`" for c in sorted(self.categories_touched(), key=lambda c: c.value)) or "none"
        lines += [
            "",
            f"*Purpose:* `{self.purpose.value}` — {policy.legitimate_use_note}.  ",
            f"*Data touched:* {touched}.  ",
            f"*Retention:* no longer than {policy.max_retention_days} days for this purpose.",
        ]
        if self.screens_as_of:
            lines.append(f"*Screens:* as found on {self.screens_as_of}.")
        return "\n".join(lines)


class _Labels:
    """``{label.full_name}`` in a step template: the column as headed on screen."""

    def __init__(self, labels: dict[str, str]) -> None:
        self._labels = labels

    def __getattr__(self, name: str) -> str:
        return self._labels.get(name, humanise(name))


def place_steps(spec, screens: ScreenMap) -> list[Placement | None]:
    """Where each step of ``spec`` happens in ``screens``; None for an off-screen step."""

    placements: list[Placement | None] = []
    previous: Placement | None = None
    for step in spec.steps:
        if step.offscreen:
            placements.append(None)
            continue
        placement = screens.place(step.layer, step.fields, step.action,
                                  previous=previous, continues=step.continues)
        placements.append(placement)
        previous = placement
    return placements


def withheld_text(reason: str) -> str:
    return (f"(withheld) I can't place this step on the HIS as it is now: {reason}. "
            f"Ask your HIS super-user before going on.")


def build_guidance(
    role: StaffRole,
    spec,                                       # agent.functions.FunctionSpec
    inputs: dict[str, str],
    screens: ScreenMap | None = None,
) -> StaffGuidance:
    """Substitute the collected inputs and today's screen words into the spec's steps."""

    screens = screens or ScreenMap()
    steps: list[GuidanceStep] = []
    for number, (step, placement) in enumerate(zip(spec.steps, place_steps(spec, screens)), start=1):
        where = page = withheld = None
        if placement is None:
            text = step.text.format(**inputs, label=_Labels({}))
        elif placement.withheld:
            withheld = placement.withheld
            text = withheld_text(withheld)
        else:
            text = step.text.format(**inputs, module=placement.module, button=placement.button,
                                    label=_Labels(placement.labels))
            if placement.elsewhere:
                text += " (" + "; ".join(placement.elsewhere) + ".)"
            if screens.crawled:
                where, page = placement.where(), placement.path
        steps.append(
            GuidanceStep(
                number=number,
                text=text,
                layer=step.layer,
                artefact=step.artefact,
                artefact_name=ARTEFACTS[step.artefact].name,
                fields=list(step.fields),
                caution=None if withheld else step.caution,
                page=page,
                where=where,
                withheld=withheld,
            )
        )
    return StaffGuidance(
        role=role,
        function_id=spec.id,
        label=spec.label,
        purpose=spec.purpose,
        inputs=dict(inputs),
        steps=steps,
        screens_as_of=screens.discovered,
    )
