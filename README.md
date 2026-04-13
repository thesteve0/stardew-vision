# Stardew Vision

An accessibility tool that lets visually impaired Stardew Valley players upload a screenshot of an in-game UI panel and hear its contents read aloud. Built as a conference talk artifact demonstrating VLMs, agentic tool-calling, OCR, and TTS for practical accessibility use cases.

## Problem Statement

Stardew Valley's UI text is small and rendered in pixel-art fonts. Players with vision impairments can read the game but struggle with small details — item names, prices, descriptions. They take a screenshot and want to hear those details narrated back to them.

## How It Works

FastAPI is the **agent runtime** — it manages the loop, executes tool calls, holds state, and calls TTS. Qwen2.5-VL-7B is the **reasoner** — it classifies the screen, calls the appropriate OCR extraction tool if one exists, validates and corrects the result, and returns a structured JSON response.

```
User uploads screenshot
  |
  v
FastAPI /analyze  (port 8000)
  |
  v
Agent loop (Qwen2.5-VL-7B via vLLM, port 8001)
  Turn 1: Qwen sees screenshot — does it match a known tool?
    • Recognized screen → tool_call: crop_pierres_detail_panel → OCR JSON returned to Qwen
    • Unrecognized screen → Qwen returns JSON immediately (no tool call)
  Turn 2 (if tool was called): Qwen reviews OCR result, silently corrects typos,
    returns final JSON: {"narration": "...", "has_errors": false|true}
  |
  v
FastAPI parses JSON:
  • has_errors=true → save screenshot to datasets/errors/, log failure
  • Either way → call MeloTTS with narration text → WAV bytes
  |
  v
Browser plays audio
```

See [`docs/adr/009-agent-tool-calling-architecture.md`](docs/adr/009-agent-tool-calling-architecture.md) and [`docs/adr/011-agent-loop-refinements.md`](docs/adr/011-agent-loop-refinements.md) for the full design.

## Dataset

- **Source**: Screenshots taken from Stardew Valley gameplay (Pierre's shop, iPad + PC)
- **Size**: 22 annotated Pierre's shop screenshots (Phase 1)
- **Location**: `datasets/pierre_shop/` (host volume — not committed to git)
- **Annotation schema**: JSONL with `image_id`, `screen_type`, `expected_extraction` fields

## Project Structure

```
src/stardew_vision/
  tools/        # Extraction agents: crop_pierres_detail_panel, etc.
  tts/          # MeloTTS wrapper (text_to_speech tool)
  serving/      # FastAPI agent loop (inference.py)
  webapp/       # FastAPI app, routes, static HTML
datasets/       # Host volume — screenshots, annotations, templates
models/         # Host volume — base + fine-tuned LoRA checkpoints
docs/adr/       # Architecture Decision Records (ADR-009 is the core design)
configs/        # Training configs, output schemas
```

## Deployment

**Production Environment:** Red Hat OpenShift AI 3.2+ with NVIDIA L40S GPUs

### OpenShift AI Deployment

Complete guides for deploying to OpenShift AI:

- **[Deployment Summary](docs/DEPLOYMENT_SUMMARY.md)** — Issues fixed, final configuration, production status
- **[KServe Deployment Guide](docs/DEPLOYING_MODELS_KSERVE.md)** — Detailed step-by-step deployment
- **[Quick Start Guide](docs/DEPLOYING_MODELS_QUICKSTART.md)** — Fast-track for experienced users

**Architecture:**
- vLLM serving Qwen2.5-VL-7B-Instruct (GPU-accelerated, tool calling enabled)
- Coordinator agent runtime (3 replicas)
- OCR tool (PaddleOCR + OpenCV, 2 replicas)
- TTS tool (Kokoro, 2 replicas)
- All services internal-only except webapp (OpenShift Route with TLS)

### Local Development Setup

This project runs in a ROCm devcontainer on AMD Strix Halo hardware.

```bash
# Install project dependencies
uv sync

# NEVER use pip install — it will overwrite the ROCm PyTorch build
```

**Hardware**: AMD Strix Halo (gfx1151), ROCm 7.2, PyTorch 2.9.1, FP16 only.

## Usage

### Run extraction tool on a screenshot (local dev)

```bash
python main.py --image datasets/pierre_shop/IMG_7708.jpg --debug
```

### Run tests

```bash
pytest tests/
pytest tests/test_tools.py -v
```

### Start vLLM server (Qwen orchestrator)

```bash
vllm serve models/fine-tuned/qwen25vl-stardew-v1 \
  --dtype float16 \
  --port 8001 \
  --served-model-name stardew-vision-vlm
```

### Start web app

```bash
uvicorn src.stardew_vision.webapp.app:app --port 8000
```

Then open `http://localhost:8000` and upload a Pierre's shop screenshot.

## Status

| Component | Status |
|-----------|--------|
| Pierre's shop OCR extraction | ✅ Complete — 8/8 tests passing |
| Agent loop (FastAPI + Qwen) | ✅ Complete — deployed to production |
| TTS tool (Kokoro) | ✅ Complete — deployed to production |
| Web app | ✅ Complete — deployed to production |
| Fine-tuning (LoRA) | Planned for Phase 2 |
| **Production Deployment** | ✅ **Live on OpenShift AI** |

**Deployment URL:** `https://stardew-vision-stardew-vision.apps.stardew-vision.sandbox5291.opentlc.com`

See [`docs/DEPLOYMENT_SUMMARY.md`](docs/DEPLOYMENT_SUMMARY.md) for complete deployment details.

## Key Technical Decisions

| Decision | Choice |
|----------|--------|
| VLM orchestrator | Qwen2.5-VL-7B-Instruct (FP16) |
| Agent loop | Raw OpenAI client — no framework |
| OCR | PaddleOCR PP-OCRv5, CPU-only |
| TTS | Kokoro (CPU, MIT license) |
| Serving | vLLM (local dev) + KServe on OpenShift AI (production) |
| Precision | FP16 only — ROCm 7.2 constraint (local dev) |

Full rationale in [`docs/adr/`](docs/adr/).

## Known Issues

- **PaddlePaddle version**: Must use `paddlepaddle==3.2.0`. Version 3.3.0 has an OneDNN PIR bug that breaks CPU inference.
- **FP16 only**: No BF16, INT4, or INT8 on this hardware.
- `datasets/` and `models/` are host volumes — not in git.

## TODOs

- **Async OCR error logging**: When OCR fails or produces gibberish, Qwen should fire-and-forget to a separate async service that logs the raw OCR debug output along with the screen capture. This must not delay the audio response to the user.

---

**Template Info**: Created from [datascience-template-ROCm](https://github.com/thesteve0/datascience-template-ROCm). For ROCm setup details, see `template_docs/`.
