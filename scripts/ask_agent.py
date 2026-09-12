"""Demo: the staff-guidance assistant, in conversation.

    python scripts/ask_agent.py                 # scripted transcripts, four scenes
    python scripts/ask_agent.py --interactive   # pick a role and type

Four scenes, each showing one thing the assistant does:

  1. Reception registers a walk-in     -- recognition, slot filling, grounded steps
  2. Reception asks about a diagnosis  -- declined before any detail is asked for
  3. Administrator says "insurance"    -- ambiguous; the assistant asks, then proceeds
  4. Nurse asks two things             -- one permitted, one declined for a different rule

No LLM is involved anywhere. The assistant is a function registry, token-overlap
recognition, and templates -- and one call to ``compliance.roles.authorise`` before
it says anything. The same policy table that scores the scraping benchmark decides
what it may say to whom.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import _present as present
from agent import ReplyKind, Session, StaffRole, capabilities

SCENES: list[tuple[str, StaffRole, list[str]]] = [
    (
        "Scene 1 -- a walk-in at the front desk",
        StaffRole.RECEPTION,
        ["I've got a new patient here, first visit",
         "Priya Raman", "1988-03-14", "+91-9800000012"],
    ),
    (
        "Scene 2 -- the same receptionist, a moment later",
        StaffRole.RECEPTION,
        ["can you tell me what's wrong with her, what's the diagnosis"],
    ),
    (
        "Scene 3 -- the accounts office, being vague",
        StaffRole.ADMINISTRATOR,
        ["insurance", "2", "INV-2026-01187"],
    ),
    (
        "Scene 4 -- on the ward",
        StaffRole.NURSE,
        ["record obs for a patient", "MRN2867825", "128/82", "76", "37.1",
         "now raise the bill for that admission"],
    ),
]


def _print_reply(text: str) -> None:
    first, *rest = text.split("\n")
    print(f"  assistant : {first}")
    for line in rest:
        print(f"              {line}")


def play(title: str, role: StaffRole, lines: list[str]) -> None:
    print(present.rule())
    print(title)
    print(f"  role      : {role.value}")
    print()
    session = Session(role)
    for line in lines:
        print(f"  {role.value:<9} > {line}")
        reply = session.respond(line)
        _print_reply(reply.text)
        print()
        if reply.kind == ReplyKind.DECLINED:
            # Nothing was asked for before the refusal -- that is the point.
            print("  (declined before asking for any patient detail)")
            print()


def interactive() -> None:
    print(present.banner("Staff-guidance assistant -- interactive"))
    roles = list(StaffRole)
    for i, role in enumerate(roles, start=1):
        print(f"  {i}. {role.value}")
    choice = input("Which role are you? ").strip()
    role = roles[int(choice) - 1] if choice.isdigit() and 1 <= int(choice) <= len(roles) else roles[0]
    session = Session(role)
    print(f"\nYou are {role.value}. As {role.value} the assistant can walk you through:")
    for spec in capabilities(role):
        print(f"  - {spec.label}")
    print("\nType a request. Empty line or 'quit' to leave.\n")
    while True:
        try:
            line = input(f"{role.value}> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not line or line.lower() in {"quit", "exit"}:
            break
        _print_reply(session.respond(line).text)
        print()


def main() -> None:
    if "--interactive" in sys.argv[1:]:
        interactive()
        return

    print(present.banner("Staff-guidance assistant -- four scenes"))
    print(
        "A rule-based assistant for hospital staff. It recognises what the person\n"
        "wants from a fixed list of HIS functions, asks for the details it needs,\n"
        "and answers with numbered steps grounded in the HIS layer and the\n"
        "interoperability artefact each step touches. Before it says anything it\n"
        "asks the compliance policy whether this role may be told how."
    )
    for title, role, lines in SCENES:
        play(title, role, lines)

    print(present.rule())
    print(
        "Three roles, one policy. Reception was refused a diagnosis under purpose\n"
        "limitation (PL-01); the nurse was refused an invoice under the same rule for\n"
        "the opposite reason. Neither was asked for a single patient detail first.\n"
        "The refusals come from the table that scores the scraping benchmark -- the\n"
        "assistant does not carry a policy of its own."
    )


if __name__ == "__main__":
    main()
