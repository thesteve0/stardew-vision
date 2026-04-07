"""TTS microservice for Stardew Vision.

Wraps Kokoro TTS (hexgrad/Kokoro-82M, Apache 2.0) to synthesize narration
text into WAV audio. The coordinator calls this service after Qwen assembles
the final narration, and returns the audio bytes directly to the browser.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from stardew_tts.synthesize import synthesize

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Warm up the Kokoro pipeline at startup to avoid first-request latency."""
    from stardew_tts.synthesize import _get_pipeline
    _get_pipeline()
    yield


app = FastAPI(
    title="Stardew TTS Tool",
    description="Synthesizes narration text to WAV audio using Kokoro TTS.",
    lifespan=lifespan,
)


class SynthesizeRequest(BaseModel):
    text: str
    voice: str = "af_heart"
    speed: float = 1.0


@app.post("/synthesize")
async def synthesize_endpoint(req: SynthesizeRequest) -> Response:
    """
    Synthesize text to audio.

    Returns raw WAV bytes with Content-Type: audio/wav.
    The browser <audio> element can play this directly.
    """
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="text must not be empty.")
    try:
        wav_bytes = synthesize(req.text, voice=req.voice, speed=req.speed)
        return Response(content=wav_bytes, media_type="audio/wav")
    except Exception as exc:
        logger.error("TTS synthesis failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
