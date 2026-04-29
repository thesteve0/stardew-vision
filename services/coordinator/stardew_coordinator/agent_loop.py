"""Two-phase agent loop for the base Qwen2.5-VL model.

Architecture:

Phase 1 — Classification + Tool Call:
  Uses OpenAI tools= parameter (vLLM parses tool calls natively via hermes).
  Single VLM call → model calls extraction tool → dispatch to OCR service.
  If no tool call → return "unrecognized screen" narration.

Phase 2 — Correction / Narration:
  Separate VLM call WITHOUT tools.
  Pass OCR results → VLM corrects OCR errors, produces natural narration.

Phase 3 — TTS:
  Narration text → TTS service → WAV audio.

See ADR-009 for the agent architecture design.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import time
import uuid
from datetime import datetime
from pathlib import Path

import httpx
from openai import AsyncOpenAI

from stardew_coordinator.tool_definitions import TOOL_DEFINITIONS

logger = logging.getLogger(__name__)

MODEL_NAME = os.getenv("VLLM_MODEL", "Qwen/Qwen2.5-VL-7B-Instruct")
VLLM_BASE_URL = os.getenv("VLLM_BASE_URL", "http://localhost:8001/v1")
PIERRES_BUYING_TOOL_URL = os.getenv("PIERRES_BUYING_TOOL_URL", "http://localhost:8002")
TTS_TOOL_URL = os.getenv("TTS_TOOL_URL", "http://localhost:8003")
ERRORS_DIR = Path(os.getenv("ERRORS_DIR", "/app/datasets/errors"))

# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are an accessibility assistant for Stardew Valley players with vision impairments.

You will be shown a screenshot from Stardew Valley. Your job is to help the player \
understand what is on the screen by extracting and narrating the relevant information.

**CRITICAL: You MUST use the extraction tools when available. Do NOT just describe what you see visually.**

**If you see Pierre's General Store detail panel (item name, description, price):**
1. IMMEDIATELY call the crop_pierres_detail_panel tool with no arguments.
   - Do NOT pass image_b64 as an argument — the image is already available to the tool.
   - Do NOT try to read the text yourself — always use the tool for accurate OCR.

**If the screen is unrecognized or you have no tool for it:**
Say so briefly — do not attempt to read the screen yourself.\
"""

_NARRATION_SYSTEM_PROMPT = """\
You are an accessibility narrator for Stardew Valley. You have been given \
OCR-extracted data from a game screenshot. Your job is to:

1. Review the extracted fields and silently correct any obvious OCR errors \
(misspellings, garbled text, wrong numbers).
2. Produce a natural narration that a visually impaired player can listen \
to. Include ALL extracted fields and their full values — do not summarize \
or truncate any information.

Respond with ONLY the narration text — no JSON, no markup, no preamble.\
"""

# ---------------------------------------------------------------------------
# Tool endpoint mapping
# ---------------------------------------------------------------------------

_TOOL_ENDPOINTS = {
    "crop_pierres_detail_panel": "/extract/pierres-detail-panel",
}


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
# Tool dispatch via HTTP
# ---------------------------------------------------------------------------


