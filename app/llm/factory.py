"""Factory that selects an OpenAI-compatible provider from the environment.

Provider config (base URL, model id) lives here, not in the client, so the same
``OpenAICompatibleClient`` backs every provider — only the config differs.
"""

from __future__ import annotations

import os

from app.llm.base import LLMClient
from app.llm.openai_compatible import OpenAICompatibleClient

# GitHub Models (primary). gpt-4o-mini on purpose: enough for the vision spike
# and early iteration without burning the small gpt-4o free allowance.
GITHUB_MODELS_BASE_URL = "https://models.github.ai/inference"
GITHUB_MODELS_MODEL = "openai/gpt-4o-mini"

# OpenRouter (fallback). Free vision model.
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "nvidia/nemotron-nano-12b-v2-vl:free"


def get_llm_client() -> LLMClient:
    """Return a client for the first provider whose key is present.

    Order: GitHub Models (GITHUB_TOKEN), then OpenRouter (OPENROUTER_API_KEY).
    Add a provider by checking its key here and returning a configured client.
    """
    if os.environ.get("GITHUB_TOKEN"):
        return OpenAICompatibleClient(
            base_url=GITHUB_MODELS_BASE_URL,
            api_key=os.environ["GITHUB_TOKEN"],
            model=GITHUB_MODELS_MODEL,
        )

    if os.environ.get("OPENROUTER_API_KEY"):
        return OpenAICompatibleClient(
            base_url=OPENROUTER_BASE_URL,
            api_key=os.environ["OPENROUTER_API_KEY"],
            model=OPENROUTER_MODEL,
        )

    raise RuntimeError(
        "No LLM provider key found. Set GITHUB_TOKEN or OPENROUTER_API_KEY "
        "(e.g. in your .env)."
    )
