"""FastAPI app exposing the trace-diagnosis pipeline.

A thin layer over the existing app.diagnosis code — no diagnosis logic is
reimplemented here. Corpus and benchmark data are read from the committed
app/demo_data/ directory, so the deployed app is self-contained and does not
depend on harness/ at runtime.
"""

from __future__ import annotations

import json
import os
import tempfile
import zipfile
from contextlib import suppress
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles
from openai import APIStatusError

from app.diagnosis.classifier import InsufficientEvidenceError, classify_trace
from app.diagnosis.ingest import NotATraceError

load_dotenv()  # app entry point: load the provider key from .env at startup

# Two distinct boundary-rejection messages (see POST /diagnose). Both surface as
# 422s the UI renders as an error, never as a diagnosis card.
_NOT_A_TRACE_MESSAGE = (
    "This does not look like a Playwright trace archive. A trace.zip contains "
    "Playwright trace event files, and this one does not."
)
_INSUFFICIENT_EVIDENCE_MESSAGE = (
    "This looks like a trace archive, but I could not pull enough usable "
    "evidence from it — no error context, DOM snapshot, actions, or network "
    "entries."
)

DEMO_DATA = Path(__file__).parent / "demo_data"
MANIFEST_PATH = DEMO_DATA / "manifest.json"
TRACES_DIR = DEMO_DATA / "traces"
BENCHMARK_PATH = DEMO_DATA / "benchmark_results.json"

app = FastAPI(title="Trace Diagnosis API")


def _load_manifest() -> dict:
    try:
        return json.loads(MANIFEST_PATH.read_text())
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="demo corpus manifest is missing")


def _classify_or_error(zip_path: str):
    """Run the classifier, turning provider HTTP errors into clean responses
    instead of raw 500s:

      - 401/403 (bad/invalid key) -> 502
      - 429 (rate limited)        -> 503, retry shortly

    Other errors propagate unchanged.
    """
    try:
        return classify_trace(zip_path)
    except APIStatusError as exc:
        if exc.status_code in (401, 403):
            raise HTTPException(
                status_code=502,
                detail="configured LLM provider rejected the request — check the API key.",
            ) from exc
        if exc.status_code == 429:
            raise HTTPException(
                status_code=503,
                detail="the LLM provider is rate limited, please try again shortly.",
            ) from exc
        raise


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/diagnose")
def diagnose(file: UploadFile = File(...)):
    """Diagnose an uploaded trace.zip and return the structured diagnosis.

    Rejects bad uploads at the boundary (422) instead of forcing the classifier
    to guess. Two cases, never reaching the LLM:
      - not a trace: a corrupt/non-zip file (BadZipFile) or a zip with no trace
        streams (NotATraceError).
      - insufficient evidence: a real trace archive that yields nothing usable.
    """
    fd, tmp = tempfile.mkstemp(suffix=".zip", prefix="upload_")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(file.file.read())
        try:
            return _classify_or_error(tmp)
        except (NotATraceError, zipfile.BadZipFile) as exc:
            raise HTTPException(status_code=422, detail=_NOT_A_TRACE_MESSAGE) from exc
        except InsufficientEvidenceError as exc:
            raise HTTPException(status_code=422, detail=_INSUFFICIENT_EVIDENCE_MESSAGE) from exc
    finally:
        with suppress(OSError):
            os.remove(tmp)


@app.get("/corpus")
def corpus() -> dict:
    """List the seeded (failing) corpus traces and their known labels."""
    return {"traces": _load_manifest().get("traces", [])}


@app.get("/corpus/{name}/diagnose")
def diagnose_corpus(name: str) -> dict:
    """Run diagnosis on one seeded corpus trace, alongside its known label."""
    traces = _load_manifest().get("traces", [])
    entry = next((t for t in traces if t.get("name") == name), None)
    if entry is None:
        known = ", ".join(t.get("name", "?") for t in traces)
        raise HTTPException(status_code=404, detail=f"unknown trace '{name}'. known: {known}")
    zip_path = TRACES_DIR / entry["file"]
    if not zip_path.is_file():
        raise HTTPException(status_code=500, detail=f"seeded trace file missing: {entry['file']}")
    return {
        "name": name,
        "true_label": entry.get("label"),
        "diagnosis": _classify_or_error(str(zip_path)),
    }


@app.get("/benchmark")
def benchmark() -> dict:
    """Return the saved benchmark accuracy and confusion matrix."""
    try:
        results = json.loads(BENCHMARK_PATH.read_text())
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="benchmark results are missing")
    return {
        "accuracy": results.get("accuracy"),
        "correct": results.get("correct"),
        "classified": results.get("classified"),
        "total_failing": results.get("total_failing"),
        "confusion_matrix": results.get("confusion_matrix"),
    }


# Serve the built React frontend (web/dist) as static files when it exists, so the
# whole thing runs as one service in production. Mounted AFTER all API routes, so
# /diagnose, /corpus and /benchmark still resolve to the API. In dev there is no
# build, so this is skipped and Vite serves the UI (proxying the API).
_FRONTEND_DIST = Path(__file__).parent.parent / "web" / "dist"
if _FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=_FRONTEND_DIST, html=True), name="frontend")
