# ADR-011: Agent Loop Refinements — TTS Handoff, JSON Output, General Screen Routing

**Date**: 2026-04-05
**Status**: Accepted
**Amends**: ADR-009 (core architecture unchanged; three specific decisions revised)
**Deciders**: Project team

## Context

After implementing the initial agent loop (ADR-009) and discussing the design in more detail, three decisions in that ADR were found to be suboptimal:

1. **TTS as a tool call**: Qwen was expected to call `text_to_speech(text="...")` as its final turn. This adds an unnecessary round-trip to Qwen — the model has already produced the narration text; deciding to call TTS is not a reasoning step.

2. **System prompt hardcoded to Pierre's shop**: The original system prompt said "You will be shown a screenshot from Pierre's General Store." This prevents the loop from generalizing to new screen types as new tools are added.

3. **`debug=True` retry step**: The loop included a second OCR call with `debug=True` when the first call returned bad data. `debug=True` does not improve OCR accuracy — it only returns the raw OCR boxes alongside the structured fields. If OCR produces gibberish, the raw output is also gibberish. The step adds latency without reliably rescuing a failed extraction.

Additionally, with fine-tuning planned for Qwen, we can enforce a structured JSON output format, which enables clean programmatic handling by FastAPI without fragile text parsing.

## Decisions

### 1. TTS moves to FastAPI — not a Qwen tool call

MeloTTS is called directly by FastAPI immediately after Qwen returns its final response. Qwen has no `text_to_speech` tool available to it.

**Why**: TTS synthesis is infrastructure, not reasoning. Qwen's job is to produce narration text — deciding *when* to convert that to audio is a pipeline concern that FastAPI can handle deterministically. Removing TTS from the tool list also simplifies Qwen's action space and reduces the total turn count by one.

### 2. Qwen always returns structured JSON as its final response

When Qwen is done reasoning, it returns:

```json
{"narration": "...", "has_errors": false}
```

or on failure:

```json
{"narration": "There was an error parsing that screen...", "has_errors": true}
```

FastAPI parses this, checks `has_errors`, saves the screenshot if needed, then calls MeloTTS with `narration`.

**Why**: Fine-tuning Qwen on `(screenshot, full_conversation)` pairs allows us to reliably enforce JSON-only output. A fine-tuned model that always returns JSON is more robust than one that uses a sentinel prefix or structured tool args to signal the same information. This also makes `has_errors` detection fully deterministic on the FastAPI side.

### 3. System prompt generalized — Qwen routes to tools by recognition

The system prompt no longer names Pierre's shop. Instead it describes Qwen's role as a general Stardew Valley accessibility assistant that should call the appropriate extraction tool if it recognizes the screen, or return a specific JSON response if it does not:

- **Recognized screen**: Qwen calls the matching extraction tool (e.g. `crop_pierres_detail_panel`), receives OCR output, validates and corrects it, then returns final JSON.
- **Unrecognized screen**: Qwen returns immediately with:
  ```json
  {
    "narration": "I have not been trained to recognize that screen. If it is important to you please let Steve know.",
    "has_errors": false
  }
  ```

**Why**: As new screen types are added (TV dialog, inventory tooltip, crafting menu), the system prompt does not need to change — only new tool definitions and training examples are added. Qwen learns which screens match which tools from fine-tuning.

### 4. `debug=True` retry step removed from the loop

The two-pass OCR strategy (first call normal, retry with `debug=True` on failure) is removed. Qwen makes one OCR tool call per screen. If the result is bad, Qwen returns `has_errors: true` with whatever partial narration is available.

**Why**: `debug=True` returns raw OCR box text and positions alongside the structured fields — it does not re-run OCR with different settings or improved accuracy. If the OCR model produced garbled text, the raw output is equally garbled. The retry step adds latency without a meaningful chance of recovery.

**Future**: When OCR fails, Qwen should fire-and-forget to a separate async logging service with the raw OCR output and the screenshot, so the failure can be diagnosed and used as training data. This must not delay the audio response to the user. See TODO in `README.md`.

## Updated Agent Loop

