"""Classify a Playwright failure: evidence bundle + screenshot -> diagnosis.

Reads the Phase 2 EvidenceBundle, attaches the failure screenshot from the trace
zip (if present), sends both to the configured LLM (gpt-4o-mini via the existing
client), and returns a structured DiagnosisResult.

Run it:  python -m app.diagnosis.classifier <path-to-trace.zip>
"""

from __future__ import annotations

import contextlib
import json
import os
import sys
import tempfile
import zipfile
from enum import Enum

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from app.diagnosis.ingest import build_evidence_bundle
from app.diagnosis.schema import EvidenceBundle
from app.llm import get_llm_client


class DiagnosisCategory(str, Enum):
    real_bug = "real_bug"
    stale_selector = "stale_selector"
    flaky_timing = "flaky_timing"
    network_failure = "network_failure"
    race_condition = "race_condition"


class DiagnosisResult(BaseModel):
    category: DiagnosisCategory
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str


_CATEGORY_GUIDE = """\
- stale_selector: the selector no longer matches, but the UI/DOM shows the intended
  element still exists under a changed id, text, or structure.
- real_bug: the app reaches a settled state, but that final state is wrong. Selectors
  and actions work; the product behaviour is broken. The DOM changed in response to the
  action but settled into the wrong result (e.g. a filter ran but kept/removed the
  wrong items — the expected item is the one now missing). Waiting longer would NOT help.
- flaky_timing: the selectors resolve and the actions run, but a later assertion about
  the resulting state times out because that state arrives late. The locator still
  finds elements — the page just has not updated yet, so the snapshot still shows the
  pre-action result (e.g. a filtered list still showing ALL the original items,
  including ones the query should exclude, because the filter has not rendered).
  Waiting for the right condition would fix it.
- network_failure: failed requests, bad statuses, timeouts, or missing API data are
  the main clue.
- race_condition: the issue depends on timing or order between actions, updates, or
  async work.

Disambiguating the wrong-count failures — stale_selector, flaky_timing, and real_bug
can all look like a wrong count, so read the DOM page snapshot, not just the error:
1. Did the locator even resolve? If the failing step is a locator/element that was
   never found (it timed out "waiting for locator(...)"), it is stale_selector — not
   flaky_timing.
2. If the locator resolved, did the action's effect actually render? Work out what the
   action should produce, then check the snapshot against it. For a search filter, a
   query like "cher" should narrow the list to the matching item (Cherry):
   - If the list still shows ALL the original items (nothing was narrowed away — the
     matching item is still present alongside items that do NOT match the query), the
     filter has not rendered yet -> flaky_timing. A wrong count here means "not updated
     yet", not "wrong result", so do not call it real_bug.
   - If the list WAS narrowed or changed but to the wrong contents — e.g. the matching
     item is the one now missing -> real_bug.
Do not make flaky_timing too broad — not every timeout or wrong assertion is timing. If
the signals are mixed, lower your confidence instead of forcing a strong answer."""

_PROMPT_TEMPLATE = """\
You are an expert at diagnosing Playwright end-to-end test failures. Classify the
failure below into exactly one category and explain why, citing actual evidence.

Categories:
{guide}

Base your reasoning on the concrete evidence — the failed selector/action, the
timeout or error message, the DOM page snapshot, console messages, network
requests, and the attached screenshot (if any). Quote specific values; do not give
generic guesses. If the failed selector times out while the page snapshot or
screenshot shows the intended element still present under a different id/text/
structure, that is stale_selector rather than real_bug.

Respond with a single JSON object and nothing else:
{{"category": "<one of: real_bug, stale_selector, flaky_timing, network_failure, race_condition>",
 "confidence": <float between 0 and 1>,
 "reasoning": "<concise explanation citing specific evidence>"}}

Evidence bundle (JSON):
{evidence}
"""


def _build_prompt(bundle: EvidenceBundle) -> str:
    return _PROMPT_TEMPLATE.format(
        guide=_CATEGORY_GUIDE,
        evidence=bundle.model_dump_json(indent=2),
    )


@contextlib.contextmanager
def _screenshot_tempfile(zip_path: str, bundle: EvidenceBundle):
    """Yield a path to the failure screenshot extracted from the trace, or None.

    Written with tempfile and removed afterwards so we don't leave stray images.
    """
    ref = bundle.screenshot
    if ref is None or not ref.present_in_zip:
        yield None
        return

    try:
        with zipfile.ZipFile(zip_path) as zf:
            data = zf.read(ref.resource_path)
    except (KeyError, OSError):
        yield None
        return

    suffix = os.path.splitext(ref.resource_path)[1] or ".img"
    fd, path = tempfile.mkstemp(prefix="trace_screenshot_", suffix=suffix)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        yield path
    finally:
        with contextlib.suppress(OSError):
            os.remove(path)


def _parse_result(raw: str) -> DiagnosisResult:
    text = raw.strip()
    if text.startswith("```"):  # tolerate ```json fences from the fallback path
        text = text.strip("`")
        text = text[text.find("{"):]
    data = json.loads(text)
    if "confidence" in data:
        try:
            data["confidence"] = max(0.0, min(1.0, float(data["confidence"])))
        except (TypeError, ValueError):
            pass
    return DiagnosisResult.model_validate(data)


def classify(bundle: EvidenceBundle, screenshot_path: str | None = None) -> DiagnosisResult:
    client = get_llm_client()
    prompt = _build_prompt(bundle)
    try:
        raw = client.generate(prompt, image=screenshot_path, json_object=True)
    except Exception as exc:  # provider may not support response_format
        print(
            f"[classifier] JSON mode (response_format) failed ({exc}); "
            "falling back to prompt+parse.",
            file=sys.stderr,
        )
        raw = client.generate(prompt, image=screenshot_path)
    return _parse_result(raw)


def classify_trace(zip_path: str) -> DiagnosisResult:
    bundle = build_evidence_bundle(zip_path)
    with _screenshot_tempfile(zip_path, bundle) as screenshot_path:
        return classify(bundle, screenshot_path)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("usage: python -m app.diagnosis.classifier <path-to-trace.zip>", file=sys.stderr)
        return 2
    zip_path = argv[0]
    if not zipfile.is_zipfile(zip_path):
        print(f"not a readable trace.zip: {zip_path}", file=sys.stderr)
        return 2
    load_dotenv()  # entry point only: load GITHUB_TOKEN / OPENROUTER_API_KEY from .env
    print(classify_trace(zip_path).model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
