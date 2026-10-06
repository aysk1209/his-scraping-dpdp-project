"""Every committed AI-agent recording still answers today's brief.

A recording is a model's answer to one exact brief -- the task wording, the
catalogue and the capability register's descriptions. Change any of them and
the recording goes stale, and the benchmark (rightly) leaves that agent out.
That must never happen silently: rewording a register description once dropped
every model from the tables. This test fails first instead.
"""

from __future__ import annotations

import re

from compliance.benchmark import bind_subject
from extraction.adapters.mock_his import MockHISDataSource
from extraction.techniques.ai_agent import RECORDINGS_DIR, AIAgentTechnique
from scripts.run_benchmark import TASKS

_NAME = re.compile(r"^(?P<provider>[^-]+(?:-code)?)--(?P<model>.+)--(?P<briefing>unaided|informed|policy)\.json$")


def test_no_committed_recording_is_stale():
    source = MockHISDataSource(records_per_layer=5, seed=42)
    tasks = bind_subject(TASKS, source)
    files = sorted(p for p in RECORDINGS_DIR.glob("*.json") if not p.name.startswith("."))
    assert files, "no recordings found"
    stale = {}
    for path in files:
        m = _NAME.match(path.name)
        assert m, f"unexpected recording name {path.name}"
        tech = AIAgentTechnique(m["provider"], briefing=m["briefing"], mode="replay", model=m["model"])
        gone = tech.stale_tasks(source, tasks)
        if gone:
            stale[path.name] = gone
    assert not stale, ("recordings no longer match the brief (a task, the catalogue or a register "
                       f"description changed): {stale}")
