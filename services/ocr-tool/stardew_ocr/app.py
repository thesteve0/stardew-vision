"""OCR extraction microservice for Stardew Vision.

Exposes a single endpoint that wraps the PaddleOCR-based extraction tool.
The coordinator calls this service rather than importing the tool directly,
keeping OCR dependencies isolated from the coordinator and TTS service.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from stardew_ocr.crop_pierres_detail_panel import (
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
