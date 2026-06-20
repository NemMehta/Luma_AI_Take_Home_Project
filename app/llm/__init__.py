"""Provider-neutral LLM client package.

Public surface: the abstract ``LLMClient`` interface, the ``OpenRouterClient``
implementation, and the ``get_llm_client`` factory. Add new providers as sibling
modules next to ``openrouter.py`` without changing the interface or callers.
"""

from app.llm.base import LLMClient
from app.llm.factory import get_llm_client
from app.llm.openrouter import OpenRouterClient

__all__ = ["LLMClient", "OpenRouterClient", "get_llm_client"]
