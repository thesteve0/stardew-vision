"""FastAPI application entrypoint for Stardew Vision."""

import logging
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

# Uvicorn only configures its own loggers; attach a handler directly so
# stardew_vision.* output always reaches the terminal.
_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s — %(message)s"))
_sv_logger = logging.getLogger("stardew_coordinator")
_sv_logger.addHandler(_handler)
_sv_logger.setLevel(logging.DEBUG)
_sv_logger.propagate = False

from stardew_coordinator import routes

_STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(
    title="Stardew Vision",
    description="Accessibility tool for Stardew Valley — upload a screenshot, hear the UI panel narrated.",
)

app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")
app.include_router(routes.router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
