"""Factory that selects an LLM provider based on the available API key."""

from __future__ import annotations

import os

from app.llm.base import LLMClient
from app.llm.openrouter import OpenRouterClient


def get_llm_client() -> LLMClient:
    """Return an LLMClient for whichever provider key is present.

    Phase 0 supports only OpenRouter. Add providers by checking their key here
    and returning the matching client.
    """
    if os.environ.get("OPENROUTER_API_KEY"):
        return OpenRouterClient(api_key=os.environ["OPENROUTER_API_KEY"])

    raise RuntimeError(
        "No LLM provider key found. Set OPENROUTER_API_KEY (e.g. in your .env)."
    )
