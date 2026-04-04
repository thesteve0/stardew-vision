# Testing the Agent Loop

**Last updated**: 2026-04-03

**What this is**: End-to-end test of the Qwen + FastAPI agentic loop. Upload a
Pierre's shop screenshot → Qwen calls `crop_pierres_detail_panel` via tool-calling →
JSON response with extracted fields and narration.

**What's stubbed**: TTS (`text_to_speech`) returns `{status, text, has_errors}` — no
audio yet. The `/analyze` endpoint returns JSON, not WAV.

**Architecture**: vLLM runs in Docker container on **host machine** (not in devcontainer) for ROCm gfx1151 compatibility. FastAPI runs in devcontainer and connects via forwarded port 8001.

---

## Prerequisites

- ✅ Docker on host machine with ROCm GPU access
- ✅ Devcontainer rebuilt with forwarded ports 8000, 8001 (see `.devcontainer/devcontainer.json`)
- ✅ Python environment in devcontainer with project dependencies (`uv sync`)
- ✅ `PYTHONPATH=/workspaces/stardew-vision/src` set (already in devcontainer)

---

## Step 1 — Start vLLM (On Host Machine)

**Run this on your host machine, outside the devcontainer:**

```bash
docker run --rm \
  --device=/dev/kfd \
  --device=/dev/dri \
  --group-add=video \
  --cap-add=SYS_PTRACE \
  --security-opt seccomp=unconfined \
  --ipc=host \
  -p 8001:8000 \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  -e HF_TOKEN=$HF_TOKEN \
  rocm/vllm:rocm7.12.0_gfx1151_ubuntu24.04_py3.12_pytorch_2.9.1_vllm_0.16.0 \
  vllm serve Qwen/Qwen2.5-VL-7B-Instruct \
  --dtype float16 \
  --port 8000 \
  --enable-auto-tool-choice \
  --tool-call-parser hermes
```

**Container details:**
- Image: `rocm/vllm:rocm7.12.0_gfx1151_ubuntu24.04_py3.12_pytorch_2.9.1_vllm_0.16.0`
- Built specifically for AMD Strix Halo (gfx1151) with ROCm 7.12
- Includes PyTorch 2.9.1, vLLM 0.16.0

**Startup time:** ~5-8 minutes
- Model weight loading: ~2-3 minutes
- Encoder cache profiling: ~2-5 minutes
- Look for: `INFO: Application startup complete.` and `Uvicorn running on http://0.0.0.0:8000`

**Test vLLM is running:**

From host:
```bash
curl http://localhost:8001/v1/models
```

From devcontainer (after rebuild):
```bash
curl http://localhost:8001/v1/models
```

Expected response:
```json
{
  "object": "list",
  "data": [
    {
      "id": "Qwen/Qwen2.5-VL-7B-Instruct",
      "object": "model",
      ...
    }
  ]
}
```

**Important flags:**
- `--dtype float16` — required on ROCm 7.2 (AMD Strix Halo). Only validated precision.
- `--enable-auto-tool-choice` — required for tool-calling to work
- `--tool-call-parser hermes` — Qwen2.5 uses Hermes-style tool call format
- Port mapping: Container port 8000 → Host port 8001

---

## Step 2 — Start FastAPI (In Devcontainer)

**Run this inside the devcontainer:**

```bash
# PYTHONPATH already set in devcontainer.json
uvicorn src.stardew_vision.webapp.app:app --host 0.0.0.0 --port 8000 --reload
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [12345] using WatchFiles
INFO:     Started server process [12346]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

**Test FastAPI health endpoint:**

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy"
}
```

---

## Step 3 — Test Agent Loop

### Option A: Browser

Open `http://localhost:8000`, upload a Pierre's shop screenshot, click Analyze.

### Option B: curl (Recommended for first test)

**From devcontainer:**

```bash
curl -s -X POST http://localhost:8000/analyze \
  -F "file=@tests/fixtures/pierre_shop_001.png" | jq .
```

