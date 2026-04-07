# Session Handoff — 2026-04-05

Read this file plus all other files in `tmp/` at the start of the next session to restore full context.

---

## What We Did This Session

We made three significant design decisions that are now documented in `docs/adr/011-agent-loop-refinements.md` and reflected in `README.md`, `docs/plan.md`, `docs/IMPLEMENTATION_STATUS.md`, and `docs/adr/009-agent-tool-calling-architecture.md`. **No Python files were changed yet.**

### Design Decision 1: TTS is no longer a Qwen tool call

FastAPI calls MeloTTS directly after Qwen returns its final JSON response. Qwen has no `text_to_speech` tool. This removes an unnecessary round-trip — TTS synthesis is infrastructure, not reasoning.

### Design Decision 2: Qwen always returns structured JSON

Qwen's final response is always:
```json
{"narration": "...", "has_errors": false}
```
This is enforced by fine-tuning. FastAPI parses it, logs + saves screenshot if `has_errors: true`, then calls MeloTTS with `narration`.

### Design Decision 3: System prompt generalized — any Stardew Valley screen

The system prompt no longer says "You will be shown a screenshot from Pierre's General Store." It describes Qwen's role for any Stardew Valley screen:
- **Recognized screen**: Qwen calls the matching OCR tool, validates/corrects result, returns JSON
- **Unrecognized screen**: Qwen returns JSON immediately with narration = "I have not been trained to recognize that screen. If it is important to you please let Steve know."

### Also decided: remove debug=True retry step

`debug=True` doesn't improve OCR accuracy — it just returns raw OCR boxes. Removed from the loop. A TODO exists in `README.md` for async error logging (fire-and-forget, must not delay audio response).

---

## What's Next (Code Changes)

The documentation is updated. Now the code needs to match. In order:

### Step 1: Rewrite `src/stardew_vision/serving/inference.py`

Key changes needed:
1. Replace `_SYSTEM_PROMPT` — generalize away from Pierre's shop, instruct Qwen to return JSON `{"narration": "...", "has_errors": bool}`, describe unrecognized-screen path
2. Remove `text_to_speech` from `TOOL_DEFINITIONS` and `TOOL_REGISTRY` (in `src/stardew_vision/tools/__init__.py`)
3. Remove the forced `tool_choice` on turn 0 (currently forces `crop_pierres_detail_panel`) — let Qwen decide freely
4. Remove the `debug=True` retry logic
5. Parse Qwen's final JSON response instead of capturing narration from TTS tool args
6. After the loop ends, call `synthesize(narration)` from `stardew_vision.tts.synthesize` directly
7. `has_errors` now comes from parsed JSON, not from TTS tool args

### Step 2: Wire MeloTTS in `src/stardew_vision/tts/synthesize.py`

Currently stubbed. FastAPI now calls `synthesize(text)` directly, so it needs to actually work before end-to-end testing.

### Step 3: Test the loop end-to-end

The previous session ended just before testing. State at that point:
- vLLM was running on host port 8001 (using `scripts/start_vllm_host.sh`)
- FastAPI was running in devcontainer on port 8000 via `uvicorn --reload`
- The `finish_reason=stop` bug fix was applied but NOT yet tested (session ended)

After rebuild + code changes, restart vLLM on host and test:
```bash
curl -s -X POST http://localhost:8000/analyze -F "file=@tests/fixtures/pierre_shop_001.png"
```
Expect: audio/wav response; logs showing Qwen calling `crop_pierres_detail_panel`, then returning JSON, then MeloTTS called.

---

## Important vLLM Bugs Already Fixed (in codebase)

See `tmp/memory_vllm_tool_calling.md` for detail. Summary:
1. **localhost vs host.docker.internal** — devcontainer must use `host.docker.internal:8001`; set in devcontainer.json
2. **Missing chat template** — `configs/serving/qwen2_5_vl_tool_template.jinja` + mounted in `scripts/start_vllm_host.sh`
3. **finish_reason=stop bug** — vLLM returns `finish_reason=stop` even when tool_calls is populated; fix: check `if msg.tool_calls:` not `if finish_reason == "tool_calls"`
4. **Qwen ignoring tools** — NOTE: with new design, forced tool_choice on turn 0 is being REMOVED (Design Decision 3 above). If Qwen ignores tools after fine-tuning, this will need revisiting.

---

## Key Files

- `docs/adr/011-agent-loop-refinements.md` — authoritative record of all design decisions from this session
- `docs/adr/009-agent-tool-calling-architecture.md` — partially superseded, see ADR-011 callout at top
- `src/stardew_vision/serving/inference.py` — needs rewrite per Step 1 above
- `src/stardew_vision/tools/__init__.py` — remove text_to_speech from TOOL_DEFINITIONS and TOOL_REGISTRY
- `src/stardew_vision/tts/synthesize.py` — needs MeloTTS wired in
- `scripts/start_vllm_host.sh` — run on HOST machine (not in devcontainer) to start vLLM
