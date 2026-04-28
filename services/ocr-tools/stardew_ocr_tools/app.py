"""Unified OCR extraction microservice for Stardew Vision.

Exposes endpoints for all screen-type extraction tools:
- Pierre's General Store detail panel
- TV dialog text
- Caught fish notification

The coordinator calls this service rather than importing the tools directly,
keeping OCR dependencies isolated from the coordinator and TTS services.
"""

from __future__ import annotations

# CRITICAL: Set PaddleX and HuggingFace environment variables BEFORE any imports
# PaddleX computes cache paths at module import time, so these MUST be set first
import os
os.environ.setdefault('PADDLEX_HOME', '/tmp/.paddlex')
os.environ.setdefault('PADDLE_PDX_CACHE_HOME', '/tmp/.paddlex')
os.environ.setdefault('PADDLEX_CACHE_DIR', '/tmp/.paddlex/cache')
os.environ.setdefault('PADDLE_HUB_HOME', '/tmp/.paddlex/hub')
os.environ.setdefault('PADDLE_OCR_BASE_DIR', '/tmp/.paddleocr')

# HuggingFace cache for PaddleX model downloads
os.environ.setdefault('HF_HOME', '/tmp/.huggingface')

# Disable MKLDNN/OneDNN optimizations to avoid CPU architecture incompatibilities
# in Kubernetes/OpenShift environments. See ADR-010 and LESSONS_LEARNED.md.
os.environ.setdefault('FLAGS_use_mkldnn', '0')
os.environ.setdefault('FLAGS_use_xdnn', '0')

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from stardew_ocr_tools.crop_pierres_detail_panel import (
    PanelNotFoundError,
    crop_pierres_detail_panel,
)
from stardew_ocr_tools.crop_tv_dialog import (
    DialogNotFoundError,
    crop_tv_dialog,
)
from stardew_ocr_tools.crop_caught_fish import (
    FishNotFoundError,
    crop_caught_fish,
)
from stardew_ocr_tools.common import load_ocr

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Loading PaddleOCR model at startup...")
    load_ocr()
    logger.info("PaddleOCR model loaded and ready.")
    yield


app = FastAPI(
    title="Stardew OCR Tools",
    description=(
        "Unified OCR extraction microservice for Stardew Vision. "
        "Handles Pierre's shop, TV dialog, and caught fish screen types."
    ),
    lifespan=lifespan,
)


class ExtractRequest(BaseModel):
    image_b64: str
    debug: bool = False


# ---------------------------------------------------------------------------
# Pierre's General Store
# ---------------------------------------------------------------------------


@app.post("/extract/pierres-detail-panel")
async def extract_pierres(req: ExtractRequest) -> JSONResponse:
    """Extract item details from Pierre's General Store detail panel."""
    try:
        result = crop_pierres_detail_panel(req.image_b64, debug=req.debug)
        return JSONResponse(content=result)
    except PanelNotFoundError as exc:
        logger.warning("Panel not found: %s", exc)
        return JSONResponse(content={"error": str(exc), "error_type": "PanelNotFoundError"})
    except Exception as exc:
        logger.error("Pierre's extraction failed: %s", exc, exc_info=True)
        return JSONResponse(
            content={"error": str(exc), "error_type": type(exc).__name__},
            status_code=500,
        )


# ---------------------------------------------------------------------------
# TV Dialog
# ---------------------------------------------------------------------------


@app.post("/extract/tv-dialog")
async def extract_tv_dialog(req: ExtractRequest) -> JSONResponse:
    """Extract dialog text from a TV screen screenshot."""
    try:
        result = crop_tv_dialog(req.image_b64, debug=req.debug)
        return JSONResponse(content=result)
    except DialogNotFoundError as exc:
        logger.warning("Dialog not found: %s", exc)
        return JSONResponse(content={"error": str(exc), "error_type": "DialogNotFoundError"})
    except Exception as exc:
        logger.error("TV dialog extraction failed: %s", exc, exc_info=True)
        return JSONResponse(
            content={"error": str(exc), "error_type": type(exc).__name__},
            status_code=500,
        )


# ---------------------------------------------------------------------------
# Caught Fish
# ---------------------------------------------------------------------------


@app.post("/extract/caught-fish")
async def extract_caught_fish(req: ExtractRequest) -> JSONResponse:
    """Extract fish info from a caught fish notification screenshot."""
    try:
        result = crop_caught_fish(req.image_b64, debug=req.debug)
        return JSONResponse(content=result)
    except FishNotFoundError as exc:
        logger.warning("Fish not found: %s", exc)
        return JSONResponse(content={"error": str(exc), "error_type": "FishNotFoundError"})
    except Exception as exc:
        logger.error("Caught fish extraction failed: %s", exc, exc_info=True)
        return JSONResponse(
            content={"error": str(exc), "error_type": type(exc).__name__},
            status_code=500,
        )


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
