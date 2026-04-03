"""
Tool registry and OpenAI function-calling definitions for Stardew Vision.

TOOL_REGISTRY maps tool names to callables used by the dispatch layer.
TOOL_DEFINITIONS is the list sent to the VLM in each chat.completions request.

Design: image_b64 is NOT exposed in TOOL_DEFINITIONS — FastAPI holds the
image for the request lifetime and injects it at dispatch time. Qwen never
needs to generate or pass the image bytes itself.
"""

from stardew_vision.tools.crop_pierres_detail_panel import (
    crop_pierres_detail_panel,
    crop_pierres_detail_panel_from_path,
)


# ---------------------------------------------------------------------------
# TTS stub — replaced when MeloTTS is wired in
# ---------------------------------------------------------------------------

def _text_to_speech_stub(text: str, has_errors: bool = False) -> dict:
    """Placeholder until src/stardew_vision/tts/synthesize.py is implemented."""
    return {"status": "ok", "text": text, "has_errors": has_errors}


# ---------------------------------------------------------------------------
# Tool registry — maps VLM tool names to production callables
# ---------------------------------------------------------------------------

TOOL_REGISTRY: dict = {
    "crop_pierres_detail_panel": crop_pierres_detail_panel,
    "text_to_speech": _text_to_speech_stub,
}

# ---------------------------------------------------------------------------
# OpenAI function-calling definitions — sent to Qwen in every loop request
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "crop_pierres_detail_panel",
            "description": (
                "Extract item details from Pierre's General Store detail panel using OCR. "
                "Returns name, description, price_per_unit, quantity_selected, total_cost, "
                "energy, and health. Use debug=true only when the initial extraction has "
                "failures you cannot correct with language knowledge alone."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "debug": {
                        "type": "boolean",
                        "description": (
                            "When true, also returns ocr_raw — a list of "
                            "{text, score, rel_y} dicts sorted by vertical position. "
                            "Use to diagnose unresolvable OCR failures."
                        ),
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "text_to_speech",
            "description": (
                "Synthesize your final narration to audio. Call this last, after "
                "extraction and any corrections are complete."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The narration text to speak aloud to the player.",
                    },
                    "has_errors": {
                        "type": "boolean",
                        "description": (
                            "Set to true if there were unresolvable extraction failures. "
                            "FastAPI will save the image for review."
                        ),
                    },
                },
                "required": ["text"],
            },
        },
    },
]
