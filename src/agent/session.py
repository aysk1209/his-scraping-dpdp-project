"""One conversation with one staff member: recognise, gate, collect, instruct.

A ``Session`` is a small state machine.

    IDLE        -- waiting for a request
    CHOOSING    -- the request matched several functions; asked which
    COLLECTING  -- gate passed; asking for the function's inputs one at a time

The order matters for compliance, and it is deliberate: **the gate runs before
any input is collected.** If the role may not be guided through a function, the
agent declines at once and never asks for the patient's name, MRN or anything
else it would then have no use for. Collecting details for a request you are
about to refuse is itself over-collection.

Recognition is token overlap between the request and each function's label and
synonyms -- nothing more. It cannot invent a function that does not exist, and
when two functions score alike it asks rather than guesses.
"""

from __future__ import annotations

import re
from enum import Enum

from pydantic import BaseModel, Field

from agent.functions import REGISTRY, FunctionSpec, capabilities
from agent.guidance import StaffGuidance, build_guidance
from compliance.roles import AccessDecision, StaffRole, authorise

_STOPWORDS = {
    "a", "an", "the", "i", "me", "my", "we", "our", "you", "to", "for", "of", "on", "in",
    "is", "it", "this", "that", "and", "or", "please", "can", "could", "would", "need",
    "want", "how", "do", "does", "up", "show", "get", "help", "with", "patient", "patients",
    "his", "her", "their", "some", "any", "there", "here", "am", "are", "be",
}

_WORD = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> set[str]:
    return {w for w in _WORD.findall(text.lower()) if w not in _STOPWORDS}


def _spec_tokens(spec: FunctionSpec) -> set[str]:
    bag = _tokens(spec.label) | _tokens(spec.id.replace("_", " "))
    for phrase in spec.synonyms:
        bag |= _tokens(phrase)
    return bag


_SPEC_TOKENS: dict[str, set[str]] = {spec.id: _spec_tokens(spec) for spec in REGISTRY}


def recognise(text: str) -> list[FunctionSpec]:
    """Functions the request could mean, best first. Empty if nothing overlaps.

    Scores are the count of shared tokens. Everything tied with the best score is
    returned so the caller can ask which was meant; a clear winner returns alone.
    """

    request = _tokens(text)
    if not request:
        return []
    scored = [
        (len(request & _SPEC_TOKENS[spec.id]), spec)
        for spec in REGISTRY
    ]
    best = max(score for score, _ in scored)
    if best == 0:
        return []
    return [spec for score, spec in scored if score == best]


class ReplyKind(str, Enum):
    ASK_CHOOSE = "ask_choose"       # several functions matched; which one?
    ASK_INPUT = "ask_input"         # gate passed; need a detail
    DECLINED = "declined"           # gate refused; rule cited
    GUIDANCE = "guidance"           # here are the steps
    UNRECOGNISED = "unrecognised"   # no function matched; here is what you can do


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
    """A conversation with one staff member in one role."""

    def __init__(self, role: StaffRole, navigation: dict[str, str] | None = None) -> None:
        self.role = role
        self.navigation = navigation          # artefact key -> page; from the Tier 2 map
        self._state = _State.IDLE
        self._options: list[FunctionSpec] = []
        self._spec: FunctionSpec | None = None
        self._inputs: dict[str, str] = {}

    # ------------------------------------------------------------------ public

    @property
    def state(self) -> str:
        return self._state.value

    def respond(self, text: str) -> Reply:
        text = text.strip()
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

    # ----------------------------------------------------------------- states

    def _start(self, text: str) -> Reply:
        matches = recognise(text)
        if not matches:
            return self._unrecognised()
        if len(matches) > 1:
            self._options = matches
            self._state = _State.CHOOSING
            lines = ["I can help with a few things that sound like that -- which one?"]
            for i, spec in enumerate(matches, start=1):
                lines.append(f"  {i}. {spec.label}")
            return Reply(kind=ReplyKind.ASK_CHOOSE, text="\n".join(lines),
                         options=[s.id for s in matches])
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
            lines = ["Sorry -- pick one by number:"]
            lines += [f"  {i}. {s.label}" for i, s in enumerate(self._options, start=1)]
            return Reply(kind=ReplyKind.ASK_CHOOSE, text="\n".join(lines),
                         options=[s.id for s in self._options])
        self._options = []
        return self._begin(chosen)

    def _begin(self, spec: FunctionSpec) -> Reply:
        # The gate, before a single detail is asked for.
        decision = authorise(self.role, spec.purpose, spec.artefacts, spec.categories)
        if not decision.allowed:
            self.reset()
            return Reply(kind=ReplyKind.DECLINED, text=self._decline_text(spec, decision),
                         decision=decision)
        self._spec = spec
        self._inputs = {}
        if not spec.inputs:
            return self._finish()
        self._state = _State.COLLECTING
        return self._ask_next(preface=f"Sure -- to {spec.label} I need a couple of details.")

    def _collect(self, text: str) -> Reply:
        assert self._spec is not None
        slot = self._spec.inputs[len(self._inputs)]
        if not text:
            return Reply(kind=ReplyKind.ASK_INPUT, text=f"{slot.prompt} (e.g. {slot.example})")
        self._inputs[slot.name] = text
        if len(self._inputs) == len(self._spec.inputs):
            return self._finish()
        return self._ask_next()

    def _ask_next(self, preface: str | None = None) -> Reply:
        assert self._spec is not None
        slot = self._spec.inputs[len(self._inputs)]
        text = f"{slot.prompt} (e.g. {slot.example})"
        if preface:
            text = f"{preface}\n{text}"
        return Reply(kind=ReplyKind.ASK_INPUT, text=text)

    def _finish(self) -> Reply:
        assert self._spec is not None
        guidance = build_guidance(self.role, self._spec, self._inputs, self.navigation)
        self.reset()
        return Reply(kind=ReplyKind.GUIDANCE, text=guidance.render(), guidance=guidance)

    # ---------------------------------------------------------------- helpers

    def _unrecognised(self) -> Reply:
        able = capabilities(self.role)
        lines = [f"I didn't recognise that. As {self.role.value} I can walk you through:"]
        lines += [f"  - {spec.label}" for spec in able]
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
