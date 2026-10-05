"""What a HIS update changed, and what that does to the staff instructions.

Two crawls of the same portal -- before and after a release -- are compared the
way a person who knew the old screens would compare them:

- **modules** are matched by what they hold, not by name: the module whose
  fields overlap most is the same module, renamed or moved; one old module whose
  fields now sit in two is a split;
- **fields**: moved between modules, moved off the list onto the record page,
  relabelled, gone, new;
- **buttons**: renamed, moved, gone, new;
- **what it cannot understand** -- a header the alias file does not map, a button
  outside the vocabulary -- is listed with a *proposal* where the update makes one
  obvious (one field vanished from that module and one unknown header appeared
  in it), for a person to confirm. Never adopted silently.

Then every function in the registry is rendered against both crawls. It is
*unchanged*, *re-worded* (the instructions now use the new names and places --
the agent did that by itself), or has a step *withheld* until a proposal is
confirmed. ``UIChanges.for_role`` is what a member of staff hears when they ask
"what changed?": only what touches their own tasks.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from agent.functions import REGISTRY, FunctionSpec, capabilities
from agent.guidance import build_guidance
from agent.ui import ACTIONS, LAYER_NAMES, ModuleView, ScreenMap, humanise, normalise
from compliance.roles import StaffRole
from data_synthetic.catalogue import FIELD_CATALOGUE

ChangeKind = Literal["module", "field", "button", "unmapped"]
_HEADINGS: dict[ChangeKind, str] = {
    "module": "Modules", "field": "Fields", "button": "Buttons",
    "unmapped": "Not understood -- needs a person to confirm",
}


class Change(BaseModel):
    kind: ChangeKind
    text: str
    modules: set[str] = Field(default_factory=set)       # titles, before and after
    fields: set[str] = Field(default_factory=set)
    actions: set[str] = Field(default_factory=set)


class TaskImpact(BaseModel):
    function_id: str
    label: str
    status: Literal["unchanged", "re-worded", "withheld"]
    reasons: list[str] = Field(default_factory=list)      # why steps are withheld
    modules: set[str] = Field(default_factory=set)        # where its steps happen, before and after


class UIChanges(BaseModel):
    before: str | None = None                             # crawl dates
    after: str | None = None
    changes: list[Change]
    field_proposals: dict[str, str] = Field(default_factory=dict)     # header -> field
    control_proposals: dict[str, str] = Field(default_factory=dict)   # button label -> action id
    impact: list[TaskImpact]

    # ----------------------------------------------------------------- views

    def by_status(self, functions: list[FunctionSpec] | None = None) -> dict[str, list[TaskImpact]]:
        ids = {f.id for f in functions} if functions is not None else None
        out: dict[str, list[TaskImpact]] = {"unchanged": [], "re-worded": [], "withheld": []}
        for t in self.impact:
            if ids is None or t.function_id in ids:
                out[t.status].append(t)
        return out

    def relevant(self, role: StaffRole) -> list[Change]:
        """Changes that touch a module, field or button this role's tasks use."""

        mine = capabilities(role)
        ids = {s.id for s in mine}
        fields = {f for s in mine for st in s.steps for f in st.fields}
        actions = {st.action for s in mine for st in s.steps if st.action}
        modules = {m for t in self.impact if t.function_id in ids for m in t.modules}
        return [c for c in self.changes
                if c.fields & fields or c.actions & actions
                or (not c.fields and not c.actions and c.modules & modules)]

    def for_role(self, role: StaffRole) -> str:
        """What a member of staff hears when they ask "what changed?"."""

        when = f" (screens of {self.after}, compared with {self.before})" if self.after else ""
        mine = self.relevant(role)
        statuses = self.by_status(capabilities(role))
        lines = [f"What changed in the HIS{when}, as it affects {role.value}:"]
        lines += [f"  - {c.text}" for c in mine] or ["  - nothing on the screens your tasks use."]
        n = {k: len(v) for k, v in statuses.items()}
        lines.append(f"  Your tasks: {n['re-worded']} re-worded to match, {n['unchanged']} unchanged, "
                     f"{n['withheld']} with a step withheld.")
        for t in statuses["withheld"]:
            lines.append(f"  - {t.label}: {'; '.join(t.reasons)}")
        if statuses["withheld"]:
            lines.append("  Withheld steps come back once your HIS super-user confirms what the new screens mean.")
        return "\n".join(lines)

    def render(self) -> str:
        lines = [f"HIS update check -- screens of {self.after or '?'} against {self.before or '?'}", ""]
        for kind, heading in _HEADINGS.items():
            items = [c for c in self.changes if c.kind == kind]
            if items:
                lines.append(f"  {heading}")
                lines += [f"  - {c.text}" for c in items]
                lines.append("")
        lines += self._impact_lines()
        return "\n".join(lines)

    def _impact_lines(self) -> list[str]:
        total = self.by_status()
        lines = [
            f"  Effect on the assistant's {len(self.impact)} tasks: {len(total['unchanged'])} unchanged, "
            f"{len(total['re-worded'])} re-worded by the assistant itself, "
            f"{len(total['withheld'])} with a step withheld",
            "",
            f"  {'role':<14} {'tasks':>5} {'unchanged':>10} {'re-worded':>10} {'withheld':>9}",
        ]
        for role in StaffRole:
            s = self.by_status(capabilities(role))
            count = sum(len(v) for v in s.values())
            lines.append(f"  {role.value:<14} {count:>5} {len(s['unchanged']):>10} "
                         f"{len(s['re-worded']):>10} {len(s['withheld']):>9}")
        if total["withheld"]:
            lines += ["", "  Withheld until confirmed:"]
            lines += [f"  - {t.label}: {'; '.join(t.reasons)}" for t in total["withheld"]]
        if self.field_proposals or self.control_proposals:
            lines += ["", "  To confirm (a person decides; nothing here is adopted by itself):"]
            lines += [f'  - field alias   "{h}" = {f}' for h, f in self.field_proposals.items()]
            lines += [f'  - button alias  "{b}" = {a}' for b, a in self.control_proposals.items()]
        return lines

    def render_markdown(self) -> str:
        lines = [f"### HIS update check — screens of {self.after or '?'} against {self.before or '?'}", ""]
        for kind, heading in _HEADINGS.items():
            items = [c for c in self.changes if c.kind == kind]
            if items:
                lines += [f"**{heading}**", ""] + [f"- {c.text}" for c in items] + [""]
        lines += ["| Role | Tasks | Unchanged | Re-worded | Withheld |", "|---|---|---|---|---|"]
        for role in StaffRole:
            s = self.by_status(capabilities(role))
            lines.append(f"| {role.value} | {sum(len(v) for v in s.values())} | {len(s['unchanged'])} | "
                         f"{len(s['re-worded'])} | {len(s['withheld'])} |")
        withheld = self.by_status()["withheld"]
        if withheld:
            lines += ["", "**Withheld until confirmed**", ""]
            lines += [f"- {t.label}: {'; '.join(t.reasons)}" for t in withheld]
        return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- #
