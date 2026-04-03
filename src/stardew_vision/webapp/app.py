"""FastAPI application entrypoint for Stardew Vision."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from stardew_vision.webapp import routes

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
