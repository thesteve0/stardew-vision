# Testing the Agent Loop

**What this is**: End-to-end test of the Qwen + FastAPI agentic loop. Upload a
Pierre's shop screenshot → Qwen calls `crop_pierres_detail_panel` via tool-calling →
JSON response with extracted fields and narration.

**What's stubbed**: TTS (`text_to_speech`) returns `{status, text, has_errors}` — no
audio yet. The `/analyze` endpoint returns JSON, not WAV.

---

## Prerequisites

- vLLM installed (`pip install vllm` or ROCm build)
- `Qwen/Qwen2.5-VL-7B-Instruct` model weights downloaded
- Python environment with project dependencies (`uv sync`)
- `PYTHONPATH=/workspaces/stardew-vision/src` set (already in devcontainer; set manually if running outside)

---

## Step 1 — Start vLLM

```bash
vllm serve Qwen/Qwen2.5-VL-7B-Instruct \
  --dtype float16 \
  --port 8001 \
  --enable-auto-tool-choice \
  --tool-call-parser hermes
```

**Flags explained:**
- `--dtype float16` — required on ROCm 7.2 (AMD Strix Halo). Use `bfloat16` on NVIDIA if preferred.
- `--enable-auto-tool-choice` — required for tool-calling to work
- `--tool-call-parser hermes` — Qwen2.5 uses Hermes-style tool call format

**If you renamed the model with `--served-model-name`:**

```bash
vllm serve Qwen/Qwen2.5-VL-7B-Instruct \
  --dtype float16 \
  --port 8001 \
  --served-model-name stardew-vision-vlm \
  --enable-auto-tool-choice \
  --tool-call-parser hermes
```

Then set the env var before starting FastAPI:
```bash
export VLLM_MODEL=stardew-vision-vlm
```

Without `--served-model-name`, the default `VLLM_MODEL=Qwen/Qwen2.5-VL-7B-Instruct` works fine.

Wait for vLLM to print `INFO: Application startup complete` before proceeding.

---

## Step 2 — Start FastAPI

In a second terminal, from the repo root:

```bash
export PYTHONPATH=/workspaces/stardew-vision/src   # skip if already set
uvicorn src.stardew_vision.webapp.app:app --port 8000 --reload
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

---

## Step 3 — Test

### Option A: browser

Open `http://localhost:8000`, upload a Pierre's shop screenshot, click Analyze.

### Option B: curl

```bash
curl -s -X POST http://localhost:8000/analyze \
  -F "file=@tests/fixtures/pierre_shop_001.png" | jq .
```

### Option C: health check first

```bash
curl http://localhost:8000/health
# → {"status":"ok"}
```

---

## Expected Response Shape

```json
{
  "narration": "The item is Parsnip Seeds. Description: Plant these in the spring. Takes 4 days to mature. Price: 20 gold each. You have selected 60, for a total of 1200 gold.",
  "has_errors": false,
  "fields": {
    "name": "Parsnip Seeds",
    "description": "Plant these in the spring. Takes 4 days to mature.",
    "price_per_unit": 20,
    "quantity_selected": 60,
    "total_cost": 1200,
    "energy": "",
    "health": ""
  }
}
```

---

## What to Verify

| Check | What to look for |
|-------|-----------------|
| Qwen made a tool call | vLLM logs show a request; FastAPI logs show `Tool call: crop_pierres_detail_panel` |
| `fields` are populated | `name`, `price_per_unit`, `quantity_selected`, `total_cost` non-zero |
| `narration` is coherent | Reads like a natural-language description of the item |
| No crash on second turn | Qwen calls `text_to_speech` after reviewing OCR result |
| `has_errors: false` for a clean image | The fixture screenshot should not trigger errors |

---

## What to Watch for in FastAPI Logs

Turn-by-turn tool calls are logged at INFO level:

```
INFO:stardew_vision.serving.inference:Tool call: crop_pierres_detail_panel args={'debug': False}
INFO:stardew_vision.serving.inference:Tool call: text_to_speech args={'text': '...', 'has_errors': False}
```

To see debug logs (turn numbers, etc.):

```bash
uvicorn src.stardew_vision.webapp.app:app --port 8000 --log-level debug
```

---

## Known Issues / Gotchas

**PaddlePaddle version**: `paddlepaddle` MUST be `==3.2.0`. Version 3.3.0 breaks
CPU inference with an OneDNN PIR error. Do not upgrade.

**FP16 only on ROCm 7.2**: `--dtype float16` is required. No BF16, INT4, or INT8.

**Tool-calling parser**: If Qwen does not emit tool calls (responds with plain text
instead), try `--tool-call-parser qwen2_5` — vLLM parser naming varies by version.
Verify with: `vllm serve --help | grep tool-call-parser`.

**VLLM_MODEL mismatch**: The model name in `inference.py` (env var `VLLM_MODEL`) must
exactly match what vLLM is serving. If vLLM was started without `--served-model-name`,
the name is `Qwen/Qwen2.5-VL-7B-Instruct`.

**datasets/errors/ not in git**: This directory is auto-created on first error. It lives
on the host volume — not committed.

**PYTHONPATH**: If running outside the devcontainer, ensure
`PYTHONPATH` includes `src/` so `stardew_vision` is importable.

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `VLLM_MODEL` | `Qwen/Qwen2.5-VL-7B-Instruct` | Model name served by vLLM |
| `VLLM_BASE_URL` | `http://localhost:8001/v1` | vLLM OpenAI-compatible endpoint |

---

## What's Next After Verification

Once tool-calling is confirmed working:

1. Remove the hard-coded Pierre's shop instruction from the system prompt in
   `src/stardew_vision/serving/inference.py` (`_SYSTEM_PROMPT`)
2. Start collecting multi-screen-type screenshots for fine-tuning
3. Wire in MeloTTS (`src/stardew_vision/tts/synthesize.py`) to replace the stub
4. Switch `/analyze` response to `audio/wav`
