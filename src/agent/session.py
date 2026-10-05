"""One conversation with one staff member: recognise, gate, collect, instruct.

A ``Session`` is a small state machine.

    IDLE        -- waiting for a request
    CHOOSING    -- the request matched several functions; asked which
    COLLECTING  -- gate passed; asking for the function's inputs one at a time

The order matters for compliance, and it is deliberate: **the gate runs before
any input is collected.** If the role may not be guided through a function, the
agent declines at once and never asks for the patient's name, MRN or anything
else it would then have no use for. Collecting details for a request you are
about to refuse is itself over-collection. A detail already typed in the request
("check in MRN2867825") is read only *after* the gate passes, and only for the
function that was asked for.

Recognition is token overlap between the request and each function's label and
synonyms -- nothing more. It cannot invent a function that does not exist. When
two functions score alike it keeps the ones this role may perform (a nurse who
says "discharge" means the ward's checklist, an administrator the bed release)
and asks if that still leaves more than one; when it leaves none, it asks among
them all and the gate then declines with the rule.

Three words work at any time: ``help`` (what this role can be walked through),
``cancel`` (drop the request and whatever was typed for it) and ``what changed``
(the last HIS update, as it affects this role -- when the session was given one).
Answers with a recognisable shape (dates, record numbers, readings) are checked
and asked again if they do not fit.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from agent.functions import REGISTRY, FunctionSpec, InputSlot, capabilities, capabilities_by_group
from agent.guidance import StaffGuidance, build_guidance
from agent.ui import ScreenMap, normalise
from compliance.roles import AccessDecision, StaffRole, authorise

if TYPE_CHECKING:
    from agent.drift import UIChanges
    from extraction.tier2.navigation import NavigationMap

_STOPWORDS = {
    "a", "an", "the", "i", "me", "my", "we", "our", "you", "to", "for", "of", "on", "in",
    "is", "it", "this", "that", "and", "or", "please", "can", "could", "would", "need",
    "want", "how", "do", "does", "up", "show", "get", "help", "with", "patient", "patients",
    "his", "her", "their", "some", "any", "there", "here", "am", "are", "be",
}

_WORD = re.compile(r"[a-z0-9]+")

# Whole-message commands, compared after ``agent.ui.normalise``.
HELP_WORDS = {"help", "menu", "options", "what can you do", "what can i do", "what can you help with"}
CANCEL_WORDS = {"cancel", "stop", "never mind", "nevermind", "start over", "start again", "reset", "abort"}
CANCELLED_TEXT = "OK -- stopped. Nothing you typed for that request was kept."
NOTHING_TEXT = "Nothing is in progress -- ask me for something, or say \"help\"."
MISFIT_TEXT = "That doesn't look like what I need here."
CHANGES_WORDS = {"what changed", "what has changed", "what s new", "whats new", "what is new",
                 "changes", "update notes", "release notes", "what changed in the update"}


def _tokens(text: str) -> set[str]:
    return {w for w in _WORD.findall(text.lower()) if w not in _STOPWORDS}


def _spec_tokens(spec: FunctionSpec) -> set[str]:
    bag = _tokens(spec.label) | _tokens(spec.id.replace("_", " "))
    for phrase in spec.synonyms:
        bag |= _tokens(phrase)
    return bag


_SPEC_TOKENS: dict[str, set[str]] = {spec.id: _spec_tokens(spec) for spec in REGISTRY}

# Multi-word names said whole ("check in", "raise the bill") outweigh the single
# words they share with other functions -- stopwords and all.
_SPEC_PHRASES: dict[str, list[str]] = {
    spec.id: [p for p in (normalise(x) for x in [spec.label, *spec.synonyms]) if " " in p]
    for spec in REGISTRY
}
PHRASE_WEIGHT = 2


def recognise(text: str) -> list[FunctionSpec]:
    """Functions the request could mean, best first. Empty if nothing overlaps.

    A function scores one per token it shares with the request, plus
    ``PHRASE_WEIGHT`` per multi-word name of it the request contains whole.
    Everything tied with the best score is returned so the caller can ask which
    was meant; a clear winner returns alone.
    """

    request = _tokens(text)
    if not request:
        return []
    said = f" {normalise(text)} "
    scored = [
        (len(request & _SPEC_TOKENS[spec.id])
         + PHRASE_WEIGHT * sum(1 for p in _SPEC_PHRASES[spec.id] if f" {p} " in said), spec)
        for spec in REGISTRY
    ]
    best = max(score for score, _ in scored)
    if best == 0:
        return []
    return [spec for score, spec in scored if score == best]


def fits(slot: InputSlot, answer: str) -> bool:
    """Does an answer have the shape the slot needs? Slots without a shape take anything."""

    return slot.pattern is None or re.fullmatch(slot.pattern, answer.strip(), re.IGNORECASE) is not None


def found_in(slot: InputSlot, text: str) -> str | None:
    """The slot's value, if the request already carries it."""

    if slot.find is None:
        return None
    match = re.search(slot.find, text, re.IGNORECASE)
    return match.group(0) if match else None


