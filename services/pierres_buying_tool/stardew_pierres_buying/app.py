"""OCR extraction microservice for Stardew Vision.

Exposes a single endpoint that wraps the PaddleOCR-based extraction tool.
The coordinator calls this service rather than importing the tool directly,
keeping OCR dependencies isolated from the coordinator and TTS service.
"""

from __future__ import annotations

# CRITICAL: Set PaddleX and HuggingFace environment variables BEFORE any imports
# PaddleX computes cache paths at module import time, so these MUST be set first
import os
os.environ.setdefault('PADDLEX_HOME', '/tmp/.paddlex')
os.environ.setdefault('PADDLE_PDX_CACHE_HOME', '/tmp/.paddlex')  # Alternative var name
os.environ.setdefault('PADDLEX_CACHE_DIR', '/tmp/.paddlex/cache')
os.environ.setdefault('PADDLE_HUB_HOME', '/tmp/.paddlex/hub')
os.environ.setdefault('PADDLE_OCR_BASE_DIR', '/tmp/.paddleocr')

# HuggingFace cache for PaddleX model downloads
# Without this, PaddleX tries to write to /.cache/huggingface which fails in OpenShift
os.environ.setdefault('HF_HOME', '/tmp/.huggingface')

# Disable MKLDNN/OneDNN optimizations to avoid CPU architecture incompatibilities
# in Kubernetes/OpenShift environments. MKLDNN requires specific CPU instruction sets
# (AVX, AVX2) that may not be available on all cluster nodes, causing SIGTERM crashes.
# See: https://github.com/PaddlePaddle/PaddleOCR/issues/16789
os.environ.setdefault('FLAGS_use_mkldnn', '0')
os.environ.setdefault('FLAGS_use_xdnn', '0')

import logging

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from stardew_pierres_buying.crop_pierres_detail_panel import (
    PanelNotFoundError,
    crop_pierres_detail_panel,
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Stardew OCR Tool",
    description="Extracts item details from Stardew Valley UI panels via template matching + PaddleOCR.",
)


class ExtractRequest(BaseModel):
    image_b64: str
    debug: bool = False


@app.post("/extract/pierres-detail-panel")
async def extract(req: ExtractRequest) -> JSONResponse:
    """
    Extract item details from Pierre's General Store detail panel.

    Returns JSON with name, description, price_per_unit, quantity_selected,
    total_cost, energy, health. If debug=true, also includes ocr_raw.
    On panel-not-found, returns a JSON error dict (not a 4xx) so the
    coordinator can relay the failure to Qwen as a tool result.
    """
    try:
        result = crop_pierres_detail_panel(req.image_b64, debug=req.debug)
        return JSONResponse(content=result)
    except PanelNotFoundError as exc:
        logger.warning("Panel not found: %s", exc)
        return JSONResponse(content={"error": str(exc), "error_type": "PanelNotFoundError"})
    except Exception as exc:
        logger.error("Extraction failed: %s", exc, exc_info=True)
        return JSONResponse(
            content={"error": str(exc), "error_type": type(exc).__name__},
            status_code=500,
        )


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
