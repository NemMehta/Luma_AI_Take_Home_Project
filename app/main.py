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

from app.diagnosis.classifier import classify_trace

load_dotenv()  # app entry point: load the provider key from .env at startup

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


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/diagnose")
def diagnose(file: UploadFile = File(...)):
    """Diagnose an uploaded trace.zip and return the structured diagnosis."""
    fd, tmp = tempfile.mkstemp(suffix=".zip", prefix="upload_")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(file.file.read())
        if not zipfile.is_zipfile(tmp):
            raise HTTPException(status_code=400, detail="uploaded file is not a valid trace.zip")
        return classify_trace(tmp)
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
        "diagnosis": classify_trace(str(zip_path)),
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
