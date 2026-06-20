"""Pydantic models for the evidence bundle extracted from a Playwright trace.

The bundle keeps only the signals useful to a later classifier — not the raw
trace. See ``ingest.py`` for how each field is populated.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class TraceMetadata(BaseModel):
    playwright_version: str | None = None
    browser_name: str | None = None
    platform: str | None = None
    sdk_language: str | None = None
    test_timeout_ms: int | None = None
    wall_time_ms: int | None = None
    viewport: dict | None = None
    user_agent: str | None = None


class Action(BaseModel):
    call_id: str | None = None
    title: str | None = None       # human-readable, e.g. Fill "cher" locator('#search-box')
    api_name: str | None = None    # class.method, e.g. Test.pw:api
    selector: str | None = None
    url: str | None = None
    value: str | None = None
    timeout_ms: float | None = None
    start_time: float | None = None
    end_time: float | None = None
    duration_ms: float | None = None
    failed: bool = False
    error: str | None = None       # cleaned error message if this action failed


class FailureInfo(BaseModel):
    error_type: str | None = None  # e.g. TimeoutError
    message: str                   # cleaned (ANSI-stripped)
    call_log: list[str] = Field(default_factory=list)
    failed_action_call_id: str | None = None
    failed_action_title: str | None = None
    failed_selector: str | None = None
    source_file: str | None = None
    source_line: int | None = None
    source_column: int | None = None


class ConsoleMessage(BaseModel):
    type: str | None = None        # log | warning | error | ...
    text: str | None = None
    location: str | None = None


class NetworkRequest(BaseModel):
    method: str | None = None
    url: str | None = None
    status: int | None = None
    status_text: str | None = None
    failed: bool = False
    failure_text: str | None = None


class DomSnapshot(BaseModel):
    source: str | None = None      # attachment it came from, e.g. "error-context"
    content_type: str | None = None
    text: str | None = None        # page snapshot (accessibility tree) at failure, truncated
    truncated: bool = False


class ScreenshotRef(BaseModel):
    sha1: str
    resource_path: str             # path inside the zip, e.g. resources/page@….jpeg
    width: int | None = None
    height: int | None = None
    timestamp: float | None = None
    present_in_zip: bool = False


class EvidenceBundle(BaseModel):
    source_path: str
    status: str                    # "passed" | "failed"
    metadata: TraceMetadata
    actions: list[Action] = Field(default_factory=list)
    failure: FailureInfo | None = None
    console: list[ConsoleMessage] = Field(default_factory=list)
    network: list[NetworkRequest] = Field(default_factory=list)
    dom_snapshot: DomSnapshot | None = None
    screenshot: ScreenshotRef | None = None
