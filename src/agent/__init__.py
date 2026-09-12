"""Rule-based staff-guidance agent (build step 6).

Recognises a pre-defined HIS function from what a staff member types, asks for
the inputs that function needs, and replies with numbered operating instructions.
Deterministic: a function registry, token-overlap recognition, slot filling, and
templated steps. No LLM, no model, no training, no network.

Its one research-relevant property: before it says anything it calls
``compliance.roles.authorise`` -- the same policy table that scores the
extraction benchmark decides what may be said to whom. A receptionist asking for
a diagnosis is declined with the rule cited. See ``PLAN.md`` section 2.

    from agent import Session, StaffRole
    session = Session(StaffRole.RECEPTION)
    reply = session.respond("I need to register a new patient")
"""

from __future__ import annotations

from agent.functions import REGISTRY, FunctionSpec, InputSlot, Step, capabilities
from agent.guidance import StaffGuidance, GuidanceStep
from agent.session import Reply, ReplyKind, Session
from compliance.roles import StaffRole

__all__ = [
    "REGISTRY", "FunctionSpec", "InputSlot", "Step", "capabilities",
    "StaffGuidance", "GuidanceStep",
    "Reply", "ReplyKind", "Session",
    "StaffRole",
]
