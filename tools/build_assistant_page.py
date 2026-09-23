"""Build the interactive assistant page: pick a role, type a request, watch the gate.

    python tools/build_assistant_page.py

The staff assistant (``src/agent/``) has no model in it: it recognises one of a
fixed set of functions by token overlap, checks the role's purpose *before*
asking for a single detail, then fills templated steps and places each on the
page the portal crawler found (``docs/benchmark_results/navigation-map.json``).
That makes it small enough to run in a browser, so the page does -- the panel
can type anything a receptionist or a nurse would say.

A copy of logic is a second place for it to be wrong, so the page does not ask
to be trusted: the builder runs the real Python ``Session`` on every scripted
conversation (every role x every function, every synonym, ties and their
follow-ups, empty answers, requests it cannot recognise) and embeds the
transcripts. On load the page replays all of them through its own engine and
compares every reply, character for character. If one differs, typing is
switched off and only the recorded Python conversations are offered.

Nothing personal is on the page: the inputs are the registry's own examples.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from agent.functions import REGISTRY                                      # noqa: E402
from agent.guidance import build_guidance                                 # noqa: E402
from agent.session import _SPEC_TOKENS, _STOPWORDS, ReplyKind, Session, recognise  # noqa: E402
from compliance.policy import PURPOSE_POLICY, policy_for                  # noqa: E402
from compliance.roles import ARTEFACTS, ROLE_POLICY, StaffRole, authorise  # noqa: E402
from extraction.tier2.navigation import NavigationMap                     # noqa: E402
from tools.page_kit import REVIEW_DIR, render, write                      # noqa: E402

TEMPLATE = ROOT / "tools" / "assistant_page.html"
DEFAULT_OUT = REVIEW_DIR / "assistant.html"
NAV_MAP = ROOT / "docs" / "benchmark_results" / "navigation-map.json"

# Requests a member of staff might type that are not any function's own wording.
PROBES = [
    "hello", "book me a taxi", "tell me a joke", "what is the weather", "what is the patient's diagnosis", "raise the bill", "register a new patient",
    "look up the diagnosis", "record", "check", "patient", "new", "bill the patient for the scan",
    "who is on the ward", "the patient has arrived", "give me the medication list", "order a blood test",
    "is the insurance valid", "discharge", "assign a bed on ward 3", "reconcile", "what do you do",
]
# The four scenes the live pipeline shows (scripts/run_pipeline.py, stage 6).
SCENES = [
    ("reception", ["register a new patient", "Priya Raman", "1988-03-14", "+91-9800000012"]),
    ("nurse", ["look up the diagnosis", "MRN2867825"]),
    ("administrator", ["raise the bill", "MRN2867825", "ENC-20260912-07"]),
    ("reception", ["what is the patient's diagnosis"]),
]


def _reply(r, fn: str | None) -> dict:
    return {"kind": r.kind.value, "fn": fn, "text": r.text}


def _play(role: StaffRole, turns: list[str], nav: dict) -> dict:
    """A fixed script through the real Session; each reply tagged with the function in play."""

    session, replies, fn = Session(role, navigation=nav), [], None
    for turn in turns:
        idle = session.state == "idle"
        reply = session.respond(turn)
        if idle:
            matches = recognise(turn)
            fn = matches[0].id if len(matches) == 1 else None
        if reply.kind == ReplyKind.ASK_INPUT and fn is None:
            fn = next(x.id for x in REGISTRY if reply.text.startswith(f"Sure -- to {x.label} "))
        if reply.kind == ReplyKind.GUIDANCE:
            fn = reply.guidance.function_id
        replies.append(_reply(reply, fn if reply.kind not in (ReplyKind.ASK_CHOOSE, ReplyKind.UNRECOGNISED) else None))
    return {"role": role.value, "turns": list(turns), "replies": replies}


def _conversation(role: StaffRole, first: str, nav: dict, *, pick: int | None = None,
                  empty_once: bool = False, bad_choice: bool = False) -> dict:
    """Drive the real Session: answer a tie with ``pick``, every question with its example."""

    session = Session(role, navigation=nav)
    turns, replies = [first], [session.respond(first)]
    matches = recognise(first)
    spec = matches[0] if len(matches) == 1 else None
    for _ in range(12):
        last = replies[-1]
        if last.kind == ReplyKind.ASK_CHOOSE:
            if bad_choice:
                answer, bad_choice = "banana", False
            else:
                answer = str(pick or 1)
                spec = next(s for s in REGISTRY if s.id == last.options[int(answer) - 1])
        elif last.kind == ReplyKind.ASK_INPUT:
            spec = spec or next(x for x in REGISTRY if last.text.startswith(f"Sure -- to {x.label} "))
            if empty_once:
                answer, empty_once = "", False
            else:
                answer = spec.inputs[len(session._inputs)].example
        else:
            break
        turns.append(answer)
        replies.append(session.respond(answer))
    # Replayed through _play so every reply carries its function the same way.
    return _play(role, turns, nav)


def _gate(role: StaffRole, spec) -> dict:
    policy = ROLE_POLICY[role]
    categories = spec.categories if spec.categories is not None else set().union(
        *(ARTEFACTS[a].categories for a in spec.artefacts))
    decision = authorise(role, spec.purpose, spec.artefacts, spec.categories)
    checks = [
        {"rule": "PL-01", "name": "a lawful purpose for this role",
         "ok": spec.purpose in policy.purposes,
         "detail": f"{spec.purpose.value} is {'one' if spec.purpose in policy.purposes else 'not one'} of "
                   f"{role.value}'s purposes ({', '.join(sorted(p.value for p in policy.purposes))})"},
        {"rule": "DM-01", "name": "only data necessary for that purpose",
         "ok": categories <= policy_for(spec.purpose).allowed_categories,
         "detail": "touches " + ", ".join(sorted(c.value for c in categories))},
        {"rule": "SS-01", "name": "only artefacts this role handles",
         "ok": spec.artefacts <= policy.artefacts,
         "detail": ", ".join(f"{ARTEFACTS[a].name}" for a in sorted(spec.artefacts))},
    ]
    return {"allowed": decision.allowed, "rule": decision.rule_id, "provision": decision.provision,
            "reason": decision.reasons[0] if decision.reasons else "", "checks": checks}


def build(out: Path = DEFAULT_OUT) -> dict:
    nav_map = NavigationMap.model_validate_json(NAV_MAP.read_text(encoding="utf-8"))
    nav = nav_map.agent_pages()

    functions = []
    for spec in REGISTRY:
        template = build_guidance(StaffRole.NURSE, spec, {s.name: "{" + s.name + "}" for s in spec.inputs}, nav)
        touched = ", ".join(sorted(c.value for c in template.categories_touched())) or "none"
        functions.append({
            "id": spec.id, "label": spec.label, "synonyms": spec.synonyms, "purpose": spec.purpose.value,
            "artefacts": [ARTEFACTS[a].name for a in sorted(spec.artefacts)],
            "inputs": [{"name": s.name, "prompt": s.prompt, "example": s.example} for s in spec.inputs],
            "steps": [{"text": st.text, "layer": st.layer.value, "artefact": st.artefact_name, "page": st.page,
                       "caution": st.caution} for st in template.steps],
            "touched": touched,
        })

    roles = []
    for role in StaffRole:
        policy = ROLE_POLICY[role]
        session = Session(role, navigation=nav)
        roles.append({
            "id": role.value, "description": policy.description,
            "purposes": sorted(p.value for p in policy.purposes),
            "may_touch": sorted(c.value for c in policy.allowed_categories()),
            "gate": {spec.id: _gate(role, spec) for spec in REGISTRY},
            "decline": {spec.id: (session._begin(spec).text if not spec.permitted_for(role) else None)
                        for spec in REGISTRY},
            "unrecognised": session._unrecognised().text,
        })
        session.reset()

    # Every conversation the page must reproduce exactly.
    vectors = []
    for role in StaffRole:
        for spec in REGISTRY:
            for phrase in [spec.label, *spec.synonyms]:
                vectors.append(_conversation(role, phrase, nav))
            vectors.append(_conversation(role, spec.label, nav, empty_once=True))
        for probe in PROBES:
            first = Session(role).respond(probe)
            if first.kind == ReplyKind.ASK_CHOOSE:
                for i in range(1, len(first.options) + 1):
                    vectors.append(_conversation(role, probe, nav, pick=i))
                vectors.append(_conversation(role, probe, nav, bad_choice=True))
            else:
                vectors.append(_conversation(role, probe, nav))
        vectors.append(_conversation(role, "", nav))
    scenes = [_play(StaffRole(r), turns, nav) for r, turns in SCENES]

    data = {
        "stopwords": sorted(_STOPWORDS),
        "tokens": {k: sorted(v) for k, v in _SPEC_TOKENS.items()},
        "order": [s.id for s in REGISTRY],
        "functions": functions,
        "roles": roles,
        "purposes": {p.value: {"note": pol.legitimate_use_note, "days": pol.max_retention_days}
                     for p, pol in PURPOSE_POLICY.items()},
        "pages": nav,
        "vectors": vectors,
        "scenes": scenes,
        "meta": {"functions": len(REGISTRY), "conversations": len(vectors),
                 "portal_discovered": nav_map.discovered_at.date().isoformat()},
    }
    write(out, render(TEMPLATE, data, current="assistant", out=out))
    return data


def main() -> int:
    data = build()
    print(f"  wrote {DEFAULT_OUT}")
    print(f"  {data['meta']['functions']} functions x {len(data['roles'])} roles; "
          f"{data['meta']['conversations']} Python conversations embedded for the page's self-check")
    return 0


if __name__ == "__main__":
    sys.exit(main())
