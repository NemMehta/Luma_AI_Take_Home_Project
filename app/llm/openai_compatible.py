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

# verify() ping: cap the wait so one slow/unreachable provider can't stall the
# whole /models check (the pings run concurrently, but each still needs a bound).
_VERIFY_TIMEOUT_S = 10.0


class OpenAICompatibleClient(LLMClient):
    """LLMClient backed by any OpenAI-compatible chat completions endpoint."""

    def __init__(self, base_url: str, api_key: str, model: str) -> None:
        self._client = OpenAI(base_url=base_url, api_key=api_key)
        self._model = model

    def generate(self, prompt: str, image: str | None = None, *, json_object: bool = False) -> str:
        content: list[dict] = [{"type": "text", "text": prompt}]
        if image is not None:
            content.append(
                {"type": "image_url", "image_url": {"url": _image_data_url(image)}}
            )

        extra: dict = {}
        if json_object:
            extra["response_format"] = {"type": "json_object"}

        response = self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": content}],
            **extra,
        )
        return response.choices[0].message.content or ""

    def verify(self) -> None:
        # Smallest legal chat call: one output token, plain text. Raises on a bad
        # key (401/403), a model id this key can't use (404), or a rate limit (429).
        self._client.chat.completions.create(
            model=self._model,
            max_tokens=1,
            messages=[{"role": "user", "content": "ping"}],
            timeout=_VERIFY_TIMEOUT_S,
        )


def _image_data_url(path: str) -> str:
    """Read an image from ``path`` and return it as a base64 ``data:`` URL.

    The MIME type is sniffed from the file's magic bytes so PNG and JPEG — the
    formats Playwright stores in a trace — are both labelled correctly.
    """
    data = Path(path).read_bytes()
    mime = "image/jpeg" if data[:3] == b"\xff\xd8\xff" else "image/png"
    encoded = base64.b64encode(data).decode("ascii")
    return f"data:{mime};base64,{encoded}"
