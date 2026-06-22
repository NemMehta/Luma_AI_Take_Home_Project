"""Read a Playwright trace.zip and build an evidence bundle.

Parsing is pure Python (``zipfile`` + ``json``) — no Node, no `playwright` CLI.
A trace.zip holds newline-delimited JSON streams:

  - ``test.trace``       test-runner steps + the failure (`error` event)
  - ``N-trace.trace``    browser stream: console, DOM snapshots, screenshots
  - ``N-trace.network``  network requests/responses
  - ``resources/``       sha1-named blobs (screenshots, snapshot resources)

Run it:  python -m app.diagnosis.ingest <path-to-trace.zip>
"""

from __future__ import annotations

import json
import re
import sys
import zipfile

from app.diagnosis.schema import (
    Action,
    ConsoleMessage,
    DomSnapshot,
    EvidenceBundle,
    FailureInfo,
    NetworkRequest,
    ScreenshotRef,
    TraceMetadata,
)

_ANSI = re.compile(r"\x1b\[[0-9;]*m")
_SNAPSHOT_CAP = 4000


class NotATraceError(ValueError):
    """The file opened as a zip but carries no Playwright trace event stream
    (no ``test.trace`` / ``N-trace.trace``), so it is not a Playwright trace.zip
    — e.g. a zip of PDFs. Raised early, before any evidence is extracted."""


# Status returned by the evidence-sufficiency guard below. NOT a diagnosis
# category: it is deliberately kept out of DiagnosisCategory and the benchmark
# labels. It only tells the upload boundary to reject before the LLM is called.
INSUFFICIENT_EVIDENCE = "insufficient_evidence"
SUFFICIENT = "sufficient"


def _strip_ansi(text):
    return _ANSI.sub("", text) if isinstance(text, str) else text


def _read_ndjson(zf, name):
    try:
        raw = zf.read(name).decode("utf-8", "replace")
    except KeyError:
        return []
    events = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def _extract_metadata(test_events, lib_events):
    test_co = next((e for e in test_events if e.get("type") == "context-options"), {})
    lib_co = next((e for e in lib_events if e.get("type") == "context-options"), {})
    opts = lib_co.get("options") if isinstance(lib_co.get("options"), dict) else {}
    return TraceMetadata(
        playwright_version=test_co.get("playwrightVersion") or lib_co.get("playwrightVersion"),
        browser_name=(lib_co.get("browserName") or test_co.get("browserName")) or None,
        platform=test_co.get("platform") or lib_co.get("platform"),
        sdk_language=test_co.get("sdkLanguage") or lib_co.get("sdkLanguage"),
        test_timeout_ms=test_co.get("testTimeout"),
        wall_time_ms=test_co.get("wallTime") or lib_co.get("wallTime"),
        viewport=opts.get("viewport"),
        user_agent=opts.get("userAgent"),
    )


def _to_float(value):
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _extract_actions(events):
    afters = {e.get("callId"): e for e in events if e.get("type") == "after"}
    actions = []
    for e in events:
        if e.get("type") != "before":
            continue
        method = e.get("method")
        if method in ("hook", "fixture"):  # framework scaffolding, not test actions
            continue
        after = afters.get(e.get("callId"), {})
        params = e.get("params") or {}
        err = after.get("error")
        start, end = e.get("startTime"), after.get("endTime")
        duration = (end - start) if isinstance(start, (int, float)) and isinstance(end, (int, float)) else None
        cls = e.get("class")
        actions.append(
            Action(
                call_id=e.get("callId"),
                title=e.get("title"),
                api_name=f"{cls}.{method}" if cls and method else (cls or method),
                selector=params.get("selector"),
                url=params.get("url"),
                value=params.get("value"),
                timeout_ms=_to_float(params.get("timeout")),
                start_time=start,
                end_time=end,
                duration_ms=duration,
                failed=bool(err),
                error=_strip_ansi(err.get("message")) if isinstance(err, dict) else None,
            )
        )
    return actions


def _parse_call_log(message):
    out = []
    capturing = False
    for line in message.splitlines():
        if line.strip().lower().startswith("call log"):
            capturing = True
            continue
        if capturing and line.strip():
            out.append(line.strip().lstrip("-").strip())
    return out


