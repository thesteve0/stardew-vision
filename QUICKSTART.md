# Stardew Vision Quick Start

**Last updated**: 2026-04-03

## Architecture Overview

```
Host Machine                           Devcontainer
┌─────────────────────────┐           ┌──────────────────────────────┐
│ vLLM Docker Container   │           │ FastAPI Webapp               │
│                         │           │   + Extraction Tools         │
│ Qwen2.5-VL-7B-Instruct  │◄──────────┤   + TTS (stub)               │
│ ROCm 7.12 / gfx1151     │  Port     │                              │
│                         │  8001     │ Connects to vLLM via         │
│ Port 8000 → 8001        │           │ http://localhost:8001/v1     │
└─────────────────────────┘           └──────────────────────────────┘
```

**Why this architecture?**
- vLLM ROCm support for Strix Halo (gfx1151) works best in official AMD container
- Avoids dependency conflicts in devcontainer
- FastAPI can still run in devcontainer with forwarded ports

---

## Step 1: Start vLLM (On Host)

**Open a terminal on your host machine** (not in devcontainer):

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

**Wait ~5-8 minutes** for startup. Look for:
```
INFO: Application startup complete.
INFO: Uvicorn running on http://0.0.0.0:8000
```

**Test from host:**
```bash
curl http://localhost:8001/v1/models
```

---

## Step 2: Rebuild Devcontainer

The devcontainer needs ports 8000 and 8001 forwarded to access vLLM and serve FastAPI.

**In IntelliJ or VSCode:**
1. Open Command Palette / Actions: `F1` or `Ctrl+Shift+P`
2. Type: "Dev Containers: Rebuild Container"
3. Select and wait for rebuild

**After rebuild, test from devcontainer:**
```bash
curl http://host.docker.internal:8001/v1/models
```

You should see the same model list response.

> **Note**: Inside the devcontainer, use `host.docker.internal` (not `localhost`) to reach the host machine. `localhost` refers to the container itself. The `VLLM_BASE_URL` env var in `devcontainer.json` is already set correctly to `http://host.docker.internal:8001/v1`.

---

## Step 3: Start FastAPI (In Devcontainer)

**Open terminal inside devcontainer:**

```bash
uvicorn src.stardew_vision.webapp.app:app --host 0.0.0.0 --port 8000 --reload
```

**Test health endpoint:**
```bash
curl http://localhost:8000/health
```

Expected: `{"status":"healthy"}`

---

## Step 4: Test Agent Loop

**POST a test image:**

```bash
curl -s -X POST http://localhost:8000/analyze \
  -F "file=@tests/fixtures/pierre_shop_001.png" | jq .
```

**Expected flow (watch FastAPI logs):**
1. Image received and encoded
2. Turn 1: Qwen calls `crop_pierres_detail_panel`
3. Turn 2: Qwen reviews OCR, corrects typos
4. Turn 3: Qwen assembles narration
5. Turn 4: Qwen calls `text_to_speech` (stub)
6. JSON response returned

**Expected response:**
```json
{
  "narration": "You are looking at Parsnip Seeds. Plant these in the spring...",
  "extraction": {
    "name": "Parsnip Seeds",
    "description": "Plant these in the spring. Takes 4 days to mature.",
    "price_per_unit": 20,
    "quantity_selected": 60,
    "total_cost": 1200
  },
  "has_errors": false
}
```

---

## Next Steps

Once the agent loop is verified:

### 1. Wire Real TTS
```bash
# Install MeloTTS
pip install git+https://github.com/myshell-ai/MeloTTS.git

# Update src/stardew_vision/tts/synthesize.py
# Test TTS in isolation
python -c "from stardew_vision.tts.synthesize import text_to_audio_bytes; import sys; sys.stdout.buffer.write(text_to_audio_bytes('Test'))" > test.wav
aplay test.wav
```

### 2. Return Audio from /analyze
- Update `src/stardew_vision/webapp/routes.py`
- Change response from JSON to `StreamingResponse(media_type="audio/wav")`

Test:
```bash
curl -X POST http://localhost:8000/analyze \
  -F "file=@tests/fixtures/pierre_shop_001.png" \
  --output response.wav

aplay response.wav
```

### 3. Fine-Tuning
- Collect multi-screen-type screenshots (50+ per type)
- Fine-tune Qwen on screen classification + tool dispatch
- Target: 95% classification accuracy, 90% field extraction accuracy

---

## Troubleshooting

### vLLM won't start
```bash
# Check GPU access
ls -la /dev/kfd /dev/dri

# Check ROCm version
rocm-smi

# Verify Docker can access GPU
docker run --rm --device=/dev/kfd --device=/dev/dri rocm/pytorch:latest rocm-smi
```

### Port 8001 not accessible from devcontainer
```bash
# Verify forwardPorts in .devcontainer/devcontainer.json
cat .devcontainer/devcontainer.json | grep forwardPorts
# Should show: "forwardPorts": [6006, 8888, 8000, 8001]

# If missing, rebuild devcontainer
```

### Tool calls not firing
- Try `--tool-call-parser qwen2_5` instead of `hermes`
- Check vLLM logs: `docker logs <container_id>`
- Verify `--enable-auto-tool-choice` flag is present

---

## Detailed Documentation

- **Full testing guide**: `docs/TESTING_AGENT_LOOP.md`
- **Architecture decisions**: `docs/adr/009-agent-tool-calling-architecture.md`
- **Project plan**: `docs/plan.md`
- **Project context**: `CLAUDE.md`
