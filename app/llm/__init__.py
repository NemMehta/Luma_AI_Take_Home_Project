"""Provider-neutral LLM client package.

Public surface: the abstract ``LLMClient`` interface, the
``OpenAICompatibleClient`` implementation, and the ``get_llm_client`` factory.
Add a provider via config in ``factory.py`` (same client) or a new sibling
module for a genuinely different API — without changing the interface or callers.
"""

from app.llm.anthropic_client import AnthropicClient
from app.llm.base import LLMClient
from app.llm.factory import get_llm_client
from app.llm.openai_compatible import OpenAICompatibleClient

__all__ = ["AnthropicClient", "LLMClient", "OpenAICompatibleClient", "get_llm_client"]
