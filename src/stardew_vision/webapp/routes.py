"""FastAPI route handlers for Stardew Vision."""

from __future__ import annotations

import base64
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from stardew_vision.serving.inference import run_agent_loop

router = APIRouter()

_STATIC_DIR = Path(__file__).parent / "static"
_MAX_FILE_BYTES = 20 * 1024 * 1024  # 20 MB


@router.get("/")
async def index() -> FileResponse:
    return FileResponse(str(_STATIC_DIR / "index.html"))


@router.post("/analyze")
async def analyze(file: UploadFile = File(...)) -> JSONResponse:
    """
    Accept a screenshot upload, run the Qwen agent loop, return JSON.

    Response shape:
        narration  (str)       — narration text assembled by Qwen
        has_errors (bool)      — True if unresolvable extraction failures
        fields     (dict|None) — extracted fields from the OCR tool
    """
    data = await file.read()

    if not data:
        raise HTTPException(status_code=400, detail="Empty file.")
    if len(data) > _MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 20 MB).")

    image_b64 = base64.b64encode(data).decode("utf-8")

    result = await run_agent_loop(image_b64)
    return JSONResponse(content=result)
