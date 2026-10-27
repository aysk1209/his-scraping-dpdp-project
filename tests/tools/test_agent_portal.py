"""The HIS Staff Assistant portal (docs/review/agent-portal.html).

Pinned here: the builder refuses a page that would carry a raw identifier; the
page carries the same engine tables and recorded conversations as the assistant
tab, and the page's own engine reproduces every one of them (run under Node where
it is installed); each badge's tour is a recorded Python conversation that ends in
steps that badge may follow; every step the page places on a screen names a module
the crawler found, a button that module has and fields it holds; the request
offered as "not this badge's" is one the gate refuses; and the committed page
carries its data and its font, says it is rule-based, and does not link to the
Report.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess

import pytest

from agent.functions import REGISTRY
from compliance.roles import StaffRole, authorise
from tools import build_agent_portal as ap
from tools import build_assistant_page as assistant
from tools import build_portal_app as v1
from tools.page_kit import REVIEW_DIR

PAGE = REVIEW_DIR / "agent-portal.html"
SPEC = {s.id: s for s in REGISTRY}


def _data(html: str) -> dict:
    return json.loads(re.search(r'<script type="application/json" id="agent-data">(.*?)</script>', html, re.S).group(1))


@pytest.fixture(scope="module")
def built():
    data = ap.payload()
    return data, ap._secrets(), ap.render(data)


def test_the_page_refuses_a_raw_identifier(built):
    data, secrets, html = built
    v1.check(html, secrets)
    with pytest.raises(v1.PortalLeak):
        v1.check(html + next(iter(secrets)), secrets)
    assert _data(html) == data


def test_the_page_carries_the_assistants_own_engine_and_conversations(built):
    data, _, _ = built
    tab = assistant.collect()
    for key in ("stopwords", "tokens", "phrases", "phraseWeight", "commands", "texts", "order", "roles", "vectors"):
        assert data[key] == tab[key], key
    assert [f["id"] for f in data["functions"]] == [f["id"] for f in tab["functions"]]
    for mine, theirs in zip(data["functions"], tab["functions"]):
        assert [s["text"] for s in mine["steps"]] == [s["text"] for s in theirs["steps"]]


@pytest.mark.skipif(shutil.which("node") is None, reason="Node is not installed")
def test_the_pages_engine_reproduces_every_recorded_conversation(built, tmp_path):
    _, _, html = built
    engine = (ap.HERE / "engine.js").read_text(encoding="utf-8")
    blob = re.search(r'<script type="application/json" id="agent-data">(.*?)</script>', html, re.S).group(1)
    (tmp_path / "data.json").write_text(blob, encoding="utf-8")
    script = tmp_path / "check.js"
    script.write_text(
        "const fs = require('fs');\n"
        f"const text = fs.readFileSync({json.dumps(str(tmp_path / 'data.json'))}, 'utf8');\n"
        "globalThis.document = { getElementById: () => ({ textContent: text }) };\n"
        "console.warn = () => {};\n"
        + engine +
        "\nprocess.stdout.write(JSON.stringify({ live: Engine.live, checked: Engine.checked }));\n",
        encoding="utf-8")
    out = json.loads(subprocess.run(["node", str(script)], capture_output=True, text=True, check=True).stdout)
    assert out["live"] is True
    assert out["checked"] == len(_data(html)["vectors"]) > 1000


def test_each_badges_tour_ends_in_steps_that_badge_may_follow(built):
    data, _, _ = built
    assert sorted(t["role"] for t in data["tours"]) == sorted(r.value for r in StaffRole)
    reachable, shown_anywhere = set(), set()
    for tour in data["tours"]:
        last = tour["replies"][-1]
        assert last["kind"] == "guidance", tour["title"]
        assert SPEC[last["fn"]].permitted_for(StaffRole(tour["role"]))
        assert all(r["kind"] in ("declined", "ask_input", "guidance") for r in tour["replies"])
        # A badge the gate can refuse for a reason other than purpose shows such a refusal in its tour,
        # and the tours between them show every rule other than purpose that the gate can reach.
        role = StaffRole(tour["role"])
        other = {authorise(role, s.purpose, s.artefacts, s.categories).rule_id for s in REGISTRY} - {None, "PL-01"}
        shown = {authorise(role, SPEC[r["fn"]].purpose, SPEC[r["fn"]].artefacts, SPEC[r["fn"]].categories).rule_id
                 for r in tour["replies"] if r["kind"] == "declined"} - {"PL-01"}
        assert shown or not other, (tour["role"], other)
        reachable |= other
        shown_anywhere |= shown
        # A tour is a recorded conversation like any other: the page's self-check covers it too.
        assert assistant._play(StaffRole(tour["role"]), tour["turns"], ap.ScreenMap.from_navigation(
            ap.NavigationMap.model_validate_json(assistant.NAV_MAP.read_text(encoding="utf-8"))))["replies"] == tour["replies"]
    assert reachable == shown_anywhere == {"DM-01", "SS-01"}


def test_every_placed_step_is_on_a_screen_the_crawler_found(built):
    data, _, _ = built
    screens = {s["title"]: s for s in data["screens"]}
    placed = 0
    for f in data["functions"]:
        for step in f["steps"]:
            place = step["place"]
            if place is None:
                continue
            placed += 1
            screen = screens[place["module"]]
            assert place["path"] == screen["path"]
            # A step with neither fields nor a button carries on where the step before it left off.
            held = {c["field"] for c in screen["list"] + screen["record"]}
            assert set(step["fields"]) <= held, (f["id"], step["text"])
            if place["button"]:
                assert place["button"] in screen["listButtons"] + screen["recordButtons"], (f["id"], place)
    assert placed > 50


def test_the_request_offered_as_another_badges_is_refused_and_the_common_tasks_are_allowed(built):
    data, _, _ = built
    for role, fn in data["outside"].items():
        assert not SPEC[fn].permitted_for(StaffRole(role))
        assert all(SPEC[c].permitted_for(StaffRole(role)) for c in data["common"][role])


def test_the_committed_page_carries_its_data_and_font_and_no_link_to_the_report():
    html = PAGE.read_text(encoding="utf-8")
    data = _data(html)
    assert len(data["vectors"]) > 1000 and len(data["tours"]) == 3
    assert "data:font/woff2;base64," in html
    assert "report.html" not in html
    assert "Rule-based" in html
