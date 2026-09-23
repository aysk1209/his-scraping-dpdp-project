"""The portal and assistant pages, and the links between the demo pages.

The assistant page runs a copy of the recogniser in the browser and checks it
against Python transcripts on load; these tests pin the Python side of that
bargain: the transcripts cover every role and function and agree with the gate.
The portal page's page-load trace must equal the meter's own count (the builder
refuses otherwise) and must carry no record number.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from agent.functions import REGISTRY
from agent.session import Session
from compliance.audit import AuditLog
from compliance.roles import StaffRole
from tools import build_assistant_page, build_portal_page
from tools.page_kit import PAGES, REVIEW_DIR, nav_html


def _data(html: str) -> dict:
    return json.loads(re.search(r'<script id="data" type="application/json">(.*?)</script>', html, re.S)
                      .group(1).replace("<\\/", "</"))


def test_the_assistant_page_carries_every_role_and_function_and_the_gate_agrees(tmp_path):
    out = tmp_path / "assistant.html"
    data = build_assistant_page.build(out)
    assert data == _data(out.read_text(encoding="utf-8"))
    assert {f["id"] for f in data["functions"]} == {s.id for s in REGISTRY}
    for role in data["roles"]:
        for spec in REGISTRY:
            assert role["gate"][spec.id]["allowed"] == spec.permitted_for(StaffRole(role["id"]))
            # Every role x function has a recorded conversation starting from its label.
            assert any(v["role"] == role["id"] and v["turns"][0] == spec.label for v in data["vectors"])
    kinds = {r["kind"] for v in data["vectors"] for r in v["replies"]}
    assert kinds == {"ask_choose", "ask_input", "declined", "guidance", "unrecognised"}


def test_the_recorded_conversations_are_what_the_python_assistant_says(tmp_path):
    data = build_assistant_page.build(tmp_path / "assistant.html")
    pages = data["pages"]
    for v in data["vectors"][::7]:
        session = Session(StaffRole(v["role"]), navigation=pages)
        assert [session.respond(t).text for t in v["turns"]] == [r["text"] for r in v["replies"]]


def test_the_navigation_bar_links_resolve_from_the_review_folder():
    html = nav_html("index", REVIEW_DIR / "index.html")
    for href in re.findall(r'href="([^"]+)"', html):
        assert (REVIEW_DIR / href).resolve() in {p.resolve() for _, p, _ in PAGES}
    for _, path, _ in PAGES:
        assert path.exists(), f"{path} is linked from every demo page but does not exist"


@pytest.mark.usefixtures("browser_available")
def test_the_portal_page_traces_every_page_load_and_shows_no_record_number(tmp_path):
    out = tmp_path / "portal.html"
    data = build_portal_page.build(out, audit_log=AuditLog(tmp_path / "audit.jsonl"), records=4, page_size=2)
    visits = data["visits"]
    # Discovery signs in the way a person would, before anything else.
    assert [v["kind"] for v in visits[:3]] == ["login", "login-submit", "home"]
    # The builder refuses a trace that disagrees with the meter; totals are therefore the meter's.
    for t in data["techniques"]:
        assert sum(1 for v in visits if v["who"] == t["name"]) == t["pages"]
    ours = next(t for t in data["techniques"] if t["kind"] == "ours")
    base = next(t for t in data["techniques"] if t["kind"] == "baseline")
    assert ours["pages"] < base["pages"]
    searches = [v for v in visits if v["kind"] == "search"]
    assert searches and all(v["q"].startswith("PSN-") for v in searches)
    assert data["meta"]["tls"] is True