```
User uploads screenshot
  |
  v
FastAPI POST /analyze  (port 8000)
  encodes image → base64
  |
  v
═══════════════════════════════════════════════════════════
  AGENT LOOP  (FastAPI runtime; Qwen reasoner)
═══════════════════════════════════════════════════════════

  TURN 1 — Screen Recognition + Extraction (or immediate fallback)
  ─────────────────────────────────────────────────────────────────
  FastAPI → Qwen: multimodal prompt {image, system prompt, tool list}

  Path A — Recognized screen:
    Qwen → FastAPI: tool_call crop_pierres_detail_panel()
    FastAPI injects image_b64, runs tool → returns OCR JSON to Qwen

  Path B — Unrecognized screen:
    Qwen → FastAPI: final JSON response (no tool call)
      {"narration": "I have not been trained to recognize that screen...",
       "has_errors": false}
    → skip to FastAPI handoff below

  TURN 2 — Validation + Correction (Path A only)
  ───────────────────────────────────────────────
  Qwen reviews OCR JSON:
    • Silently corrects recoverable typos using language knowledge
    • If critical fields missing or uncorrectable: sets has_errors=true
  Qwen → FastAPI: final JSON response
    {"narration": "The item is Parsnip Seeds...", "has_errors": false}
    or
    {"narration": "There was an error parsing that screen...", "has_errors": true}

  LOOP ENDS
  |
  v
FastAPI handoff:
  • has_errors=true → save screenshot to datasets/errors/, write structured log
  • Call MeloTTS directly with narration text → WAV bytes
  |
  v
FastAPI response (audio/wav, autoplay)
  |
  v
Browser <audio> element plays
```

**Maximum turns**: 2 for recognized screens (1 tool call + 1 final response). 1 for unrecognized screens (immediate JSON). Down from 4 in ADR-009.

## Updated Responsibility Table

| FastAPI (runtime) | Qwen (reasoner) |
|---|---|
| Holds base64 image for request lifetime | Decides whether screen is recognized |
| Executes tool calls, injects image_b64 | Calls appropriate extraction tool |
| Saves error screenshots to `datasets/errors/` | Silently corrects OCR typos |
| Logs failures to structured log | Signals `has_errors: true` when unresolvable |
| Calls MeloTTS with narration text | Returns structured JSON `{"narration", "has_errors"}` |
| Returns WAV to browser | — |

## Updated Tool Inventory

**`crop_pierres_detail_panel`** (Phase 1 — MVP)
- Input: `image_b64` injected by FastAPI at dispatch; `debug: bool = False` (debug mode retained in the tool but no longer called by the loop — available for manual debugging)
- Output: `{ "name", "description", "price_per_unit", "quantity_selected", "total_cost", "energy", "health" }`

**`crop_tv_dialog`** (Phase 2)
- Output: `{ "text": str }`

**`crop_inventory_tooltip`** (Phase 3)
- Output: `{ "name", "description", "sell_price" }`

`text_to_speech` is **not** in the tool list. It is called directly by FastAPI.

## Fine-Tuning Implications

Training examples for Qwen must include the full conversation:

**Recognized screen, clean OCR:**
```
[system prompt]
[user: image]
[assistant: tool_call crop_pierres_detail_panel()]
[tool: {OCR JSON}]
[assistant: {"narration": "The item is Parsnip Seeds...", "has_errors": false}]
```

**Recognized screen, bad OCR:**
```
[system prompt]
[user: image]
[assistant: tool_call crop_pierres_detail_panel()]
[tool: {partial/garbled OCR JSON}]
[assistant: {"narration": "There was an error parsing that screen...", "has_errors": true}]
```

**Unrecognized screen:**
```
[system prompt]
[user: image]
[assistant: {"narration": "I have not been trained to recognize that screen...", "has_errors": false}]
```

Fine-tuning on these patterns enforces both the JSON output format and the correct routing behavior.

## Alternatives Considered

| Option | Why not selected |
|---|---|
| **Keep TTS as a tool call** | Adds a full Qwen round-trip for a non-reasoning step; TTS synthesis is infrastructure, not intelligence |
| **Sentinel prefix for error detection** (e.g. `ERROR:`) | Fragile — Qwen may not follow it consistently pre-fine-tuning; JSON is cleaner and machine-readable |
| **FastAPI validates `fields` dict for has_errors** | Duplicates validation logic that Qwen is better positioned to do (it can detect semantic garbage, not just missing fields) |
| **Keep `debug=True` retry** | Does not improve OCR accuracy; adds ~3-5s latency per failure; async logging achieves the diagnostic goal without blocking the user |

## References

- [ADR-009](009-agent-tool-calling-architecture.md): Core agent/tool-calling architecture (partially superseded by this ADR)
- [ADR-003](003-tts-selection.md): TTS selection — MeloTTS-English
- `README.md`: TODOs section — async OCR error logging
