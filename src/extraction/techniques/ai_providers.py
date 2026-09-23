"""Thin adapters over publicly available AI models, for the AI-agent technique.

One job: given a system prompt, a user prompt and a JSON schema, return the
model's decision as a dict that validates against the schema. Nothing here
knows what the decision is *about* -- the technique (``ai_agent.py``) owns the
prompts and the interpretation; this file owns the SDK calls.

Three public providers, each behind its own official SDK, imported lazily so the
repository runs without any of them installed:

    claude       -> ``anthropic``       ANTHROPIC_API_KEY
    openai       -> ``openai``          OPENAI_API_KEY
    gemini       -> ``google-genai``    GEMINI_API_KEY (or GOOGLE_API_KEY)
    claude-code  -> the Claude Code CLI, signed in with a Claude subscription (no API key)

Model identifiers default to a current model of each and can be overridden
with ``AI_AGENT_MODEL_CLAUDE`` / ``_OPENAI`` / ``_GEMINI`` so the comparison can be
re-run against whatever is current without a code change.

A ``FakeProvider`` returns scripted decisions for tests and never touches the
network. Nothing in this module ever receives a patient value: the technique
sends field *names* and a task description, by design (see ``ai_agent.py``).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from typing import Any, Protocol

PROVIDERS = ("claude", "openai", "gemini", "claude-code")
# Providers the recorder uses only when named: they spend a person's own
# subscription allowance, so being installed is not consent to use them.
EXPLICIT_ONLY = ("claude-code",)

# One decision is a short structured answer; anything beyond this is a stalled
# connection, and a stall must surface as an error the recorder can retry.
REQUEST_TIMEOUT_S = 90.0

DEFAULT_MODELS = {
    "claude": "claude-opus-5",
    "openai": "gpt-6-astra",
    "gemini": "gemini-3.1-flash-lite",     # the recorded model; the flagship's free tier proved unusable (2026-09-22)
    "claude-code": "claude-haiku-4-5",
}

_KEY_VARS = {
    "claude": ("ANTHROPIC_API_KEY",),
    "openai": ("OPENAI_API_KEY",),
    "gemini": ("GEMINI_API_KEY", "GOOGLE_API_KEY"),
}


def model_for(provider: str) -> str:
    return os.environ.get(f"AI_AGENT_MODEL_{provider.upper()}") or DEFAULT_MODELS.get(provider, provider)


def key_available(provider: str) -> bool:
    """True when the environment carries a credential for ``provider``.

    The value is never read here beyond checking it is non-empty.
    """

    if provider == "claude-code":
        return shutil.which("claude") is not None       # a subscription sign-in, not a key
    return any(os.environ.get(var) for var in _KEY_VARS.get(provider, ()))


class Provider(Protocol):
    name: str
    model: str

    def decide(self, system: str, user: str, schema: dict[str, Any]) -> dict[str, Any]:
        """Return a dict conforming to ``schema``. Raise on any failure."""


class ProviderUnavailable(RuntimeError):
    """The SDK is missing or the credential is absent."""


# ----------------------------------------------------------------- claude ----


@dataclass
class ClaudeProvider:
    name: str = "claude"
    model: str = field(default_factory=lambda: model_for("claude"))

    def decide(self, system: str, user: str, schema: dict[str, Any]) -> dict[str, Any]:
        try:
            import anthropic
        except ImportError as exc:                     # pragma: no cover - environment
            raise ProviderUnavailable("pip install anthropic") from exc
        if not key_available("claude"):
            raise ProviderUnavailable("ANTHROPIC_API_KEY is not set")

        client = anthropic.Anthropic(timeout=REQUEST_TIMEOUT_S)
        response = client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": user}],
            output_config={"format": {"type": "json_schema", "schema": schema}},
        )
        if response.stop_reason == "refusal":
            raise RuntimeError(f"{self.model} declined the request")
        text = next(b.text for b in response.content if b.type == "text")
        return json.loads(text)


# ----------------------------------------------------------------- openai ----


@dataclass
class OpenAIProvider:
    name: str = "openai"
    model: str = field(default_factory=lambda: model_for("openai"))

    def decide(self, system: str, user: str, schema: dict[str, Any]) -> dict[str, Any]:
        try:
            from openai import OpenAI
        except ImportError as exc:                     # pragma: no cover - environment
            raise ProviderUnavailable("pip install openai") from exc
        if not key_available("openai"):
            raise ProviderUnavailable("OPENAI_API_KEY is not set")

        client = OpenAI(timeout=REQUEST_TIMEOUT_S)
        response = client.responses.create(
            model=self.model,
            input=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            text={"format": {"type": "json_schema", "name": "agent_decision",
                             "schema": schema, "strict": True}},
        )
        return json.loads(response.output_text)


# ----------------------------------------------------------------- gemini ----


@dataclass
class GeminiProvider:
    name: str = "gemini"
    model: str = field(default_factory=lambda: model_for("gemini"))

    def decide(self, system: str, user: str, schema: dict[str, Any]) -> dict[str, Any]:
        try:
            from google import genai
        except ImportError as exc:                     # pragma: no cover - environment
            raise ProviderUnavailable("pip install google-genai") from exc
        if not key_available("gemini"):
            raise ProviderUnavailable("GEMINI_API_KEY is not set")

        client = genai.Client()
        # ``response_format`` is a typed TextResponseFormat: a bare schema dict
        # matches no member of the union and is silently dropped (the server
        # then rejects the request as having a mime type but no format).
        interaction = client.interactions.create(
            model=self.model,
            input=user,
            system_instruction=system,
            response_format={"type": "text", "mime_type": "application/json", "schema": schema},
            timeout=REQUEST_TIMEOUT_S,
        )
        return json.loads(interaction.output_text)


# ------------------------------------------------------------ claude code ----


# Environment variables that must not reach the CLI: an API key would switch it
# from the subscription to API billing, and a parent session's markers would
# make it behave as a nested session.
_CLAUDE_CODE_STRIP = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT",
                      "CLAUDE_CODE_SSE_PORT")


@dataclass
class ClaudeCodeProvider:
    """Claude through the Claude Code CLI in headless mode, on a subscription sign-in.

    One call is ``claude -p`` run from an empty temporary directory with *our*
    system prompt replacing Claude Code's own, no tools, no session kept, and
    the JSON schema enforced -- so the model sees exactly the brief the API
    adapters send, and nothing of this repository (no CLAUDE.md, no memory, no
    files). ``--bare`` additionally skips hooks, skills and memory discovery;
    where the installed CLI refuses a subscription sign-in in bare mode, the
    call is retried without it and the empty directory is what keeps project
    context out.
    """

    name: str = "claude-code"
    model: str = field(default_factory=lambda: model_for("claude-code"))
    # Pinned, not inherited: the signed-in user's own settings (effortLevel) would
    # otherwise decide how hard the model thinks, and the recording could not say.
    effort: str = "high"
    bare: bool = True

    @property
    def sampling(self) -> str:
        return (f"Claude Code headless (claude -p) on a subscription sign-in; our system prompt replaces "
                f"Claude Code's; no tools, no MCP servers, no skills; run from an empty directory; "
                f"effort {self.effort} (pinned); no temperature or seed set")

    def command(self, system: str, schema: dict[str, Any], *, bare: bool) -> list[str]:
        exe = shutil.which("claude")
        if exe is None:
            raise ProviderUnavailable("the Claude Code CLI (claude) is not on PATH")
        cmd = [exe, "-p", "--model", self.model, "--effort", self.effort, "--system-prompt", system,
               "--tools", "", "--strict-mcp-config", "--json-schema", json.dumps(schema),
               "--output-format", "json", "--no-session-persistence", "--disable-slash-commands",
               "--max-turns", "3"]
        return cmd + (["--bare"] if bare else [])

    def decide(self, system: str, user: str, schema: dict[str, Any]) -> dict[str, Any]:
        env = {k: v for k, v in os.environ.items() if k not in _CLAUDE_CODE_STRIP}
        last = ""
        for bare in ([True, False] if self.bare else [False]):
            with tempfile.TemporaryDirectory(prefix="agent-brief-") as cwd:
                proc = subprocess.run(self.command(system, schema, bare=bare), input=user, capture_output=True,
                                      text=True, encoding="utf-8", timeout=REQUEST_TIMEOUT_S * 2, cwd=cwd, env=env)
            out = (proc.stdout or "").strip()
            try:
                data = json.loads(out) if out else {}
            except ValueError:
                data = {}
            if proc.returncode == 0 and isinstance(data, dict) and data and not data.get("is_error"):
                return _claude_code_decision(data)
            last = (data.get("result") if isinstance(data, dict) else "") or proc.stderr or out
            if bare and any(w in str(last).lower() for w in ("login", "log in", "api key", "auth")):
                self.bare = False                       # bare mode wants an API key: signed in from now on
                continue
            if "limit" in str(last).lower() and any(w in str(last).lower() for w in ("usage", "reset", "hit your")):
                # The subscription's usage window is spent: nothing more will succeed until it
                # resets, so stop the run cleanly (the recorder resumes where it left off).
                raise ProviderUnavailable(f"the subscription's usage limit is reached ({str(last).strip()[:120]}); "
                                          f"re-run the same command after it resets")
            break
        raise RuntimeError(f"claude -p failed: {str(last).strip()[:300]}")


def _claude_code_decision(data: dict[str, Any]) -> dict[str, Any]:
    """The schema-validated answer from ``claude -p --output-format json``."""

    if isinstance(data.get("structured_output"), dict):
        return data["structured_output"]
    result = data.get("result")
    if isinstance(result, dict):
        return result
    text = str(result or "").strip()
    if text.startswith("```"):
        text = text.strip("`").split("\n", 1)[-1]
    return json.loads(text)


# ------------------------------------------------------------------- fake ----


@dataclass
class FakeProvider:
    """Scripted decisions for tests: returns ``decisions`` in order, cycling.

    A list with one entry is a deterministic agent; several differing entries
    are a non-deterministic one, which is what the benchmark's determinism
    column has to be able to see.
    """

    decisions: list[dict[str, Any]]
    name: str = "fake"
    model: str = "fake-1"
    calls: list[tuple[str, str]] = field(default_factory=list)

    def decide(self, system: str, user: str, schema: dict[str, Any]) -> dict[str, Any]:
        self.calls.append((system, user))
        return dict(self.decisions[(len(self.calls) - 1) % len(self.decisions)])


def list_models(provider: str) -> list[str]:
    """Model ids the account behind ``provider``'s key can actually use.

    Read-only, one call. Accounts differ in tier -- a free OpenAI account or a
    Gemini Pro subscription do not see the same ids -- so the recording script
    offers this before anyone guesses a default.
    """

    if not key_available(provider):
        raise ProviderUnavailable(f"no key for {provider}")
    # Listings paginate lazily, so the client must outlive the iteration --
    # a temporary ``Client()`` in the loop header is closed before page two.
    if provider == "claude":
        import anthropic
        client = anthropic.Anthropic()
        return sorted(m.id for m in client.models.list())
    if provider == "openai":
        from openai import OpenAI
        client = OpenAI()
        return sorted(m.id for m in client.models.list())
    if provider == "claude-code":
        # The CLI takes aliases and full ids; these are the ones a Pro sign-in serves.
        return ["claude-haiku-4-5", "claude-sonnet-5"]
    if provider == "gemini":
        from google import genai
        client = genai.Client()
        names = []
        for m in client.models.list():
            name = getattr(m, "name", "") or ""
            names.append(name.split("/", 1)[-1])       # "models/gemini-..." -> "gemini-..."
        return sorted(n for n in names if n)
    raise ValueError(f"unknown provider '{provider}'")


def provider_for(name: str, model: str | None = None) -> Provider:
    """An adapter for ``name``; ``model`` overrides the env/default model id."""

    kwargs = {"model": model} if model else {}
    if name == "claude":
        return ClaudeProvider(**kwargs)
    if name == "openai":
        return OpenAIProvider(**kwargs)
    if name == "gemini":
        return GeminiProvider(**kwargs)
    if name == "claude-code":
        return ClaudeCodeProvider(**kwargs)
    raise ValueError(f"unknown provider '{name}'; choose from {', '.join(PROVIDERS)}")


__all__ = [
    "PROVIDERS", "EXPLICIT_ONLY", "DEFAULT_MODELS", "Provider", "ProviderUnavailable",
    "ClaudeProvider", "OpenAIProvider", "GeminiProvider", "ClaudeCodeProvider", "FakeProvider",
    "provider_for", "model_for", "key_available", "list_models",
]
