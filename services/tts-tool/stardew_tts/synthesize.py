"""Kokoro TTS wrapper for Stardew Vision.

Lazy-loads the Kokoro pipeline on first call so the service starts fast
even before the model weights are cached locally.

Kokoro downloads ~165 MB of weights from HuggingFace on first use.
After that they are cached in HF_HOME and subsequent starts are instant.
"""

from __future__ import annotations

import io
import logging

import numpy as np
import soundfile as sf

logger = logging.getLogger(__name__)

_pipeline = None
_VOICE = "af_heart"       # American English female — clear and natural
_SAMPLE_RATE = 24000      # Kokoro outputs 24 kHz


def _get_pipeline():
    global _pipeline
    if _pipeline is None:
        logger.info("Loading Kokoro TTS pipeline (first-time model download may take a moment)...")
        from kokoro import KPipeline
        # CPU is ~15x faster than AMD gfx1151 GPU for this 82M-param model —
        # GPU dispatch overhead dominates at this scale.
        _pipeline = KPipeline(lang_code="a", device="cpu")  # 'a' = American English
        logger.info("Kokoro pipeline ready.")
    return _pipeline


def synthesize(text: str, voice: str = _VOICE, speed: float = 1.0) -> bytes:
    """
    Synthesize text to WAV bytes using Kokoro TTS.

    Parameters
    ----------
    text:
        The narration text to speak aloud.
    voice:
        Kokoro voice ID. Defaults to 'af_heart' (American English female).
        Other options: 'af_bella', 'am_adam', 'af_sarah', 'am_michael', etc.
    speed:
        Speech rate multiplier. 1.0 = normal, 0.85 = slightly slower (good
        for accessibility).

    Returns
    -------
    bytes
        Raw WAV file bytes suitable for returning as audio/wav HTTP response.
    """
    pipeline = _get_pipeline()

    chunks: list[np.ndarray] = []
    for _, _, audio in pipeline(text, voice=voice, speed=speed):
        if audio is not None and len(audio) > 0:
            chunks.append(audio)

    if not chunks:
        raise RuntimeError("Kokoro produced no audio output for the given text.")

    full_audio = np.concatenate(chunks)

    buf = io.BytesIO()
    sf.write(buf, full_audio, _SAMPLE_RATE, format="WAV")
    buf.seek(0)
    return buf.read()
