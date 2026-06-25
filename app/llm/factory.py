"""Factory that selects an LLM provider client from the environment.

Anthropic uses its own ``AnthropicClient``. OpenAI, GitHub Models, and OpenRouter
are OpenAI-compatible and share ``OpenAICompatibleClient``; their per-provider config
(base URL, model id) lives here — only that config differs between them.

A single ordered ``PROVIDERS`` registry is the source of truth for both selection
and availability checks (see ``availability.py``). The order is the historical
priority order, so ``get_llm_client()`` with no argument behaves exactly as before:
the first provider with a real key wins. ``get_llm_client(provider_id=...)`` honours
an explicit user choice instead.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from app.llm.anthropic_client import DEFAULT_MODEL as ANTHROPIC_MODEL
from app.llm.anthropic_client import AnthropicClient
from app.llm.base import LLMClient
from app.llm.openai_compatible import OpenAICompatibleClient

# OpenAI (used when no Anthropic key is set — e.g. a reviewer's own key).
# gpt-4o is vision-capable.
OPENAI_BASE_URL = "https://api.openai.com/v1"
OPENAI_MODEL = "gpt-4o"

# GitHub Models. gpt-4o-mini on purpose: enough for the vision spike and early
# iteration without burning the small gpt-4o free allowance.
GITHUB_MODELS_BASE_URL = "https://models.github.ai/inference"
GITHUB_MODELS_MODEL = "openai/gpt-4o-mini"

# OpenRouter (fallback). Free vision model.
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "nvidia/nemotron-nano-12b-v2-vl:free"


@dataclass(frozen=True)
class ProviderInfo:
    """One selectable provider/model. ``kind`` picks the client class; ``base_url``
    is ``None`` for Anthropic (its own client) and the endpoint URL otherwise."""

    id: str
    label: str
    model: str
    env_var: str
    kind: str  # "anthropic" | "openai_compatible"
    base_url: str | None = None


# Ordered by historical priority (first real key wins for the no-arg path). The id
# is the stable value the UI sends back; the label is what the dropdown shows.
PROVIDERS: list[ProviderInfo] = [
    ProviderInfo(
        id="anthropic",
        label="Anthropic — Claude Haiku 4.5",
        model=ANTHROPIC_MODEL,
        env_var="ANTHROPIC_API_KEY",
        kind="anthropic",
    ),
    ProviderInfo(
        id="openai",
        label="OpenAI — GPT-4o",
        model=OPENAI_MODEL,
        env_var="OPENAI_API_KEY",
        kind="openai_compatible",
        base_url=OPENAI_BASE_URL,
    ),
    ProviderInfo(
        id="github",
        label="GitHub Models — GPT-4o-mini",
        model=GITHUB_MODELS_MODEL,
        env_var="GITHUB_TOKEN",
        kind="openai_compatible",
        base_url=GITHUB_MODELS_BASE_URL,
    ),
    ProviderInfo(
        id="openrouter",
        label="OpenRouter — Nemotron Nano 12B",
        model=OPENROUTER_MODEL,
        env_var="OPENROUTER_API_KEY",
        kind="openai_compatible",
        base_url=OPENROUTER_BASE_URL,
    ),
]

_PROVIDERS_BY_ID: dict[str, ProviderInfo] = {p.id: p for p in PROVIDERS}


class UnknownProviderError(ValueError):
    """The caller asked for a provider id that is not in the registry."""


class ProviderUnavailableError(RuntimeError):
    """The requested provider exists but has no real (non-placeholder) key set."""


def _is_real(value: str | None) -> bool:
    """A key counts only if it is non-empty and not an obvious xxxxx placeholder.

    Catches the .env.example stubs (sk-xxxxx, sk-ant-xxxxx, ghp_xxxxx, xxxxx). No
    length/prefix checks — those could wrongly reject a real key later.
    """
    value = (value or "").strip()
    return bool(value) and "xxxxx" not in value


def provider_key(info: ProviderInfo) -> str | None:
    """The configured key for ``info``, or None — already trimmed by ``_is_real``."""
    return os.environ.get(info.env_var)


def _build_client(info: ProviderInfo, key: str) -> LLMClient:
    """Construct the client for ``info`` with ``key``. No network call happens here."""
    if info.kind == "anthropic":
        return AnthropicClient(api_key=key, model=info.model)
    return OpenAICompatibleClient(base_url=info.base_url, api_key=key, model=info.model)


def get_llm_client(provider_id: str | None = None) -> LLMClient:
    """Return a configured LLM client.

    With no ``provider_id`` (the historical behaviour): return a client for the
    first provider in ``PROVIDERS`` with a real (non-placeholder) key — Anthropic,
    then OpenAI, GitHub Models, OpenRouter. Earlier providers win, so a reviewer's
    real key takes precedence even if a stub for a later one is still in the env.

    With a ``provider_id``: honour that explicit choice instead of the priority
    order. Raises ``UnknownProviderError`` for an unknown id and
    ``ProviderUnavailableError`` if the chosen provider has no real key.
    """
    if provider_id is not None:
        info = _PROVIDERS_BY_ID.get(provider_id)
        if info is None:
            known = ", ".join(p.id for p in PROVIDERS)
            raise UnknownProviderError(f"unknown model '{provider_id}'. known: {known}")
        key = provider_key(info)
        if not _is_real(key):
            raise ProviderUnavailableError(
                f"model '{provider_id}' is not configured — its API key "
                f"({info.env_var}) is missing."
            )
        return _build_client(info, key)

    for info in PROVIDERS:
        key = provider_key(info)
        if _is_real(key):
            return _build_client(info, key)

    raise RuntimeError(
        "No LLM provider key found. Set ANTHROPIC_API_KEY, OPENAI_API_KEY, "
        "GITHUB_TOKEN, or OPENROUTER_API_KEY (e.g. in your .env)."
    )
