# ADR-009: Agent/Tool-Calling Pipeline Architecture

**Date**: 2026-03-17
**Status**: Partially superseded by ADR-011 (2026-04-05)
**Supersedes**: ADR-002
**Deciders**: Project team

> **ADR-011 amends this ADR on three points**: (1) TTS is no longer a Qwen tool call — FastAPI calls MeloTTS directly after Qwen returns its final response. (2) Qwen always returns structured JSON `{"narration": "...", "has_errors": bool}` rather than signaling completion via a tool call — JSON output is enforced by fine-tuning. (3) The `debug=True` retry step is removed from the loop — see ADR-011 for rationale and the async logging TODO. The core architecture (FastAPI as runtime, Qwen as reasoner, OpenCV+PaddleOCR extraction tools, raw OpenAI client) is unchanged.

## Context

The original architecture (ADR-002) assumed the VLM would read a grid of loot box cells and output a flat JSON array of item names and quantities. After planning the MVP in detail, this approach has two problems:

1. **Wrong problem for the user**: The most actionable accessibility gap is not loot box grids but reading UI panels that appear during normal gameplay — Pierre's shop item details, TV program text, inventory tooltips. These panels are text-heavy and structured, not pixel-art grids.

2. **Annotation cost**: Labeling hundreds of grid cells at the item level is expensive. Fine-tuning a VLM to classify individual 16×16 sprites is harder than fine-tuning it to classify which screen type the user is looking at.

The pivot: **targeted panel reading via an agent/tool-calling pipeline**. The VLM classifies the screen type (orchestrator), then dispatches to a specialized extraction agent (tool) that crops the relevant region and runs OCR. GPU time is spent only on vision classification; text extraction runs on CPU.

## Decision

**Orchestrator VLM** (Qwen2.5-VL-7B-Instruct, LoRA fine-tuned, GPU) runs inside a **full agentic loop** managed by FastAPI. Qwen reasons across multiple turns — calling extraction tools, checking for failures, applying corrections, assembling narration, and delegating to TTS. **FastAPI is the agent runtime**: it holds state (the base64 image), executes tool calls Qwen requests, and feeds results back into the conversation. This is directly analogous to how Claude Code is the runtime that executes tools on behalf of the Claude LLM. **Specialized extraction agents** (OpenCV + OCR, CPU-only) handle region cropping and text extraction.

### Architecture

```
User uploads screenshot
  |
  v
FastAPI POST /analyze  (port 8000)
  | encodes image → base64, holds it for the duration of the request
  v
═══════════════════════════════════════════════════════════
  AGENT LOOP  (FastAPI is the runtime; Qwen is the reasoner)
═══════════════════════════════════════════════════════════

  TURN 1 — Classification + Extraction
  ─────────────────────────────────────
  FastAPI → Qwen:  multimodal prompt {image: <base64>, system prompt + tool list}
  Qwen → FastAPI:  tool_call crop_pierres_detail_panel(image_b64, debug=False)
  FastAPI runs tool → returns OCR JSON to Qwen

  TURN 2 — Quality Check
  ──────────────────────
  Qwen reasons over OCR result:
    • Detects and silently corrects recoverable typos (e.g. "Storter" → "Starter")
    • Detects unresolvable failures (e.g. price_per_unit=0, name garbled beyond repair)
  If failures detected:
    Qwen → FastAPI: tool_call crop_pierres_detail_panel(image_b64, debug=True)
    FastAPI runs tool → returns OCR JSON + ocr_raw (raw text boxes + scores + positions)
    Qwen reasons over raw boxes to attempt further correction

  TURN 3 — Narration Assembly
  ────────────────────────────
  Qwen assembles narration text from best available fields.
  If unresolvable failures remain, Qwen sets has_errors=True in its response.
  FastAPI reads has_errors:
    • Saves screenshot to datasets/errors/<timestamp>_<uuid>.png
    • Logs: image path, failure description, raw OCR output
  Narration text prefixed with error message when has_errors=True:
    "There was an error trying to understand that image. I have logged the error.
     In the meantime, here is the information I was able to get: [partial fields]"

  TURN 4 — Speech Synthesis
  ──────────────────────────
  Qwen → FastAPI: tool_call text_to_speech(text="...")
  FastAPI runs MeloTTS → returns WAV bytes

  LOOP ENDS — Qwen signals done
  |
  v
FastAPI response  (audio/wav, with autoplay header)
  |
  v
Browser <audio> element plays
```

### Tool Inventory

**`crop_pierres_detail_panel`** (Phase 1 — MVP)
- Input: `image_b64` (base64-encoded screenshot), `debug: bool = False`
- Action: OpenCV template matching to locate the right-column detail panel; 2× upscale; PaddleOCR text extraction
- Output (normal): `{ "name": str, "description": str, "price_per_unit": int, "quantity_selected": int, "total_cost": int, "energy": str, "health": str }`
- Output (debug=True): same fields + `"ocr_raw": [{"text": str, "score": float, "rel_y": float}, ...]`

