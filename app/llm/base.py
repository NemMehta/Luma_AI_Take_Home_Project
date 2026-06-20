"""Shared, provider-neutral LLM interface."""

from __future__ import annotations

from abc import ABC, abstractmethod


class LLMClient(ABC):
    """A provider-neutral LLM client.

    The interface is intentionally free of any provider-specific or image-library
    types so that providers (OpenRouter today; Claude, OpenAI, ... later) can be
    swapped without touching callers.
    """

    @abstractmethod
    def generate(self, prompt: str, image: str | None = None) -> str:
        """Generate a text response for ``prompt``.

        Args:
            prompt: The text prompt.
            image: Optional path to a PNG file on disk, as a plain string. The
                implementation reads and encodes the bytes itself; no image
                objects cross this interface.

        Returns:
            The model's text response.
        """
        ...