async def _dispatch_tool(
    name: str,
    args: dict,
    image_b64: str,
    http: httpx.AsyncClient,
) -> dict:
    """Call the appropriate OCR tool microservice over HTTP."""
    endpoint = _TOOL_ENDPOINTS.get(name)
    if endpoint is None:
        return {"error": f"Unknown tool: {name}"}

    args["image_b64"] = image_b64  # inject — model never supplies this
    resp = await http.post(
        f"{PIERRES_BUYING_TOOL_URL}{endpoint}",
        json=args,
        timeout=120.0,
    )
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def run_agent_loop(image_b64: str) -> dict:
    """
    Run the two-phase agent loop for a single screenshot.

    Returns dict with keys:
        narration   (str)        — final text for the player
        has_errors  (bool)       — True if unresolvable extraction failures
        fields      (dict|None)  — extracted fields from the last successful OCR call
        audio_bytes (bytes|None) — WAV audio from TTS
    """
    start_time = time.perf_counter()
    logger.info("Starting agent loop: vLLM=%s model=%s", VLLM_BASE_URL, MODEL_NAME)

    client = AsyncOpenAI(base_url=VLLM_BASE_URL, api_key="EMPTY")
    mime = _detect_mime(image_b64)

    fields: dict | None = None
    narration: str = ""
    has_errors: bool = False
    audio_bytes: bytes | None = None

    # -----------------------------------------------------------------------
    # Phase 1 — Classification + Tool Call
    # -----------------------------------------------------------------------
    phase1_messages: list[dict] = [
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
                    "text": "Please extract and narrate the details from this screenshot.",
                },
            ],
        },
    ]

    vlm_start = time.perf_counter()
    response = await client.chat.completions.create(
        model=MODEL_NAME,
        messages=phase1_messages,
        tools=TOOL_DEFINITIONS,
        tool_choice="auto",
    )
    vlm_elapsed = time.perf_counter() - vlm_start

    choice = response.choices[0]
    msg = choice.message
    logger.info(
        "Phase 1 VLM response (%.2fs): finish_reason=%s has_tool_calls=%s",
        vlm_elapsed,
        choice.finish_reason,
        bool(msg.tool_calls),
    )

    if not msg.tool_calls:
        # Model didn't call a tool — unrecognized screen
        narration = (
            "I have not been trained to recognize that screen. "
            "If it is important to you, please let Steve know."
        )
        has_errors = False
    else:
        # Dispatch the first tool call
        tc = msg.tool_calls[0]
        name = tc.function.name
        try:
            args = json.loads(tc.function.arguments)
        except json.JSONDecodeError:
            args = {}

        logger.info("Phase 1 tool call: %s args=%s", name, args)

        async with httpx.AsyncClient() as http:
            tool_start = time.perf_counter()
            try:
                result = await _dispatch_tool(name, args, image_b64, http)
                tool_elapsed = time.perf_counter() - tool_start
                logger.info("OCR tool %s completed in %.2fs", name, tool_elapsed)

                if isinstance(result, dict) and "error" not in result:
                    fields = {k: v for k, v in result.items() if k != "ocr_raw"}
                else:
                    logger.warning("OCR tool returned error: %s", result)
                    has_errors = True

            except Exception as exc:
                tool_elapsed = time.perf_counter() - tool_start
                logger.warning("OCR tool %s failed after %.2fs: %s", name, tool_elapsed, exc)
                result = {"error": str(exc)}
                has_errors = True

        # -------------------------------------------------------------------
        # Phase 2 — Correction / Narration (separate VLM call, no tools)
        # -------------------------------------------------------------------
        if fields:
            phase2_messages: list[dict] = [
                {"role": "system", "content": _NARRATION_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Here are the OCR-extracted fields from a {name.replace('crop_', '').replace('_', ' ')} screen:\n\n"
                        f"{json.dumps(fields, indent=2)}\n\n"
                        "Please review, correct any OCR errors, and narrate this for the player."
                    ),
                },
            ]

            vlm2_start = time.perf_counter()
            response2 = await client.chat.completions.create(
                model=MODEL_NAME,
                messages=phase2_messages,
            )
            vlm2_elapsed = time.perf_counter() - vlm2_start

            narration_content = response2.choices[0].message.content or ""
            narration = narration_content.strip()
            logger.info("Phase 2 narration (%.2fs): %s", vlm2_elapsed, narration[:200])
        else:
            narration = (
                "There was an error extracting information from this screen. "
                "I have logged it for review."
            )

    # Save error screenshot if needed
    if has_errors:
        _save_error(image_b64, fields)

    # -----------------------------------------------------------------------
    # Phase 3 — TTS
    # -----------------------------------------------------------------------
    if narration:
        try:
            tts_start = time.perf_counter()
            async with httpx.AsyncClient() as http:
                resp = await http.post(
                    f"{TTS_TOOL_URL}/synthesize",
                    json={"text": narration, "speed": 1.0},
                    timeout=60.0,
                )
                resp.raise_for_status()
                audio_bytes = resp.content
                tts_elapsed = time.perf_counter() - tts_start
                logger.info("TTS synthesis succeeded in %.2fs (%d bytes)", tts_elapsed, len(audio_bytes))
        except Exception as exc:
            tts_elapsed = time.perf_counter() - tts_start
            logger.error("TTS synthesis failed after %.2fs: %s", tts_elapsed, exc, exc_info=True)
            audio_bytes = None

    total_elapsed = time.perf_counter() - start_time
    logger.info("TOTAL agent loop completed in %.2fs", total_elapsed)

    return {
        "narration": narration,
        "has_errors": has_errors,
        "fields": fields,
        "audio_bytes": audio_bytes,
    }
