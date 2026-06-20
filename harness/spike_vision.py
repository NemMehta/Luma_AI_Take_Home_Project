"""Phase 0 spike: prove the screenshot -> OpenRouter vision flow end to end.

Run from the repo root:

    python -m harness.spike_vision /path/to/screenshot.png

It sends a real PNG (base64 data URL, not text) to a free vision model and
prints the model's description. A useful description back = the integration works.
"""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

from app.llm import get_llm_client

PROMPT = "Describe what is shown in this screenshot."


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python -m harness.spike_vision <path-to-png>", file=sys.stderr)
        return 2

    image_path = sys.argv[1]
    if not Path(image_path).is_file():
        print(f"file not found: {image_path}", file=sys.stderr)
        return 2

    load_dotenv()
    client = get_llm_client()
    print(client.generate(PROMPT, image=image_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
