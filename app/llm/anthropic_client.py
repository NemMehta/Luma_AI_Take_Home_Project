"""Client for Anthropic's Messages API.

Anthropic is not OpenAI-compatible, so it gets its own ``LLMClient`` rather than
reusing ``OpenAICompatibleClient`` — the sibling-module path the package docstring
anticipates. The interface (``generate``) is unchanged; only the wire calls differ:
this client uses ``messages.create`` with Anthropic content blocks.
"""

from __future__ import annotations

import base64
from pathlib import Path

import anthropic

from app.llm.base import LLMClient

# Default model. claude-haiku-4-5 is vision-capable and cheap enough for the
# classifier. NOTE: confirm this id against a real Anthropic key before relying on
# it — this seam was built and verified without a live API call.
DEFAULT_MODEL = "claude-haiku-4-5"

# Messages API requires max_tokens. 4096 comfortably covers the classifier's JSON
# output and keeps the (non-streaming) request well under the SDK's timeout.
MAX_TOKENS = 4096

# Anthropic has no OpenAI-style response_format, so JSON mode is prompted: instruct
# the model to emit exactly one JSON object and nothing else. The caller's prompt
# still describes the desired shape (see LLMClient.generate).
_JSON_ONLY_INSTRUCTION = (
    "Return only one valid JSON object. Do not include any prose, explanation, "
    "or markdown code fences — output the JSON object and nothing else."
)


class AnthropicClient(LLMClient):
    """LLMClient backed by Anthropic's Messages API."""

    def __init__(self, api_key: str, model: str = DEFAULT_MODEL) -> None:
        # Constructing the client does not make a network call; requests happen in
        # generate(). Safe to build with a placeholder key.
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def generate(self, prompt: str, image: str | None = None, *, json_object: bool = False) -> str:
        text = f"{prompt}\n\n{_JSON_ONLY_INSTRUCTION}" if json_object else prompt

        content: list[dict] = []
        if image is not None:
            media_type, data = _encode_image(image)
            content.append(
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": media_type, "data": data},
                }
            )
        content.append({"type": "text", "text": text})

        response = self._client.messages.create(
            model=self._model,
            max_tokens=MAX_TOKENS,
            messages=[{"role": "user", "content": content}],
        )
        return "".join(block.text for block in response.content if block.type == "text")


def _encode_image(path: str) -> tuple[str, str]:
    """Read an image from ``path`` and return ``(media_type, base64_data)``.

    The MIME type is sniffed from the file's magic bytes so PNG and JPEG — the
    formats Playwright stores in a trace — are both labelled correctly.
    """
    raw = Path(path).read_bytes()
    media_type = "image/jpeg" if raw[:3] == b"\xff\xd8\xff" else "image/png"
    return media_type, base64.b64encode(raw).decode("ascii")