# The comparison
# --------------------------------------------------------------------------- #

def _known(m: ModuleView) -> set[str]:
    catalogue = FIELD_CATALOGUE.get(m.layer, {})
    return {f for f in m.fields() if f in catalogue}


def _successors(before: ScreenMap, after: ScreenMap) -> tuple[dict[str, list[ModuleView]], dict[str, ModuleView]]:
    """Old title -> the new modules that hold its content; new title -> where it came from."""

    succ: dict[str, list[ModuleView]] = {o.title: [] for o in before.modules or []}
    origin: dict[str, ModuleView] = {}
    for n in after.modules or []:
        scored = []
        for o in before.modules or []:
            if o.layer != n.layer:
                continue
            a, b = _known(o), _known(n)
            overlap = len(a & b) / len(a | b) if a | b else 0.0
            scored.append((overlap, o.title == n.title, o))
        if scored:
            overlap, _, o = max(scored, key=lambda t: (t[0], t[1]))
            if overlap > 0:
                succ[o.title].append(n)
                origin[n.title] = o
    return succ, origin


def _screen(m: ModuleView, field: str) -> str:
    return "list page" if field in m.list_fields else "record page"


def compare(before: ScreenMap, after: ScreenMap) -> UIChanges:
    """Everything a release changed between two crawls, and what it does to every task."""

    if not (before.crawled and after.crawled):
        raise ValueError("compare() needs two crawled screen maps")
    succ, origin = _successors(before, after)

    def now_called(old: ModuleView) -> str:
        news = succ[old.title]
        return news[0].title if len(news) == 1 else old.title

    changes: list[Change] = []

    def add(kind: ChangeKind, text: str, **tags) -> None:
        for c in changes:
            if c.kind == kind and c.text.lower() == text.lower():                  # the same words from another layer
                for key, value in tags.items():
                    getattr(c, key).update(value)
                return
        changes.append(Change(kind=kind, text=text[:1].upper() + text[1:], **tags))

    # -- modules --------------------------------------------------------------
    for o in before.modules or []:
        news = succ[o.title]
        if not news:
            add("module", f"{o.title} ({o.path}) is gone; no module now holds what it held.", modules={o.title})
        elif len(news) > 1:
            parts = " and ".join(f"{n.title} ({n.path})" for n in news)
            add("module", f"{o.title} is now split: {parts}.", modules={o.title, *(n.title for n in news)})
        else:
            n = news[0]
            if n.title != o.title and n.path != o.path:
                add("module", f"{o.title} is now {n.title} ({o.path} -> {n.path}).", modules={o.title, n.title})
            elif n.title != o.title:
                add("module", f"{o.title} is now called {n.title}.", modules={o.title, n.title})
            elif n.path != o.path:
                add("module", f"{o.title} has moved: {o.path} -> {n.path}.", modules={o.title})
    for n in after.modules or []:
        if n.title not in origin:
            add("module", f"New module: {n.title} ({n.path}).", modules={n.title})

    # -- fields ---------------------------------------------------------------
    vanished: dict[str, set[str]] = {}                              # layer value -> fields gone
    for layer, catalogue in FIELD_CATALOGUE.items():
        olds, news = before.in_layer(layer), after.in_layer(layer)
        if not olds or not news:
            continue
        had = {f for m in olds for f in _known(m)}
        has = {f for m in news for f in _known(m)}
        vanished[layer.value] = had - has
        for f in catalogue:
            if f not in had | has:
                continue
            old_label = next(m.label(f) for m in olds if f in m.fields()) if f in had else None
            new_label = next(m.label(f) for m in news if f in m.fields()) if f in has else None
            if f in had and f not in has:
                add("field", f"{old_label} is no longer found on any {LAYER_NAMES[layer]} page.",
                    fields={f}, modules={m.title for m in olds if f in m.fields()})
                continue
            if f in has and f not in had:
                where = "; ".join(f"{m.title}, {_screen(m, f)}" for m in news if f in m.fields())
                add("field", f"{new_label} now appears on {where}.", fields={f})
                continue
            if normalise(old_label) != normalise(new_label):
                add("field", f'The "{old_label}" column is now headed "{new_label}".', fields={f})
            if f == "mrn":                                          # on every module; its moves are the modules'
                continue
            was = sorted({(now_called(m), _screen(m, f)) for m in olds if f in m.fields()})
            now = sorted({(m.title, _screen(m, f)) for m in news if f in m.fields()})
            if was != now:
                text = lambda places: "; ".join(f"{t}, {s}" for t, s in places)   # noqa: E731
                if [t for t, _ in was] == [t for t, _ in now]:
                    add("field", f"{new_label} is now on the {now[0][1]} of {now[0][0]} (was the {was[0][1]}).",
                        fields={f}, modules={t for t, _ in now})
                else:
                    add("field", f"{new_label} moved: {text(was)} -> {text(now)}.",
                        fields={f}, modules={t for t, _ in [*was, *now]})

    # -- buttons --------------------------------------------------------------
    def first_place(screens: ScreenMap, action: str) -> tuple[ModuleView, str, str] | None:
        for m in screens.modules or []:
            if action in m.list_actions:
                return m, "list page", m.list_actions[action]
            if action in m.record_actions:
                return m, "record page", m.record_actions[action]
        return None

    gone_actions: dict[str, tuple[ModuleView, str]] = {}
    for action in ACTIONS:
        was, now = first_place(before, action), first_place(after, action)
        if was is None and now is None:
            continue
        if now is None:
            m, screen, label = was
            gone_actions[action] = (m, screen)
            add("button", f'"{label}" ({m.title}, {screen}) is gone: no button for it was recognised.',
                actions={action}, modules={m.title})
            continue
        if was is None:
            m, screen, label = now
            add("button", f'New button "{label}" on {m.title}, {screen}.', actions={action}, modules={m.title})
            continue
        (om, oscreen, olabel), (nm, nscreen, nlabel) = was, now
        moved = (now_called(om), oscreen) != (nm.title, nscreen)
        if olabel != nlabel and moved:
            add("button", f'"{olabel}" is now "{nlabel}", on {nm.title}, {nscreen}.',
                actions={action}, modules={om.title, nm.title})
        elif olabel != nlabel:
            add("button", f'"{olabel}" is now "{nlabel}" ({nm.title}, {nscreen}).', actions={action})
        elif moved:
            add("button", f'"{nlabel}" moved to {nm.title}, {nscreen}.',
                actions={action}, modules={om.title, nm.title})

    # -- what it cannot understand, and what it proposes ------------------------
    field_proposals: dict[str, str] = {}
    control_proposals: dict[str, str] = {}
    for n in after.modules or []:
        old = origin.get(n.title)
        for screen, header in n.unknown_headers:
            if old is not None and header in {h for _, h in old.unknown_headers}:
                continue
            gone = sorted(f for f in vanished.get(n.layer.value, set()) if old is None or f in old.fields())
            text = f'A column headed "{header}" on {n.title} ({screen}) is not in the field aliases'
            if len(gone) == 1:
                field_proposals[header] = gone[0]
                text += (f" -- most likely {humanise(gone[0])}, which disappeared in the same update. "
                         f'Confirm "{header}" = {gone[0]} to restore it.')
                add("unmapped", text, fields={gone[0]}, modules={n.title})
            else:
                add("unmapped", text + ".", modules={n.title})
        for screen, label in n.unknown_controls:
            if old is not None and label in {c for _, c in old.unknown_controls}:
                continue
            gone = sorted(a for a, (m, s) in gone_actions.items()
                          if s == screen and (m.title == n.title or n in succ.get(m.title, [])))
            text = f'A button "{label}" on {n.title} ({screen}) is not one I recognise'
            if len(gone) == 1:
                control_proposals[label] = gone[0]
                text += (f' -- most likely "{ACTIONS[gone[0]].label}", which disappeared in the same '
                         f'update. Confirm "{label}" = {gone[0]} to restore it.')
                add("unmapped", text, actions={gone[0]}, modules={n.title})
            else:
                add("unmapped", text + ".", modules={n.title})

    return UIChanges(
        before=before.discovered, after=after.discovered, changes=changes,
        field_proposals=field_proposals, control_proposals=control_proposals,
        impact=[_impact(spec, before, after) for spec in REGISTRY],
    )


def _impact(spec: FunctionSpec, before: ScreenMap, after: ScreenMap) -> TaskImpact:
    placeholders = {slot.name: "{" + slot.name + "}" for slot in spec.inputs}
    role = next((r for r in StaffRole if spec.permitted_for(r)), StaffRole.RECEPTION)
    was = build_guidance(role, spec, placeholders, before)
    now = build_guidance(role, spec, placeholders, after)
    modules = {s.where.split(", ")[0] for s in [*was.steps, *now.steps] if s.where}
    if now.withheld():
        return TaskImpact(function_id=spec.id, label=spec.label, status="withheld",
                          reasons=list(dict.fromkeys(s.withheld for s in now.withheld())), modules=modules)
    same = [(s.text, s.where) for s in was.steps] == [(s.text, s.where) for s in now.steps]
    return TaskImpact(function_id=spec.id, label=spec.label,
                      status="unchanged" if same else "re-worded", modules=modules)


__all__ = ["Change", "TaskImpact", "UIChanges", "compare"]
