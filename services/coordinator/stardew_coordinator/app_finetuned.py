"""FastAPI application entrypoint with switchable agent loop.

Reads the AGENT_MODE environment variable to select between:
  - "base" (default): uses the original agent_loop.run_agent_loop
  - "finetuned": uses agent_loop_finetuned.run_agent_loop_finetuned

This allows the same coordinator container image to serve either model
by simply changing the ConfigMap/env vars.
"""

import base64
import logging
import os
import sys
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

# Configure logging before other imports
_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s — %(message)s"))
_sv_logger = logging.getLogger("stardew_coordinator")
_sv_logger.addHandler(_handler)
_sv_logger.setLevel(logging.DEBUG)
_sv_logger.propagate = False

AGENT_MODE = os.getenv("AGENT_MODE", "base")

if AGENT_MODE == "finetuned":
    from stardew_coordinator.agent_loop_finetuned import run_agent_loop_finetuned as _run_agent_loop
else:
    from stardew_coordinator.agent_loop import run_agent_loop as _run_agent_loop

_STATIC_DIR = Path(__file__).parent / "static"
_MAX_FILE_BYTES = 20 * 1024 * 1024  # 20 MB

app = FastAPI(
    title="Stardew Vision",
    description="Accessibility tool for Stardew Valley — upload a screenshot, hear the UI panel narrated.",
)

app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(str(_STATIC_DIR / "index.html"))


@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    """Accept a screenshot upload, run the agent loop, return audio."""
    data = await file.read()

    if not data:
        raise HTTPException(status_code=400, detail="Empty file.")
    if len(data) > _MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 20 MB).")

    image_b64 = base64.b64encode(data).decode("utf-8")
    result = await _run_agent_loop(image_b64)

    audio = result.get("audio_bytes")
    if audio:
        return Response(content=audio, media_type="audio/wav")

    return JSONResponse(content={
        "narration": result.get("narration", ""),
        "has_errors": result.get("has_errors", False),
        "fields": result.get("fields"),
    })


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "agent_mode": AGENT_MODE}
