"""OpenRouter implementation of the LLMClient interface.

All OpenRouter / OpenAI-SDK specifics are contained in this module.
"""

from __future__ import annotations

import base64
from pathlib import Path

from openai import OpenAI

from app.llm.base import LLMClient

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
#DEFAULT_MODEL = "qwen/qwen2.5-vl-72b-instruct:free"
DEFAULT_MODEL = "nvidia/nemotron-nano-12b-v2-vl:free"

class OpenRouterClient(LLMClient):
    """LLMClient backed by OpenRouter's OpenAI-compatible API."""

    def __init__(self, api_key: str, model: str = DEFAULT_MODEL) -> None:
        self._client = OpenAI(base_url=OPENROUTER_BASE_URL, api_key=api_key)
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
