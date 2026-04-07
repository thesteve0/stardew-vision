"""FastAPI route handlers for Stardew Vision coordinator."""

from __future__ import annotations

import base64
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response

from stardew_coordinator.agent_loop import run_agent_loop

router = APIRouter()

_STATIC_DIR = Path(__file__).parent / "static"
_MAX_FILE_BYTES = 20 * 1024 * 1024  # 20 MB


@router.get("/")
async def index() -> FileResponse:
    return FileResponse(str(_STATIC_DIR / "index.html"))


@router.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    """
    Accept a screenshot upload, run the Qwen agent loop, return audio.

    On success: returns audio/wav bytes — browser <audio> plays directly.
    On TTS failure or no audio: falls back to JSON with narration text.
    """
    data = await file.read()

    if not data:
        raise HTTPException(status_code=400, detail="Empty file.")
    if len(data) > _MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 20 MB).")

    image_b64 = base64.b64encode(data).decode("utf-8")
    result = await run_agent_loop(image_b64)

    audio = result.get("audio_bytes")
    if audio:
        return Response(content=audio, media_type="audio/wav")

    # Fallback: TTS was not called or failed — return narration as JSON
    return JSONResponse(content={
        "narration": result.get("narration", ""),
        "has_errors": result.get("has_errors", False),
        "fields": result.get("fields"),
    })
