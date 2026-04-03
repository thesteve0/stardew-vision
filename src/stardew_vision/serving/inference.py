"""
Multi-turn agent loop for Stardew Vision.

FastAPI is the agent runtime: it holds the base64 image for the request
lifetime, executes tool calls by dispatching to TOOL_REGISTRY, and manages
the conversation state.

Qwen2.5-VL (served by vLLM on port 8001) is the reasoner: it classifies the
screen, calls extraction tools, silently corrects OCR typos, signals
has_errors when failures are unresolvable, and calls text_to_speech last.

NOTE: The system prompt below is hard-coded for Pierre's shop (Phase 1 MVP).
It will be replaced with a screen-type classification prompt once the loop is
validated and fine-tuning begins.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path

from openai import AsyncOpenAI

from stardew_vision.tools import TOOL_DEFINITIONS, TOOL_REGISTRY

logger = logging.getLogger(__name__)

MODEL_NAME = os.getenv("VLLM_MODEL", "Qwen/Qwen2.5-VL-7B-Instruct")
VLLM_BASE_URL = os.getenv("VLLM_BASE_URL", "http://localhost:8001/v1")
ERRORS_DIR = Path(__file__).parents[3] / "datasets" / "errors"
MAX_TURNS = 6

# ---------------------------------------------------------------------------
# System prompt — Phase 1 Pierre's shop only
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are an accessibility assistant for Stardew Valley players with vision impairments.

You will be shown a screenshot from Pierre's General Store. Your job is to extract \
the item details from the shop panel and narrate them clearly to the player.

Follow this workflow:
1. Call crop_pierres_detail_panel() to extract the item details.
   IMPORTANT: Do NOT include an image_b64 argument — the image is already \
available to the tool.
2. Review the extracted fields. Silently correct obvious OCR errors using \
your language knowledge (for example, "Storter" → "Starter", \
"Pars nip" → "Parsnip").
3. If critical fields (name, price, quantity) are missing or uncorrectable, \
call crop_pierres_detail_panel(debug=true) to get raw OCR data and try again.
4. Call text_to_speech() with your complete narration. Set has_errors=true \
if there were unresolvable failures.

Your narration should cover: item name, description, price per unit in gold, \
quantity selected, and total cost.

If there were errors, begin with: "There was an error understanding part of \
this image. I have logged it. Here is what I was able to get: " and then \
describe whatever was successfully extracted.\
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _detect_mime(image_b64: str) -> str:
    """Return MIME type from the first bytes of the decoded image."""
    header = base64.b64decode(image_b64[:16] + "==")
    if header[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if header[:4] == b"\x89PNG":
        return "image/png"
    return "image/jpeg"


def _save_error(image_b64: str, fields: dict | None) -> None:
    """Persist the failing screenshot and log structured metadata."""
    ERRORS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    uid = uuid.uuid4().hex[:8]
    path = ERRORS_DIR / f"{ts}_{uid}.png"
    path.write_bytes(base64.b64decode(image_b64))
    logger.error(
        "extraction_error",
        extra={"image_path": str(path), "fields": fields},
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def run_agent_loop(image_b64: str) -> dict:
    """
    Run the multi-turn Qwen agent loop for a single screenshot.

    Parameters
    ----------
    image_b64:
        Base64-encoded PNG or JPEG screenshot.

    Returns
    -------
    dict with keys:
        narration  (str)       — final text for the player
        has_errors (bool)      — True if unresolvable extraction failures occurred
        fields     (dict|None) — extracted fields from the last successful tool call
    """
    client = AsyncOpenAI(base_url=VLLM_BASE_URL, api_key="EMPTY")
    mime = _detect_mime(image_b64)

    messages: list[dict] = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime};base64,{image_b64}"},
                },
                {
                    "type": "text",
                    "text": "Please extract and narrate the item details from this screenshot.",
                },
            ],
        },
    ]

    fields: dict | None = None
    narration: str = ""
    has_errors: bool = False

    for turn in range(MAX_TURNS):
        logger.debug("Agent turn %d/%d", turn + 1, MAX_TURNS)

        response = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            tools=TOOL_DEFINITIONS,
        )

        choice = response.choices[0]
        msg = choice.message
        messages.append(msg.model_dump(exclude_none=True))

        if choice.finish_reason == "tool_calls" and msg.tool_calls:
            for tc in msg.tool_calls:
                name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    args = {}

                logger.info("Tool call: %s args=%s", name, args)

                if name not in TOOL_REGISTRY:
                    result: dict = {"error": f"Unknown tool: {name}"}
                else:
                    try:
                        if name == "crop_pierres_detail_panel":
                            # Inject image — Qwen does not supply it
                            args["image_b64"] = image_b64

                        result = TOOL_REGISTRY[name](**args)

                        if name == "text_to_speech":
                            # Capture narration and error signal from TTS args
                            narration = args.get("text", "")
                            has_errors = bool(args.get("has_errors", False))
                        elif name == "crop_pierres_detail_panel" and isinstance(result, dict):
                            # Store fields; ocr_raw is for Qwen only, not caller
                            fields = {k: v for k, v in result.items() if k != "ocr_raw"}

                    except Exception as exc:
                        logger.warning("Tool %s raised: %s", name, exc)
                        result = {"error": str(exc)}

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(result),
                    }
                )

        elif choice.finish_reason == "stop":
            # Qwen finished. If text_to_speech was never called, fall back to
            # the final text response as the narration.
            if not narration and msg.content:
                narration = msg.content
            break

        else:
            logger.warning("Unexpected finish_reason: %s — stopping loop", choice.finish_reason)
            break

    if has_errors:
        _save_error(image_b64, fields)

    return {"narration": narration, "has_errors": has_errors, "fields": fields}