def _extract_failure(events, actions):
    error_ev = next((e for e in events if e.get("type") == "error"), None)
    failed_action = next((a for a in actions if a.failed), None)
    if not error_ev and not failed_action:
        return None

    raw_message = (error_ev.get("message") if error_ev else None) or (
        failed_action.error if failed_action else ""
    ) or ""
    message = _strip_ansi(raw_message).strip()

    error_type = message.split(":", 1)[0].strip() if message else None
    if error_type and (" " in error_type or len(error_type) > 40):
        error_type = None  # only keep a clean leading token like "TimeoutError"

    stack = (error_ev.get("stack") if error_ev else None) or []
    src = stack[0] if isinstance(stack, list) and stack and isinstance(stack[0], dict) else {}

    return FailureInfo(
        error_type=error_type,
        message=message,
        call_log=_parse_call_log(message),
        failed_action_call_id=failed_action.call_id if failed_action else None,
        failed_action_title=failed_action.title if failed_action else None,
        failed_selector=failed_action.selector if failed_action else None,
        source_file=src.get("file"),
        source_line=src.get("line"),
        source_column=src.get("column"),
    )


def _format_location(loc):
    if not isinstance(loc, dict):
        return None
    url = loc.get("url") or loc.get("file")
    if url is None:
        return None
    line = loc.get("lineNumber", loc.get("line"))
    col = loc.get("columnNumber", loc.get("column"))
    parts = [str(url)] + [str(p) for p in (line, col) if p is not None]
    return ":".join(parts)


def _extract_console(lib_events):
    messages = []
    for e in lib_events:
        is_console = e.get("type") == "console" or (
            e.get("type") == "event" and e.get("method") == "console"
        )
        if not is_console:
            continue
        params = e.get("params") if isinstance(e.get("params"), dict) else e
        messages.append(
            ConsoleMessage(
                type=params.get("type") or params.get("messageType"),
                text=params.get("text") or params.get("message"),
                location=_format_location(params.get("location")),
            )
        )
    return messages


def _extract_network(network_events):
    requests = []
    for e in network_events:
        if e.get("type") != "resource-snapshot":
            continue
        snap = e.get("snapshot") or {}
        req = snap.get("request") or {}
        resp = snap.get("response") or {}
        status = resp.get("status") if isinstance(resp.get("status"), int) else None
        failure_text = snap.get("_failureText")
        failed = bool(failure_text) or (status is not None and (status == 0 or status >= 400))
        requests.append(
            NetworkRequest(
                method=req.get("method"),
                url=req.get("url"),
                status=status,
                status_text=resp.get("statusText"),
                failed=failed,
                failure_text=failure_text,
            )
        )
    return requests


def _read_resource(zf, sha1):
    try:
        return zf.read(f"resources/{sha1}").decode("utf-8", "replace")
    except KeyError:
        return None


def _extract_page_snapshot_section(markdown):
    if not isinstance(markdown, str):
        return None
    match = re.search(r"#\s*Page snapshot\s*\n+```[a-zA-Z]*\n(.*?)```", markdown, re.DOTALL)
    return match.group(1).strip() if match else None


def _truncate(text, cap):
    if text is None:
        return None, False
    if len(text) > cap:
        return text[:cap] + " …", True
    return text, False


def _extract_dom_snapshot(events, zf):
    # Playwright attaches an 'error-context' on failure: a markdown doc whose
    # '# Page snapshot' is an accessibility-tree view of the live DOM at the
    # moment of failure — a better signal than the incremental frame snapshots.
    # Present only on failing traces; passing traces have none.
    for e in events:
        if e.get("type") != "after":
            continue
        for att in e.get("attachments") or []:
            if att.get("name") == "error-context" and att.get("sha1"):
                body = _read_resource(zf, att["sha1"])
                if body is None:
                    return None
                text, truncated = _truncate(_extract_page_snapshot_section(body) or body, _SNAPSHOT_CAP)
                return DomSnapshot(
                    source=att.get("name"),
                    content_type=att.get("contentType"),
                    text=text,
                    truncated=truncated,
                )
    return None


def _extract_screenshot(lib_events, zip_names):
    frames = [e for e in lib_events if e.get("type") == "screencast-frame" and e.get("sha1")]
    if not frames:
        return None
    last = max(frames, key=lambda e: e.get("timestamp") or 0)
    resource_path = f"resources/{last['sha1']}"
    return ScreenshotRef(
        sha1=last["sha1"],
        resource_path=resource_path,
        width=last.get("width"),
        height=last.get("height"),
        timestamp=last.get("timestamp"),
        present_in_zip=resource_path in zip_names,
    )


