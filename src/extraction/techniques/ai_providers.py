"""Thin adapters over publicly available AI models, for the AI-agent technique.

One job: given a system prompt, a user prompt and a JSON schema, return the
model's decision as a dict that validates against the schema. Nothing here
knows what the decision is *about* -- the technique (``ai_agent.py``) owns the
prompts and the interpretation; this file owns the SDK calls.

Three public providers, each behind its own official SDK, imported lazily so the
repository runs without any of them installed:

    claude   -> ``anthropic``       ANTHROPIC_API_KEY
    openai   -> ``openai``          OPENAI_API_KEY
    gemini   -> ``google-genai``    GEMINI_API_KEY (or GOOGLE_API_KEY)

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
from dataclasses import dataclass, field
from typing import Any, Protocol

PROVIDERS = ("claude", "openai", "gemini")

# One decision is a short structured answer; anything beyond this is a stalled
# connection, and a stall must surface as an error the recorder can retry.
REQUEST_TIMEOUT_S = 90.0

DEFAULT_MODELS = {
    "claude": "claude-opus-5",
    "openai": "gpt-6-astra",
    "gemini": "gemini-3.1-flash-lite",     # the recorded model; the flagship's free tier proved unusable (2026-09-22)
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
    raise ValueError(f"unknown provider '{name}'; choose from {', '.join(PROVIDERS)}")


__all__ = [
    "PROVIDERS", "DEFAULT_MODELS", "Provider", "ProviderUnavailable",
    "ClaudeProvider", "OpenAIProvider", "GeminiProvider", "FakeProvider",
    "provider_for", "model_for", "key_available", "list_models",
]
