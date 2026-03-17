# ADR-009: Agent/Tool-Calling Pipeline Architecture

**Date**: 2026-03-17
**Status**: Accepted
**Supersedes**: ADR-002
**Deciders**: Project team

## Context

The original architecture (ADR-002) assumed the VLM would read a grid of loot box cells and output a flat JSON array of item names and quantities. After planning the MVP in detail, this approach has two problems:

1. **Wrong problem for the user**: The most actionable accessibility gap is not loot box grids but reading UI panels that appear during normal gameplay — Pierre's shop item details, TV program text, inventory tooltips. These panels are text-heavy and structured, not pixel-art grids.

2. **Annotation cost**: Labeling hundreds of grid cells at the item level is expensive. Fine-tuning a VLM to classify individual 16×16 sprites is harder than fine-tuning it to classify which screen type the user is looking at.

The pivot: **targeted panel reading via an agent/tool-calling pipeline**. The VLM classifies the screen type (orchestrator), then dispatches to a specialized extraction agent (tool) that crops the relevant region and runs OCR. GPU time is spent only on vision classification; text extraction runs on CPU.

## Decision

**Orchestrator VLM** (Qwen2.5-VL-7B-Instruct, LoRA fine-tuned, GPU) classifies the screen and dispatches tool calls. **Specialized extraction agents** (OpenCV + OCR, CPU-only) handle region cropping and text extraction.

### Architecture

```
User uploads screenshot
  |
  v
FastAPI POST /analyze  (port 8000)
  |
  v
Orchestrator VLM  (Qwen2.5-VL-7B, FP16, ROCm, vLLM port 8001)
  Classifies screen type
  Returns tool_call response
  |
  +-- tool_call: crop_pierres_detail_panel  -----> OpenCV crop + EasyOCR
  |                                                  Returns: {name, description,
  |                                                            price_per_unit,
  |                                                            quantity_selected,
  |                                                            total_cost}
  |
  +-- tool_call: crop_tv_dialog  [Phase 2] ------> OpenCV crop + EasyOCR
  |                                                  Returns: {text}
  |
  +-- tool_call: crop_inventory_tooltip  [Phase 3] > OpenCV crop + EasyOCR
                                                      Returns: {name, description,
                                                                sell_price}
  |
  v
Narration template (Python string formatting)
  |
  v
MeloTTS synthesis  (CPU, WAV output)
  |
  v
FastAPI response  (audio/wav)
  |
  v
Browser <audio> element plays
```

### Tool Definitions

Tools are passed to the orchestrator VLM in OpenAI function-calling format:

**`crop_pierres_detail_panel`** (Phase 1 — MVP)
- Input: screenshot image path
- Action: OpenCV template matching to locate the right-column detail panel; EasyOCR text extraction
- Output: `{ "name": str, "description": str, "price_per_unit": int, "quantity_selected": int, "total_cost": int }`

**`crop_tv_dialog`** (Phase 2)
- Input: screenshot image path
- Action: OpenCV crop of TV screen region; EasyOCR
- Output: `{ "text": str }`

**`crop_inventory_tooltip`** (Phase 3)
- Input: screenshot image path
- Action: OpenCV crop of tooltip popup; EasyOCR
- Output: `{ "name": str, "description": str, "sell_price": int }`

### Orchestrator Fine-Tuning Target

The VLM is fine-tuned to perform **screen classification + tool dispatch**. Training examples are `(screenshot, tool_call_response)` pairs — the VLM learns to look at a screenshot and output the correct function call. It does not need to read text or extract field values itself.

This is a much simpler fine-tuning target than cell-level item recognition.

### Orchestrator Prompting

The system prompt passes the tool list and instructs the model to call exactly one tool per screenshot:

```
You are an accessibility assistant for Stardew Valley. Given a screenshot, identify the active UI panel and call the appropriate tool to extract its contents. Call exactly one tool. Do not attempt to extract text yourself.
```

## Alternatives Considered

| Option | Why not selected |
|--------|-----------------|
| **VLM reads full grid cells (ADR-002 original)** | Wrong primary user need; high annotation cost; 16×16 sprite recognition is harder than screen type classification |
| **VLM does both classification and text extraction** | GPU-intensive for simple OCR; harder to debug (wrong answer could be vision or text error); OCR is CPU-sufficient for clean rendered text |
| **OCR-only (no VLM)** | Cannot generalize to new screen types without hardcoded logic; VLM handles screen type variability naturally |
| **Separate classifier + OCR (no tool calling)** | Tool-calling format makes the architecture cleaner, more extensible, and directly demonstrates the agent pattern for the conference talk |

## Rationale

**GPU stays free for vision**: Screen classification requires vision; text extraction does not. Keeping OCR on CPU leaves GPU headroom for the orchestrator and avoids unnecessary GPU memory pressure.

**Separation of concerns**: Classification failures and extraction failures are independently debuggable. If the wrong tool is called, the VLM is at fault. If field values are wrong, the OCR agent is at fault.

**Scales to new screen types by adding tools**: Adding Phase 2 (TV dialog) requires writing one new extraction function — the orchestrator learns to call it by adding training examples. No architectural changes needed.

**Simpler fine-tuning**: Screen type classification (N classes) is simpler than cell-level item recognition (~600 item vocabulary). Fewer training examples needed; faster to validate.

**Strong talk narrative**: The agent/tool-calling pattern is a core topic in applied AI engineering. This architecture teaches that pattern in a concrete, relatable use case.

## Consequences

**Gets easier**:
- Fine-tuning target is simpler (screen classification, not item recognition)
- Extraction agents (OpenCV + OCR) are deterministic and testable in isolation
- New screen types added by writing one function + training examples
- GPU/CPU separation makes resource management straightforward
- No synthetic grid data generation needed for MVP

**Gets harder**:
- Two components to maintain (VLM orchestrator + OCR agents)
- OpenCV template matching is brittle to UI skin changes (acceptable for MVP vanilla Stardew)
- Need screen-type labeled screenshots for orchestrator training (different from item-labeled data)

**We are committing to**:
- Qwen2.5-VL-7B as the orchestrator (screen classifier + tool dispatcher)
- OpenCV + EasyOCR for CPU-side extraction (see ADR-010)
- Pierre's shop detail panel as the MVP screen type
- OpenAI function-calling format for tool dispatch (compatible with vLLM serving)
- SmolVLM2 comparison question changes to: "can a 2.2B model accurately classify screen types?"

## Evaluation Metrics

| Metric | Target | Description |
|--------|--------|-------------|
| Screen classification accuracy | >= 95% | % of screenshots where correct tool is called |
| Field extraction accuracy | >= 90% | % of extracted fields matching ground truth (exact or fuzzy) |
| End-to-end narration quality | Human eval | Spot-check: does the audio correctly describe the panel? |
| JSON validity rate | >= 99% | % of tool call responses producing valid JSON |

## References

- [ADR-001](001-vlm-selection.md): VLM selection — Qwen2.5-VL-7B role updated to orchestrator
- [ADR-002](002-vlm-role-architecture.md): Superseded by this ADR
- [ADR-005](005-serving-strategy.md): Serving strategy — tool-calling via OpenAI-compatible API
- [ADR-010](010-screen-region-extraction.md): Extraction layer details
- `docs/plan.md`: Implementation sequence and phases