**`text_to_speech`** *(removed as a tool — see ADR-011)*
- FastAPI now calls MeloTTS directly after Qwen returns its final JSON. TTS is no longer dispatched via tool call.

**`crop_tv_dialog`** (Phase 2)
- Input: `image_b64`
- Output: `{ "text": str }`

**`crop_inventory_tooltip`** (Phase 3)
- Input: `image_b64`
- Output: `{ "name": str, "description": str, "sell_price": int }`

### Image Transport Design

The orchestrator VLM must receive the image to classify the screen type, but in a distributed
deployment (e.g. OpenShift) the webapp pod, vLLM pod, and extraction service pod may run on
different nodes with no shared filesystem.

**How the image travels**:

1. FastAPI receives the upload and encodes the image to base64 in memory.
2. The base64 image is embedded in the multimodal prompt sent to Qwen (vLLM). Qwen sees it
   and emits a tool call JSON with only the tool name — no image in the parameters, because
   the model cannot reproduce the image and the dispatch layer already holds it.
3. FastAPI's dispatch layer intercepts the tool call, takes the base64 it already has from
   step 1, and calls the extraction service with it.
4. The extraction service (CPU pod) decodes base64 → numpy array and runs the pipeline.

This means the image crosses the network exactly twice: once to the VLM, once to the extraction
service. No shared filesystem or object storage is required for MVP.

**Tool input interface**:
- Production: `image_b64: str` (base64-encoded PNG/JPEG bytes)
- Local dev: convenience wrapper accepts a file path and converts to base64 internally

### FastAPI as Agent Runtime

FastAPI plays the same role Claude Code's shell process plays when running Claude: it is the **runtime** that actually executes tool calls, holds state between turns, and manages the loop. Qwen is the **reasoner** that decides what to do next based on what it sees.

Responsibilities split:

| FastAPI (runtime) | Qwen (reasoner) |
|-------------------|-----------------|
| Holds base64 image for request lifetime | Decides which tool to call and with what args |
| Executes tool calls and returns results | Detects typos and failures in OCR output |
| Writes error images to `datasets/errors/` | Applies silent corrections |
| Logs failures to structured log | Signals `has_errors=True` when failures are unresolvable |
| Runs MeloTTS via `text_to_speech` tool | Assembles narration text |
| Returns WAV to browser | Calls `text_to_speech` with final text |

### Error Handling Design

**What Qwen does**:
- Silently corrects recoverable typos (no log, no user notification)
- Sets `has_errors: True` only for unresolvable failures where data is missing or unrepairable
- Includes partial data in narration regardless of error state

**What FastAPI does when `has_errors=True`**:
- Saves original screenshot to `datasets/errors/<timestamp>_<uuid>.png`
- Writes structured log entry: `{ "image_path": ..., "error": ..., "ocr_raw": ... }`
- Passes Qwen's assembled narration (with error prefix) to `text_to_speech`

**What the user hears**: "There was an error trying to understand that image. I have logged the error. In the meantime, here is the information I was able to get: [partial fields]"

### Orchestrator Fine-Tuning Target

The VLM is fine-tuned to perform **screen classification + multi-turn agentic reasoning**. Training examples are `(screenshot, full_conversation_with_tool_calls)` tuples — the VLM learns to look at a screenshot, call the right extraction tool, evaluate the result, apply corrections, and assemble a narration. It does not need to perform OCR itself.

This is a much simpler fine-tuning target than cell-level item recognition.

### Orchestrator Prompting

The system prompt passes the tool list and instructs Qwen on the full agentic loop:

```
You are an accessibility assistant for Stardew Valley. Your job is to help visually
impaired players understand what is on their screen.

Given a screenshot:
1. Call the appropriate extraction tool to get the panel contents.
2. Review the result. Silently correct obvious OCR typos using your language knowledge
   (e.g. "Storter" → "Starter Seeds"). Do NOT log or mention corrections to the user.
3. If critical fields are missing or unrepairable (price_per_unit=0, name is garbled
   beyond recognition), call the extraction tool again with debug=True and examine
   the raw OCR output. If still unresolvable, set has_errors=True.
4. Assemble a natural-language narration of the panel contents from the best available
   data. If has_errors=True, prefix the narration with the standard error message.
5. Call text_to_speech with your final narration text.

Do not attempt to read text from the image yourself. Use the extraction tools.
```

## Alternatives Considered

