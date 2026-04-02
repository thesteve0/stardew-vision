# Stardew Vision

An accessibility tool that lets visually impaired Stardew Valley players upload a screenshot of an in-game UI panel and hear its contents read aloud. Built as a conference talk artifact demonstrating VLMs, agentic tool-calling, OCR, and TTS for practical accessibility use cases.

## Problem Statement

Stardew Valley's UI text is small and rendered in pixel-art fonts. Players with vision impairments can read the game but struggle with small details — item names, prices, descriptions. They take a screenshot and want to hear those details narrated back to them.

## How It Works

FastAPI is the **agent runtime** — it manages the loop, executes tool calls, and holds state. Qwen2.5-VL-7B is the **reasoner** — it classifies the screen, calls extraction tools, checks for failures, applies corrections, assembles narration, and delegates to TTS.

```
User uploads screenshot
  |
  v
FastAPI /analyze  (port 8000)
  |
  v
Agent loop (Qwen2.5-VL-7B via vLLM, port 8001)
  Turn 1: Qwen calls crop_pierres_detail_panel → OCR JSON
  Turn 2: Qwen checks result, corrects typos, retries with debug=True if needed
  Turn 3: Qwen calls text_to_speech → WAV
  |
  v
Browser plays audio
```

See [`docs/adr/009-agent-tool-calling-architecture.md`](docs/adr/009-agent-tool-calling-architecture.md) for the full design.

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

## Setup

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
| Pierre's shop OCR extraction | Complete — 93% field accuracy |
| Agent loop (FastAPI + Qwen) | In progress |
| TTS tool (MeloTTS) | Not started |
| Web app | Not started |
| Fine-tuning (LoRA) | Not started |

See [`docs/IMPLEMENTATION_STATUS.md`](docs/IMPLEMENTATION_STATUS.md) for full detail.

## Key Technical Decisions

| Decision | Choice |
|----------|--------|
| VLM orchestrator | Qwen2.5-VL-7B-Instruct (FP16, LoRA) |
| Agent loop | Raw OpenAI client — no framework |
| OCR | PaddleOCR PP-OCRv5, CPU-only |
| TTS | MeloTTS-English, CPU |
| Serving | vLLM (local) + KServe on OpenShift AI |
| Precision | FP16 only — ROCm 7.2 constraint |

Full rationale in [`docs/adr/`](docs/adr/).

## Known Issues

- **PaddlePaddle version**: Must use `paddlepaddle==3.2.0`. Version 3.3.0 has an OneDNN PIR bug that breaks CPU inference.
- **FP16 only**: No BF16, INT4, or INT8 on this hardware.
- `datasets/` and `models/` are host volumes — not in git.

---

**Template Info**: Created from [datascience-template-ROCm](https://github.com/thesteve0/datascience-template-ROCm). For ROCm setup details, see `template_docs/`.
