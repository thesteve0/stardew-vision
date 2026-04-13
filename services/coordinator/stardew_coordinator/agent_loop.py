"""Multi-turn agent loop for Stardew Vision coordinator.

FastAPI is the agent runtime: it holds the base64 image for the request
lifetime, dispatches tool calls over HTTP to the OCR microservice, manages
the conversation state, and calls TTS directly after Qwen returns final JSON.

Qwen2.5-VL (served by vLLM on port 8001) is the reasoner: it classifies the
screen, calls extraction tools if recognized, silently corrects OCR typos,
and returns structured JSON {"narration": "...", "has_errors": bool}.

Tool dispatch is HTTP:
  OCR tool:  POST {OCR_TOOL_URL}/extract/pierres-detail-panel
  TTS tool:  POST {TTS_TOOL_URL}/synthesize  → called by FastAPI, not Qwen

See ADR-011 for the full design.
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
OCR_TOOL_URL = os.getenv("OCR_TOOL_URL", "http://localhost:8002")
TTS_TOOL_URL = os.getenv("TTS_TOOL_URL", "http://localhost:8003")
# Error screenshots directory (mounted PVC in container, local path in dev)
ERRORS_DIR = Path(os.getenv("ERRORS_DIR", "/app/datasets/errors"))
MAX_TURNS = 6

# ---------------------------------------------------------------------------
# System prompt — generalized for any Stardew Valley screen
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
2. After receiving the OCR result, review the extracted fields. Silently correct obvious \
OCR errors using your language knowledge (e.g., "Storter" → "Starter", "Pars nip" → "Parsnip").
3. Then return a JSON response with your narration based on the corrected fields:
   {"narration": "The item is Parsnip Seeds. Description: Plant in spring, takes 4 days. \
Price per unit: 20 gold. You have 5 selected for a total of 100 gold.", "has_errors": false}

**If the screen is unrecognized or you have no tool for it:**
Return immediately:
{"narration": "I have not been trained to recognize that screen. If it is important to you, \
please let Steve know.", "has_errors": false}

**On extraction failure:**
If critical fields are missing or uncorrectable after reviewing the OCR result, return:
{"narration": "There was an error understanding part of this image. I have logged it. \
Here is what I was able to get: [partial info]", "has_errors": true}

Your final response must ALWAYS be valid JSON with "narration" and "has_errors" keys.\
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
# Tool dispatch via HTTP
# ---------------------------------------------------------------------------


async def _dispatch_tool(
    name: str,
    args: dict,
    image_b64: str,
    http: httpx.AsyncClient,
) -> dict:
    """
    Call the appropriate OCR tool microservice over HTTP.

    Returns
    -------
    dict
        JSON result returned to Qwen as the tool response.
    """
    if name == "crop_pierres_detail_panel":
        args["image_b64"] = image_b64  # inject — Qwen never supplies this
        resp = await http.post(
            f"{OCR_TOOL_URL}/extract/pierres-detail-panel",
            json=args,
            timeout=120.0,  # First request loads models into memory, can take 60+ seconds
        )
        resp.raise_for_status()
        return resp.json()

    return {"error": f"Unknown tool: {name}"}


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
        narration   (str)        — final text for the player
        has_errors  (bool)       — True if unresolvable extraction failures
        fields      (dict|None)  — extracted fields from the last successful OCR call
        audio_bytes (bytes|None) — WAV audio from TTS
    """
    start_time = time.perf_counter()
    logger.info("⏱️  Starting agent loop: vLLM=%s model=%s", VLLM_BASE_URL, MODEL_NAME)
    logger.info("Available tools: %s", [t["function"]["name"] for t in TOOL_DEFINITIONS])

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
                    "text": "Please extract and narrate the details from this screenshot.",
                },
            ],
        },
    ]

    fields: dict | None = None
    narration: str = ""
    has_errors: bool = False
    audio_bytes: bytes | None = None

    async with httpx.AsyncClient() as http:
        for turn in range(MAX_TURNS):
            turn_start = time.perf_counter()
            logger.info("=== Agent turn %d/%d ===", turn + 1, MAX_TURNS)
            logger.debug(
                "Sending to vLLM: model=%s, tools=%s, tool_choice=auto, messages=%d",
                MODEL_NAME,
                [t["function"]["name"] for t in TOOL_DEFINITIONS],
                len(messages)
            )

            vlm_start = time.perf_counter()
            response = await client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                tools=TOOL_DEFINITIONS,
                tool_choice="auto",
            )
            vlm_elapsed = time.perf_counter() - vlm_start

            choice = response.choices[0]
            msg = choice.message
            logger.info(
                "⏱️  VLM response (%.2fs): finish_reason=%s has_tool_calls=%s num_tool_calls=%d content_preview=%s",
                vlm_elapsed,
                choice.finish_reason,
                bool(msg.tool_calls),
                len(msg.tool_calls) if msg.tool_calls else 0,
                (msg.content[:100] + "...") if msg.content and len(msg.content) > 100 else msg.content,
            )
            if msg.tool_calls:
                for tc in msg.tool_calls:
                    logger.info("Tool call detected: name=%s id=%s args=%s",
                               tc.function.name, tc.id, tc.function.arguments)

            messages.append(msg.model_dump(exclude_none=True))

            # Check for tool calls (vLLM bug: finish_reason may be "stop" even with tool_calls)
            if msg.tool_calls:
                for tc in msg.tool_calls:
                    name = tc.function.name
                    try:
                        args = json.loads(tc.function.arguments)
                    except json.JSONDecodeError:
                        args = {}

                    logger.info("Tool call: %s args=%s", name, args)

                    tool_start = time.perf_counter()
                    try:
                        result = await _dispatch_tool(name, args, image_b64, http)
                        tool_elapsed = time.perf_counter() - tool_start
                        logger.info("⏱️  Tool %s completed in %.2fs", name, tool_elapsed)

                        if name == "crop_pierres_detail_panel" and isinstance(result, dict):
                            fields = {k: v for k, v in result.items() if k != "ocr_raw"}

                    except Exception as exc:
                        tool_elapsed = time.perf_counter() - tool_start
                        logger.warning("⏱️  Tool %s failed after %.2fs: %s", name, tool_elapsed, exc)
                        result = {"error": str(exc)}

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(result),
                    })

            elif choice.finish_reason == "stop":
                # Qwen has finished — parse its JSON response
                if msg.content:
                    try:
                        response_json = json.loads(msg.content)
                        narration = response_json.get("narration", msg.content)
                        has_errors = bool(response_json.get("has_errors", False))
                    except json.JSONDecodeError:
                        logger.warning("Qwen returned non-JSON content: %r", msg.content)
                        narration = msg.content
                        has_errors = False
                turn_elapsed = time.perf_counter() - turn_start
                logger.info("⏱️  Turn %d completed in %.2fs (loop ending, finish_reason=stop)", turn + 1, turn_elapsed)
                break

            else:
                turn_elapsed = time.perf_counter() - turn_start
                logger.warning(
                    "⏱️  Turn %d completed in %.2fs - Unexpected finish_reason: %s — stopping loop",
                    turn + 1, turn_elapsed, choice.finish_reason
                )
                break

            turn_elapsed = time.perf_counter() - turn_start
            logger.info("⏱️  Turn %d completed in %.2fs (continuing to next turn)", turn + 1, turn_elapsed)

    # Save error screenshot if needed
    if has_errors:
        _save_error(image_b64, fields)

    # Call TTS directly (not a tool call)
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
                logger.info("⏱️  TTS synthesis succeeded in %.2fs (%d bytes)", tts_elapsed, len(audio_bytes))
        except Exception as exc:
            tts_elapsed = time.perf_counter() - tts_start
            logger.error("⏱️  TTS synthesis failed after %.2fs: %s", tts_elapsed, exc, exc_info=True)
            audio_bytes = None

    total_elapsed = time.perf_counter() - start_time
    logger.info("⏱️  TOTAL agent loop completed in %.2fs", total_elapsed)

    return {
        "narration": narration,
        "has_errors": has_errors,
        "fields": fields,
        "audio_bytes": audio_bytes,
    }
