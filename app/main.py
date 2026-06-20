"""Minimal FastAPI app for the take-home. Phase 0: health check only."""

from fastapi import FastAPI

app = FastAPI(title="Luma Take-Home")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
