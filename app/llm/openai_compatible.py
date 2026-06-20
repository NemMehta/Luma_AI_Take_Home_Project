"""Client for any OpenAI-compatible chat completions API.

Provider specifics (base URL, model id) are supplied by the caller — see
``factory.py`` — so the same class backs GitHub Models, OpenRouter, and any
other OpenAI-compatible endpoint without subclassing.
"""

from __future__ import annotations

import base64
from pathlib import Path

from openai import OpenAI

from app.llm.base import LLMClient


class OpenAICompatibleClient(LLMClient):
    """LLMClient backed by any OpenAI-compatible chat completions endpoint."""

    def __init__(self, base_url: str, api_key: str, model: str) -> None:
        self._client = OpenAI(base_url=base_url, api_key=api_key)
        self._model = model

    def generate(self, prompt: str, image: str | None = None) -> str:
        content: list[dict] = [{"type": "text", "text": prompt}]
        if image is not None:
            content.append(
                {"type": "image_url", "image_url": {"url": _png_data_url(image)}}
            )

        response = self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": content}],
        )
        return response.choices[0].message.content or ""


def _png_data_url(path: str) -> str:
    """Read a PNG from ``path`` and return it as a base64 ``data:`` URL."""
    encoded = base64.b64encode(Path(path).read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"
