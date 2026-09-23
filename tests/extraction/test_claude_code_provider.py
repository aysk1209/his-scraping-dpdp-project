"""The subscription-backed Claude provider (``claude -p``), with the CLI faked.

What must hold for its recordings to be comparable with the API adapters': the
model sees only our brief (our system prompt, no tools, no MCP, no skills, an
empty working directory), the effort is pinned rather than inherited from the
signed-in user's settings, an API key in the environment never switches it to
API billing, and the answer is the schema-validated one. No test here reaches
the real CLI.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from extraction.techniques import ai_providers
from extraction.techniques.ai_providers import EXPLICIT_ONLY, PROVIDERS, ClaudeCodeProvider

DECISION = {"fields": ["patient_administration/mrn"], "retention_days": 30}
SCHEMA = {"type": "object"}


class FakeCLI:
    """Stands in for subprocess.run; records every call."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    def __call__(self, cmd, **kw):
        self.calls.append({"cmd": cmd, **kw})
        code, payload = self.replies.pop(0)
        return SimpleNamespace(returncode=code, stdout=json.dumps(payload), stderr="")


@pytest.fixture()
def cli(monkeypatch):
    monkeypatch.setattr(ai_providers.shutil, "which", lambda name: "C:/bin/claude.exe")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-should-never-reach-the-cli")
    monkeypatch.setenv("CLAUDECODE", "1")

    def install(*replies):
        fake = FakeCLI(replies)
        monkeypatch.setattr(ai_providers.subprocess, "run", fake)
        return fake
    return install


def test_the_model_sees_only_our_brief(cli):
    fake = cli((0, {"is_error": False, "structured_output": DECISION}))
    assert ClaudeCodeProvider(model="claude-haiku-4-5").decide("SYSTEM", "USER", SCHEMA) == DECISION
    call = fake.calls[0]
    cmd = call["cmd"]
    assert cmd[cmd.index("--system-prompt") + 1] == "SYSTEM"        # replaces Claude Code's own
    assert cmd[cmd.index("--tools") + 1] == ""                      # no tools
    assert "--strict-mcp-config" in cmd and "--disable-slash-commands" in cmd
    assert cmd[cmd.index("--model") + 1] == "claude-haiku-4-5"
    assert cmd[cmd.index("--effort") + 1] == "high"                 # pinned, not the user's setting
    assert json.loads(cmd[cmd.index("--json-schema") + 1]) == SCHEMA
    assert call["input"] == "USER"
    # An empty directory, not this repository: no CLAUDE.md, no project files.
    assert Path(call["cwd"]).name.startswith("agent-brief-")
    assert Path(__file__).resolve().parents[2] not in Path(call["cwd"]).resolve().parents


def test_an_api_key_in_the_environment_never_reaches_the_cli(cli):
    fake = cli((0, {"structured_output": DECISION}))
    ClaudeCodeProvider().decide("S", "U", SCHEMA)
    env = fake.calls[0]["env"]
    assert "ANTHROPIC_API_KEY" not in env and "CLAUDECODE" not in env
    assert os.environ["ANTHROPIC_API_KEY"]                           # the parent's is untouched


def test_bare_mode_refused_on_a_subscription_falls_back_once_and_remembers(cli):
    fake = cli((1, {"is_error": True, "result": "Not logged in · Please run /login"}),
               (0, {"structured_output": DECISION}),
               (0, {"structured_output": DECISION}))
    provider = ClaudeCodeProvider()
    assert provider.decide("S", "U", SCHEMA) == DECISION
    assert "--bare" in fake.calls[0]["cmd"] and "--bare" not in fake.calls[1]["cmd"]
    provider.decide("S", "U", SCHEMA)
    assert len(fake.calls) == 3 and "--bare" not in fake.calls[2]["cmd"]   # no second wasted attempt


def test_the_answer_is_read_from_structured_output_or_the_result_text(cli):
    cli((0, {"result": json.dumps(DECISION)}))
    assert ClaudeCodeProvider(bare=False).decide("S", "U", SCHEMA) == DECISION
    cli((0, {"result": "```json\n" + json.dumps(DECISION) + "\n```"}))
    assert ClaudeCodeProvider(bare=False).decide("S", "U", SCHEMA) == DECISION


def test_a_failed_call_is_an_error_not_an_empty_decision(cli):
    cli((1, {"is_error": True, "result": "Overloaded"}))
    with pytest.raises(RuntimeError, match="Overloaded"):
        ClaudeCodeProvider(bare=False).decide("S", "U", SCHEMA)


def test_a_spent_usage_window_stops_the_recorder_instead_of_failing_every_task(cli):
    from extraction.techniques.ai_providers import ProviderUnavailable
    cli((1, {"is_error": True, "result": "Claude usage limit reached. Your limit will reset at 5pm"}))
    with pytest.raises(ProviderUnavailable, match="usage limit"):
        ClaudeCodeProvider(bare=False).decide("S", "U", SCHEMA)


def test_it_is_used_only_when_named():
    assert "claude-code" in PROVIDERS and "claude-code" in EXPLICIT_ONLY


def test_a_live_decision_is_recorded_under_its_own_provider_with_the_conditions(cli, tmp_path):
    from compliance.models import Purpose
    from extraction.adapters.mock_his import MockHISDataSource
    from extraction.technique import ExtractionTask, LayerFields
    from extraction.techniques.ai_agent import AIAgentTechnique
    from interop.layers import HISLayer

    decision = {
        "fields": ["patient_administration/mrn", "patient_administration/sex"], "scope": "one_patient",
        "purpose_specified": True, "secondary_uses": [], "lawful_basis_type": "legitimate_use",
        "lawful_basis_reference": "s.7", "retention_days": 30, "deletion_mechanism": "PURGE-01",
        "transport_encrypted": True, "at_rest_encrypted": True, "access_controlled": True,
        "identifiers_pseudonymised": True, "notice_reference": "N-1", "notice_covers_purpose": True,
        "notice_machine_readable": True, "audit_log_enabled": True, "accountable_party": "DPO",
        "processing_record_kept": True, "rationale": "field names only",
    }
    cli((0, {"structured_output": decision}))
    tech = AIAgentTechnique("claude-code", briefing="policy", mode="live", recordings_dir=tmp_path,
                            model="claude-haiku-4-5")
    task = ExtractionTask(task_id="t", purpose=Purpose.CARE_COORDINATION,
                          needed=[LayerFields(layer=HISLayer.PATIENT_ADMINISTRATION, fields=["mrn", "sex"])])
    tech.decide(MockHISDataSource(records_per_layer=2, seed=1), task)
    recording = json.loads((tmp_path / "claude-code--claude-haiku-4-5--policy.json").read_text(encoding="utf-8"))
    assert recording["provider"] == "claude-code" and recording["model"] == "claude-haiku-4-5"
    assert "effort high (pinned)" in recording["sampling"] and "empty directory" in recording["sampling"]
    assert tech.name == "ai agent: claude-haiku-4-5 (told the policy)"
