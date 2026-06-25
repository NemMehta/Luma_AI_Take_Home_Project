"""Factory that selects an LLM provider client from the environment.

Anthropic uses its own ``AnthropicClient``. OpenAI, GitHub Models, and OpenRouter
are OpenAI-compatible and share ``OpenAICompatibleClient``; their per-provider config
(base URL, model id) lives here — only that config differs between them.
"""

from __future__ import annotations

import os

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


def _is_real(value: str | None) -> bool:
    """A key counts only if it is non-empty and not an obvious xxxxx placeholder.

    Catches the .env.example stubs (sk-xxxxx, sk-ant-xxxxx, ghp_xxxxx, xxxxx). No
    length/prefix checks — those could wrongly reject a real key later.
    """
    value = (value or "").strip()
    return bool(value) and "xxxxx" not in value


def get_llm_client() -> LLMClient:
    """Return a client for the first provider with a real (non-placeholder) key.

    Order: Anthropic (ANTHROPIC_API_KEY), OpenAI (OPENAI_API_KEY), GitHub Models
    (GITHUB_TOKEN), then OpenRouter (OPENROUTER_API_KEY). Earlier providers win, so
    a reviewer's real key takes precedence even if a stub for a later one is still
    in the environment. Anthropic uses its own client (AnthropicClient); the model
    id is that client's default rather than config here, since — unlike the shared
    OpenAI-compatible providers — it is not selected by base URL.
    Add a provider by checking its key here and returning a configured client.
    """
    # Anthropic wins first; its model id lives in AnthropicClient, not configured here.
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    if _is_real(anthropic_key):
        return AnthropicClient(api_key=anthropic_key)

    openai_key = os.environ.get("OPENAI_API_KEY")
    if _is_real(openai_key):
        return OpenAICompatibleClient(
            base_url=OPENAI_BASE_URL, api_key=openai_key, model=OPENAI_MODEL
        )

    github_token = os.environ.get("GITHUB_TOKEN")
    if _is_real(github_token):
        return OpenAICompatibleClient(
            base_url=GITHUB_MODELS_BASE_URL, api_key=github_token, model=GITHUB_MODELS_MODEL
        )

    openrouter_key = os.environ.get("OPENROUTER_API_KEY")
    if _is_real(openrouter_key):
        return OpenAICompatibleClient(
            base_url=OPENROUTER_BASE_URL, api_key=openrouter_key, model=OPENROUTER_MODEL
        )

    raise RuntimeError(
        "No LLM provider key found. Set ANTHROPIC_API_KEY, OPENAI_API_KEY, "
        "GITHUB_TOKEN, or OPENROUTER_API_KEY (e.g. in your .env)."
    )