def build_evidence_bundle(zip_path) -> EvidenceBundle:
    path = str(zip_path)
    # zipfile.ZipFile raises zipfile.BadZipFile here for a non-zip / corrupt
    # upload; we let it propagate so the caller can reject it cleanly rather
    # than building evidence from garbage.
    with zipfile.ZipFile(path) as zf:
        names = set(zf.namelist())

        # Validate this is actually a Playwright trace BEFORE extracting. A real
        # trace.zip always carries at least one trace event stream — test.trace
        # and/or N-trace.trace — and those *.trace files are exactly what we read
        # below to recover actions/failure/console (see action_source). If none
        # is present, the archive is not a Playwright trace, so reject it instead
        # of emitting an empty bundle that would force the classifier to guess.
        if not any(n.endswith(".trace") for n in names):
            raise NotATraceError(
                "archive has no Playwright trace event stream "
                "(expected test.trace or an N-trace.trace)"
            )

        test_events = _read_ndjson(zf, "test.trace")

        lib_events = []
        for name in sorted(n for n in names if n.endswith(".trace") and n != "test.trace"):
            lib_events.extend(_read_ndjson(zf, name))

        net_events = []
        for name in sorted(n for n in names if n.endswith(".network")):
            net_events.extend(_read_ndjson(zf, name))

        # Steps and failure come from the test stream; fall back to the browser
        # stream if a trace has no separate test.trace.
        action_source = test_events or lib_events
        actions = _extract_actions(action_source)
        failure = _extract_failure(action_source, actions)

        return EvidenceBundle(
            source_path=path,
            status="failed" if failure is not None else "passed",
            metadata=_extract_metadata(action_source, lib_events),
            actions=actions,
            failure=failure,
            console=_extract_console(lib_events),
            network=_extract_network(net_events),
            dom_snapshot=_extract_dom_snapshot(action_source, zf),
            screenshot=_extract_screenshot(lib_events, names),
        )


def _has_text(value) -> bool:
    """True only if a string field is present AND non-blank.

    Matches how the extractor leaves text fields: usually ``None`` when absent,
    but sometimes an empty/whitespace string (e.g. a DomSnapshot whose page
    snapshot section came back empty — see _extract_dom_snapshot). Both count as
    "no text".
    """
    return bool(value) and bool(str(value).strip())


def evidence_sufficiency(bundle: EvidenceBundle) -> str:
    """Gate, run right after extraction, that decides whether a bundle is worth
    sending to the LLM. Returns ``INSUFFICIENT_EVIDENCE`` or ``SUFFICIENT``.

    Insufficient means the bundle carries no usable signal AT ALL — ALL FOUR of
    these are empty (note the field types, matched exactly):

      - error context   ``failure``      -> None when absent
      - DOM snapshot     ``dom_snapshot`` -> None, or an object with empty ``.text``
      - actions          ``actions``      -> [] when absent (list, never None)
      - network entries  ``network``      -> [] when absent (list, never None)

    The check is an AND across all four on purpose: a perfectly valid trace may
    legitimately lack any one of them (a passing trace has no ``failure``; a
    UI-only test makes no network requests), so any single present signal makes
    the bundle sufficient. Only total emptiness — what a non-trace archive
    produces — is rejected.
    """
    has_error_context = bundle.failure is not None
    has_dom_snapshot = bundle.dom_snapshot is not None and _has_text(bundle.dom_snapshot.text)
    has_actions = bool(bundle.actions)      # list[Action]; [] when none
    has_network = bool(bundle.network)      # list[NetworkRequest]; [] when none
    if has_error_context or has_dom_snapshot or has_actions or has_network:
        return SUFFICIENT
    return INSUFFICIENT_EVIDENCE


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("usage: python -m app.diagnosis.ingest <path-to-trace.zip>", file=sys.stderr)
        return 2
    zip_path = argv[0]
    if not zipfile.is_zipfile(zip_path):
        print(f"not a readable trace.zip: {zip_path}", file=sys.stderr)
        return 2
    print(build_evidence_bundle(zip_path).model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
