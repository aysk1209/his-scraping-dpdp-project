"""The agent's answer: numbered steps, grounded and annotated.

A ``StaffGuidance`` is what a staff member receives once the gate has passed and
the inputs are collected. Every step says where in the HIS it happens (layer and
artefact) and, where it matters, why the instruction is shaped the way it is
(the DPDP caution). The footer states the purpose the guidance was given for,
the lawful basis that purpose rests on, and the data categories the steps touch
-- so the answer carries its own compliance context rather than assuming it.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from compliance.models import FieldCategory, Purpose
from compliance.policy import policy_for
from compliance.roles import ARTEFACTS, StaffRole
from data_synthetic.catalogue import categories_for_fields
from interop.layers import HISLayer


class GuidanceStep(BaseModel):
    number: int
    text: str                       # slot values substituted
    layer: HISLayer
    artefact: str                   # key into ARTEFACTS
    artefact_name: str              # the standard's name for it, for the reader
    fields: list[str] = Field(default_factory=list)
    caution: str | None = None
    page: str | None = None         # filled from the navigation map when one exists


class StaffGuidance(BaseModel):
    role: StaffRole
    function_id: str
    label: str
    purpose: Purpose
    inputs: dict[str, str]
    steps: list[GuidanceStep]

    def categories_touched(self) -> set[FieldCategory]:
        touched: set[FieldCategory] = set()
        for step in self.steps:
            touched |= categories_for_fields(step.layer, step.fields)
        return touched

    def render(self) -> str:
        policy = policy_for(self.purpose)
        lines = [f"How to {self.label} -- for {self.role.value}", ""]
        for step in self.steps:
            where = f"[{step.layer.value} / {step.artefact_name}"
            if step.page:
                where += f" / {step.page}"
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
        return "\n".join(lines)

    def render_markdown(self) -> str:
        policy = policy_for(self.purpose)
        lines = [f"**How to {self.label}** — for `{self.role.value}`", ""]
        for step in self.steps:
            where = f"`{step.layer.value}` · {step.artefact_name}"
            if step.page:
                where += f" · `{step.page}`"
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
        return "\n".join(lines)


def build_guidance(
    role: StaffRole,
    spec,                                       # agent.functions.FunctionSpec
    inputs: dict[str, str],
    navigation: dict[str, str] | None = None,
) -> StaffGuidance:
    """Substitute collected inputs into the spec's step templates."""

    steps: list[GuidanceStep] = []
    for number, step in enumerate(spec.steps, start=1):
        steps.append(
            GuidanceStep(
                number=number,
                text=step.text.format(**inputs),
                layer=step.layer,
                artefact=step.artefact,
                artefact_name=ARTEFACTS[step.artefact].name,
                fields=list(step.fields),
                caution=step.caution,
                page=(navigation or {}).get(step.artefact, step.page),
            )
        )
    return StaffGuidance(
        role=role,
        function_id=spec.id,
        label=spec.label,
        purpose=spec.purpose,
        inputs=dict(inputs),
        steps=steps,
    )