| Option | Why not selected |
|--------|-----------------|
| **VLM reads full grid cells (ADR-002 original)** | Wrong primary user need; high annotation cost; 16×16 sprite recognition is harder than screen type classification |
| **VLM does both classification and text extraction** | GPU-intensive for simple OCR; harder to debug (wrong answer could be vision or text error); OCR is CPU-sufficient for clean rendered text |
| **OCR-only (no VLM)** | Cannot generalize to new screen types without hardcoded logic; VLM handles screen type variability naturally |
| **Separate classifier + OCR (no tool calling)** | Tool-calling format makes the architecture cleaner, more extensible, and directly demonstrates the agent pattern for the conference talk |
| **Single tool call (no agentic loop)** | No mechanism for quality checking, typo correction, or graceful degradation; forces all error handling into the extraction tool itself; removes the opportunity to demonstrate real agentic reasoning |
| **Agent framework (Smolagents, LangGraph, etc.)** | The loop is simple enough that raw OpenAI client gives full control with less abstraction; avoids a dependency whose abstractions may conflict with vLLM's tool-calling implementation |

## Rationale

**GPU stays free for vision**: Screen classification and reasoning require vision; text extraction does not. Keeping OCR on CPU leaves GPU headroom for the orchestrator and avoids unnecessary GPU memory pressure.

**FastAPI as runtime is the right mental model**: FastAPI is not just a web server — it is the agent loop. Framing it this way makes the architecture legible: Qwen reasons, FastAPI acts. This maps directly to how Claude Code works (shell runs tools, LLM reasons) and gives the conference talk a clear teaching moment.

**Agentic loop enables quality checking**: A single-shot architecture has no mechanism to detect or correct OCR failures. The loop lets Qwen evaluate its own tool's output and request debug information when needed — a more robust and realistic production design.

**Separation of concerns**: Classification failures and extraction failures are independently debuggable. If the wrong tool is called, the VLM is at fault. If field values are wrong, the OCR agent is at fault. If Qwen fails to detect an obvious typo, the system prompt or fine-tuning is at fault.

**Scales to new screen types by adding tools**: Adding Phase 2 (TV dialog) requires writing one new extraction function — the orchestrator learns to call it by adding training examples. No architectural changes needed.

**Error logging creates improvement data**: Every unresolvable failure writes the image and raw OCR to `datasets/errors/`. This becomes future training data — the failure cases are exactly the images the model most needs to learn from.

**Strong talk narrative**: The full agentic loop — tool call, quality check, correction, re-try, graceful degradation, TTS — demonstrates the complete agent pattern in a concrete, relatable use case. It shows audiences what a real production agent looks like, not a toy one-shot demo.

## Consequences

**Gets easier**:
- Fine-tuning target is multi-turn reasoning, which is still simpler than item recognition
- Extraction agents (OpenCV + OCR) are deterministic and testable in isolation
- New screen types added by writing one function + training examples
- GPU/CPU separation makes resource management straightforward
- No synthetic grid data generation needed for MVP
- Error cases automatically log themselves as future training data

**Gets harder**:
- Multi-turn conversation management adds complexity vs. single-shot dispatch
- OpenCV template matching is brittle to UI skin changes (acceptable for MVP vanilla Stardew)
- Need screen-type labeled screenshots for orchestrator training (different from item-labeled data)
- Fine-tuning training examples must capture the full conversation, not just the first tool call

**We are committing to**:
- Qwen2.5-VL-7B as the orchestrator (agentic reasoner + tool dispatcher)
- FastAPI as the agent runtime (loop management, tool execution, state, error logging)
- OpenCV + PaddleOCR (PP-OCRv5) for CPU-side extraction (see ADR-010)
- MeloTTS called directly by FastAPI (not a Qwen tool call — see ADR-011)
- Pierre's shop detail panel as the MVP screen type
- Raw OpenAI client (no agent framework) for the loop — full control, no abstraction layer
- OpenAI function-calling format for tool dispatch (compatible with vLLM serving)
- SmolVLM2 comparison question: "can a 2.2B model handle multi-turn agentic reasoning over OCR output?"

## Evaluation Metrics

| Metric | Target | Description |
|--------|--------|-------------|
| Screen classification accuracy | >= 95% | % of screenshots where correct extraction tool is called on turn 1 |
| Field extraction accuracy | >= 90% | % of extracted fields matching ground truth after Qwen correction |
| Correction accuracy | >= 80% | % of detectable OCR typos that Qwen silently corrects |
| False positive error rate | <= 5% | % of successful extractions incorrectly flagged as `has_errors=True` |
| End-to-end narration quality | Human eval | Spot-check: does the audio correctly describe the panel? |
| JSON validity rate | >= 99% | % of tool call responses producing valid JSON |
| Loop turn count | <= 4 median | Median number of turns before Qwen signals done |

## References

- [ADR-001](001-vlm-selection.md): VLM selection — Qwen2.5-VL-7B role updated to orchestrator
- [ADR-002](002-vlm-role-architecture.md): Superseded by this ADR
- [ADR-005](005-serving-strategy.md): Serving strategy — tool-calling via OpenAI-compatible API
- [ADR-010](010-screen-region-extraction.md): Extraction layer details
- `docs/plan.md`: Implementation sequence and phases