**What happens:**
1. FastAPI receives image, encodes to base64
2. Sends to Qwen via vLLM (http://localhost:8001/v1) with tool definitions
3. **Turn 1**: Qwen calls `crop_pierres_detail_panel(image_b64, debug=False)`
4. **Turn 2**: Qwen reviews OCR, corrects typos or calls debug=True
5. **Turn 3**: Qwen assembles narration, sets has_errors if needed
6. **Turn 4**: Qwen calls `text_to_speech(text="...")` (stub)
7. FastAPI returns JSON response

**Expected duration:** 10-30 seconds (depends on vLLM inference speed)

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

**vLLM runs on host, not in devcontainer**: Due to ROCm gfx1151 compatibility, vLLM runs in a Docker container on the host. The devcontainer connects via forwarded port 8001.

**Port forwarding required**: If `curl http://localhost:8001/v1/models` fails from devcontainer, rebuild the container. The `.devcontainer/devcontainer.json` must have `"forwardPorts": [6006, 8888, 8000, 8001]`.

**PaddlePaddle version**: `paddlepaddle` MUST be `==3.2.0`. Version 3.3.0 breaks
CPU inference with an OneDNN PIR error. Do not upgrade.

**FP16 only on ROCm 7.2**: `--dtype float16` is required. No BF16, INT4, or INT8 validated.

**Tool-calling parser**: If Qwen does not emit tool calls (responds with plain text
instead), try `--tool-call-parser qwen2_5` in the vLLM Docker command.

**VLLM_MODEL mismatch**: The model name in `inference.py` (env var `VLLM_MODEL`) must
exactly match what vLLM is serving: `Qwen/Qwen2.5-VL-7B-Instruct`.

**datasets/errors/ not in git**: This directory is auto-created on first error. It lives
on the host volume — not committed.

**First vLLM startup is slow**: Initial model download can take 10-15 minutes depending on network speed. The model weights are cached in `~/.cache/huggingface` on the host and persist between container restarts.

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `VLLM_MODEL` | `Qwen/Qwen2.5-VL-7B-Instruct` | Model name served by vLLM |
| `VLLM_BASE_URL` | `http://localhost:8001/v1` | vLLM OpenAI-compatible endpoint (host port 8001 → container port 8000) |

**Note:** After devcontainer rebuild with forwarded ports, `localhost:8001` from inside the devcontainer connects to the vLLM container running on the host.

---

## What's Next After Verification

Once tool-calling is confirmed working:

1. **Wire real MeloTTS** (see ADR-003):
   - Install MeloTTS: `pip install git+https://github.com/myshell-ai/MeloTTS.git`
   - Update `src/stardew_vision/tts/synthesize.py` to use MeloTTS instead of stub
   - Test TTS in isolation: `python -c "from stardew_vision.tts.synthesize import text_to_audio_bytes; import sys; sys.stdout.buffer.write(text_to_audio_bytes('Test'))" > test.wav && aplay test.wav`

2. **Switch `/analyze` to return audio**:
   - Update `src/stardew_vision/webapp/routes.py` to return `StreamingResponse` with `media_type="audio/wav"`
   - Test: `curl -X POST http://localhost:8000/analyze -F "file=@tests/fixtures/pierre_shop_001.png" --output response.wav && aplay response.wav`

3. **Collect multi-screen-type screenshots** for fine-tuning:
   - Pierre's shop (MVP - already have fixture)
   - TV dialog screens
   - Inventory tooltips
   - Minimum 50 examples per screen type

4. **Fine-tune Qwen** on screen classification + tool dispatch:
   - Training data: `(screenshot, tool_call_response)` conversation pairs
   - LoRA fine-tuning via PEFT (see ADR-001)
   - Log to MLFlow

5. **Evaluation**:
   - Screen classification accuracy >= 95%
   - Field extraction accuracy >= 90%
   - End-to-end narration quality (human spot-check)

## Troubleshooting

### vLLM container not starting

```bash
# Check if container is running
docker ps | grep vllm

# Check container logs
docker logs <container_id>

# Common issues:
# - GPU not accessible: verify /dev/kfd and /dev/dri exist on host
# - ROCm driver mismatch: ensure host has ROCm 7.2+ drivers
# - Out of memory: Qwen2.5-VL-7B needs ~16GB VRAM + system RAM
```

### Port 8001 not accessible from devcontainer

```bash
# Test from devcontainer
curl http://localhost:8001/v1/models

# If fails:
# 1. Verify devcontainer.json has: "forwardPorts": [6006, 8888, 8000, 8001]
# 2. Rebuild devcontainer: F1 → "Dev Containers: Rebuild Container"
# 3. Test again after rebuild
```

### Tool calls not firing

```bash
# Check vLLM logs for tool call attempts
docker logs <vllm_container_id> | grep -i tool

# Try alternative parser:
# In the docker run command, change:
# --tool-call-parser hermes
# to:
# --tool-call-parser qwen2_5
```

### FastAPI can't connect to vLLM

```bash
# Verify vLLM is responding
curl http://localhost:8001/v1/models

# Check FastAPI logs for connection errors
# Ensure VLLM_BASE_URL env var is correct (default: http://localhost:8001/v1)
```