class ReplyKind(str, Enum):
    ASK_CHOOSE = "ask_choose"       # several functions matched; which one?
    ASK_INPUT = "ask_input"         # gate passed; need a detail
    DECLINED = "declined"           # gate refused; rule cited
    GUIDANCE = "guidance"           # here are the steps
    UNRECOGNISED = "unrecognised"   # no function matched; here is what you can do
    HELP = "help"                   # asked what it can do
    CANCELLED = "cancelled"         # dropped the request
    CHANGES = "changes"             # the last HIS update, for this role


class Reply(BaseModel):
    kind: ReplyKind
    text: str
    options: list[str] = Field(default_factory=list)    # function ids, for ASK_CHOOSE
    decision: AccessDecision | None = None              # for DECLINED
    guidance: StaffGuidance | None = None               # for GUIDANCE


class _State(str, Enum):
    IDLE = "idle"
    CHOOSING = "choosing"
    COLLECTING = "collecting"


class Session:
    """A conversation with one staff member in one role.

    ``navigation`` is the portal as last crawled (a ``NavigationMap`` or a
    ``ScreenMap``); without it the steps are worded in the HIS model's own terms.
    ``changes`` is the comparison of the last two crawls, for "what changed".
    """

    def __init__(
        self,
        role: StaffRole,
        navigation: "NavigationMap | ScreenMap | None" = None,
        *,
        changes: "UIChanges | None" = None,
        control_aliases: dict[str, str] | None = None,
    ) -> None:
        self.role = role
        if navigation is None or isinstance(navigation, ScreenMap):
            self.screens = navigation or ScreenMap()
        else:
            self.screens = ScreenMap.from_navigation(navigation, control_aliases)
        self.changes = changes
        self._state = _State.IDLE
        self._options: list[FunctionSpec] = []
        self._spec: FunctionSpec | None = None
        self._inputs: dict[str, str] = {}
        self._request = ""

    # ------------------------------------------------------------------ public

    @property
    def state(self) -> str:
        return self._state.value

    @property
    def inputs(self) -> dict[str, str]:
        return dict(self._inputs)

    def respond(self, text: str) -> Reply:
        text = text.strip()
        command = normalise(text)
        if command in HELP_WORDS:
            return self._help()
        if command in CHANGES_WORDS:
            return self._what_changed()
        if command in CANCEL_WORDS:
            if self._state == _State.IDLE:
                return Reply(kind=ReplyKind.CANCELLED, text=NOTHING_TEXT)
            self.reset()
            return Reply(kind=ReplyKind.CANCELLED, text=CANCELLED_TEXT)
        if self._state == _State.CHOOSING:
            return self._choose(text)
        if self._state == _State.COLLECTING:
            return self._collect(text)
        return self._start(text)

    def reset(self) -> None:
        self._state = _State.IDLE
        self._options = []
        self._spec = None
        self._inputs = {}
        self._request = ""

    # ----------------------------------------------------------------- states

    def _start(self, text: str) -> Reply:
        matches = recognise(text)
        if not matches:
            return self._unrecognised()
        if len(matches) > 1:
            mine = [spec for spec in matches if spec.permitted_for(self.role)]
            if len(mine) == 1:
                self._request = text
                return self._begin(mine[0])
            matches = mine or matches
            self._request = text
            self._options = matches
            self._state = _State.CHOOSING
            lines = ["I can help with a few things that sound like that -- which one?"]
            for i, spec in enumerate(matches, start=1):
                lines.append(f"  {i}. {spec.label}")
            return Reply(kind=ReplyKind.ASK_CHOOSE, text="\n".join(lines),
                         options=[s.id for s in matches])
        self._request = text
        return self._begin(matches[0])

    def _choose(self, text: str) -> Reply:
        chosen: FunctionSpec | None = None
        if text.isdigit() and 1 <= int(text) <= len(self._options):
            chosen = self._options[int(text) - 1]
        else:
            for spec in self._options:
                if text.lower() in (spec.id, spec.label.lower()):
                    chosen = spec
                    break
            if chosen is None:
                narrowed = [s for s in recognise(text) if s in self._options]
                if len(narrowed) == 1:
                    chosen = narrowed[0]
        if chosen is None:
            return self._choose_again()
        self._options = []
        return self._begin(chosen)

    def _begin(self, spec: FunctionSpec) -> Reply:
        # The gate, before a single detail is asked for -- or read from the request.
        decision = authorise(self.role, spec.purpose, spec.artefacts, spec.categories)
        if not decision.allowed:
            self.reset()
            return Reply(kind=ReplyKind.DECLINED, text=self._decline_text(spec, decision),
                         decision=decision)
        self._spec = spec
        self._inputs = {}
        for slot in spec.inputs:
            value = found_in(slot, self._request)
            if value is not None and fits(slot, value):
                self._inputs[slot.name] = value
        taken = dict(self._inputs)
        if len(self._inputs) == len(spec.inputs):
            return self._finish()
        self._state = _State.COLLECTING
        preface = f"Sure -- to {spec.label} I need a couple of details."
        if taken:
            preface += "\n(From your message: " + ", ".join(f"{k} {v}" for k, v in taken.items()) + ".)"
        return self._ask_next(preface=preface)

    def _collect(self, text: str) -> Reply:
        slot = self._pending()
        if not text:
            return Reply(kind=ReplyKind.ASK_INPUT, text=f"{slot.prompt} (e.g. {slot.example})")
        if not fits(slot, text):
            return Reply(kind=ReplyKind.ASK_INPUT,
                         text=f"{MISFIT_TEXT}\n{slot.prompt} (e.g. {slot.example})")
        self._inputs[slot.name] = text
        if self._spec is not None and len(self._inputs) == len(self._spec.inputs):
            return self._finish()
        return self._ask_next()

    def _pending(self) -> InputSlot:
        assert self._spec is not None
        return next(s for s in self._spec.inputs if s.name not in self._inputs)

    def _ask_next(self, preface: str | None = None) -> Reply:
        slot = self._pending()
        text = f"{slot.prompt} (e.g. {slot.example})"
        if preface:
            text = f"{preface}\n{text}"
        return Reply(kind=ReplyKind.ASK_INPUT, text=text)

    def _finish(self) -> Reply:
        assert self._spec is not None
        guidance = build_guidance(self.role, self._spec, self._inputs, self.screens)
        self.reset()
        return Reply(kind=ReplyKind.GUIDANCE, text=guidance.render(), guidance=guidance)

    # ---------------------------------------------------------------- helpers

    def _choose_again(self) -> Reply:
        lines = ["Sorry -- pick one by number:"]
        lines += [f"  {i}. {s.label}" for i, s in enumerate(self._options, start=1)]
        return Reply(kind=ReplyKind.ASK_CHOOSE, text="\n".join(lines),
                     options=[s.id for s in self._options])

    def menu(self) -> list[str]:
        """What this role can be walked through, grouped as the menu shows it."""

        lines: list[str] = []
        for group, specs in capabilities_by_group(self.role):
            lines.append(f"  {group}:")
            lines += [f"  - {spec.label}" for spec in specs]
        return lines

    def _help(self) -> Reply:
        if self._state == _State.COLLECTING:
            assert self._spec is not None
            slot = self._pending()
            return Reply(kind=ReplyKind.ASK_INPUT,
                         text=f"(Say \"cancel\" to stop.) To {self._spec.label} I still need this:\n"
                              f"{slot.prompt} (e.g. {slot.example})")
        if self._state == _State.CHOOSING:
            return self._choose_again()
        lines = [f"As {self.role.value} I can walk you through:", *self.menu(),
                 "Say \"cancel\" at any point to stop."]
        return Reply(kind=ReplyKind.HELP, text="\n".join(lines))

    def _what_changed(self) -> Reply:
        if self.changes is None:
            text = ("I have no record of a change to the HIS since its screens were last mapped"
                    + (f" ({self.screens.discovered})." if self.screens.discovered else "."))
        else:
            text = self.changes.for_role(self.role)
        return Reply(kind=ReplyKind.CHANGES, text=text)

    def _unrecognised(self) -> Reply:
        lines = [f"I didn't recognise that. As {self.role.value} I can walk you through:", *self.menu()]
        return Reply(kind=ReplyKind.UNRECOGNISED, text="\n".join(lines))

    def _decline_text(self, spec: FunctionSpec, decision: AccessDecision) -> str:
        who = [r.value for r in StaffRole if r != self.role and spec.permitted_for(r)]
        lines = [
            f"I can't walk you through how to {spec.label} as {self.role.value}.",
            f"  {decision.reasons[0]}",
            f"  [{decision.rule_id} -- {decision.provision}]",
        ]
        if who:
            lines.append(f"  This is something {' or '.join(who)} can do; please hand it to them.")
        else:
            lines.append("  No role in this hospital is set up to do this through the assistant.")
        return "\n".join(lines)


__all__ = ["Session", "Reply", "ReplyKind", "recognise", "fits", "found_in", "capabilities"]
