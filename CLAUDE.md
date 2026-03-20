# CLAUDE.md

This file provides context to Claude Code when working on this project.

## Project Overview

**Purpose**: There are two purposes to this project. 1) We are building a site that allows visually impaired, but not blind, Stardew Valley players to upload a screenshot of an in-game UI panel (starting with Pierre's shop) and receive an audio file narrating the panel contents. 2) This repository and application will be used to give conference talks and workshops to AI practitioners on using VLMs, agent/tool-calling patterns, OCR, and TTS for practical accessibility use cases.

**Problem Domain**: ["Fine tuning multi-modal models for user interface  state recognition", "Text to speech for visually impared"]

**Key Technologies**:
- Devcontainers, all of this work is happening inside a devcontainer environment
- PyTorch 2.9.1 (ROCm 7.2-accelerated, AMD Strix Halo gfx1151)
- **FP16 only** — the only officially validated precision on this hardware (no BF16, no INT4)
- HuggingFace: `transformers`, `peft`, `trl`, `datasets`, `evaluate`
- VLMs: `Qwen/Qwen2.5-VL-7B-Instruct` (primary) and `HuggingFaceTB/SmolVLM2-2.2B-Instruct` (comparison)
- TTS: MeloTTS-English (local, CPU/GPU-optional, MIT)
- Serving: vLLM 0.7.x (local) + KServe on OpenShift AI (production)
- Training scale-out: Ray Train on OpenShift AI via KubeRay
- Experiment tracking: MLFlow
- Web framework: FastAPI + static HTML
- Feature store: Filesystem/JSONL for MVP; Feast Phase 2

**Full project plan**: See [`docs/plan.md`](docs/plan.md) — the authoritative reference for architecture, implementation sequence, and decisions.
**Architecture decisions**: See [`docs/adr/`](docs/adr/) — ADRs 001-010 document all major choices and their rationale. ADR-009 and ADR-010 are the current architecture.

## Codebase Structure

```
scripts/    # Experiment scripts and data collection utilities
datasets/   # Host volume — screenshots, annotations, OpenCV anchor templates
models/     # Host volume — base + fine-tuned LoRA checkpoints
configs/    # Training configs, output schemas, OpenShift serving manifests
docs/       # ADRs, plan, data-collection-plan, evaluation rubric
src/
└── stardew_vision/
    ├── tools/       # Extraction agents: crop_pierres_detail_panel, crop_tv_dialog, etc.
    ├── models/      # VLM orchestrator wrapper, LoRA fine-tuning (Qwen + SmolVLM2)
    ├── tts/         # MeloTTS synthesize.py
    ├── serving/     # vLLM OpenAI-client wrapper + tool dispatch logic
    └── webapp/      # FastAPI app, routes, static HTML
```

**Key files**:
Main model architecture
- `main.py` - The driver program when this is run from the CLI. 
- The rest are to be built out and updated as we work together

## Development Workflow

**Common commands**:

```bash
# Run extraction tool on a screenshot
python scripts/test_extraction_tool.py

# Test OCR output
python scripts/test_ocr_on_panel.py
```

**Testing**:
```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_tools.py -v

# Run with coverage
pytest tests/ --cov=src/stardew_vision
```

**Linting/Formatting** (if configured):
We are using Ruff
```bash

```

## Architectural Decisions

See [`docs/adr/`](docs/adr/) for full ADRs. Quick reference:

- **Pipeline**: Agent/tool-calling. Orchestrator VLM (Qwen2.5-VL-7B, GPU) classifies the screen type and dispatches a tool call. CPU extraction agents (OpenCV + PaddleOCR) crop the region and extract text. Result goes to MeloTTS → WAV. See [ADR-009](docs/adr/009-agent-tool-calling-architecture.md).
- **Extraction layer**: OpenCV template matching for UI region location; PaddleOCR (PP-OCRv5) for text extraction; both CPU-only. Chosen over EasyOCR for faster CPU throughput, SOTA accuracy, and correct capitalization preservation. See [ADR-010](docs/adr/010-screen-region-extraction.md) and [docs/ocr-choice.md](docs/ocr-choice.md).
- **MVP screen type**: Pierre's General Store detail panel — name, description, price per unit, quantity selected, total cost.
- **Fine-tuning**: Orchestrator VLM fine-tuned on `(screenshot, tool_call_response)` pairs. LoRA via PEFT for Qwen2.5-VL-7B; TRL SFTTrainer for SmolVLM2-2.2B. Both in FP16. See [ADR-001](docs/adr/001-vlm-selection.md).
- **Configuration**: YAML files in `configs/training/` for hyperparameters; `configs/output_schema.json` for per-screen-type extraction JSON schemas.
- **Checkpointing**: LoRA adapters saved to `models/fine-tuned/{run_name}/` (host volume). Naming: `{model_short_name}-{run_type}-v{N}`.
- **Experiment tracking**: MLFlow; local `mlruns/`; run naming `{model_short_name}-{run_type}-v{N}`.
- **Serving**: vLLM on port 8001 (OpenAI-compatible API with tool-calling); FastAPI web app on port 8000. Client uses `openai` library — same code works for local and OpenShift AI endpoints. See [ADR-005](docs/adr/005-serving-strategy.md).
- **Feature store**: Filesystem/JSONL for MVP. Feast in Phase 2 (see [ADR-006](docs/adr/006-feature-store-strategy.md)). Annotation schema is Feast-compatible from day 1 (UUID image_id, timestamps).

## Important Patterns

**ROCm constraints** (enforced throughout — see `template_docs/notesOnRocm72.md`):
- `dtype=torch.float16` everywhere — no BF16, no INT4, no INT8
- `ROCBLAS_USE_HIPBLASLT=1` (already in devcontainer env)
- `torch.compile(mode="reduce-overhead")` for inference
- SmolVLM2 may need BF16 as fallback — test FP16 first, document result

**Package management**: `uv` with `exclude-dependencies` in pyproject.toml to protect ROCm-provided packages. Never `pip install torch` — it will overwrite the ROCm build.

**Python package**: The importable package is `stardew_vision` (underscore). `src/stardew-vision/` with hyphen must be renamed. `PYTHONPATH=/workspaces/stardew-vision/src` is set in devcontainer.

## Known Issues and Gotchas

- `src/stardew-vision/` must be renamed to `src/stardew_vision/` before any code is written there (hyphen is illegal as Python package name) [RESOLVED]
- **PaddlePaddle version**: MUST use `paddlepaddle==3.2.0`. Version 3.3.0 has an OneDNN PIR conversion bug that breaks CPU inference with error `ConvertPirAttribute2RuntimeAttribute not support [pir::ArrayAttribute<pir::DoubleAttribute>]`. Do NOT upgrade without testing.
- SmolVLM2 prefers BF16 but ROCm 7.2 only validates FP16 — test FP16 first; if unstable, document BF16 result in ADR-001 update
- SmolVLM2's 81-token image compression may miss fine-grained pixel-art detail — this is the hypothesis to test
- vLLM port 8001 and webapp port 8000 need to be added to `devcontainer.json` `forwardPorts`
- `datasets/` and `models/` are host volumes — not committed to git; add to `.gitignore`

## External Dependencies

- **Sprite sheet**: Stardew Valley `springobjects.png` from fan wiki (CC-BY-NC-SA); downloaded locally to `datasets/assets/`
- **Item manifest**: Community-maintained JSON mapping item IDs to names/categories
- **Base models**: Downloaded from HuggingFace Hub to `models/base/` (via `HF_HOME` env var in devcontainer)
- **HuggingFace Hub**: Dataset and model artifacts pushed to `{username}/stardew-loot-vision-dataset` and `{username}/stardew-vision-vlm`
- **No external APIs** at MVP (everything runs locally)

## Testing Strategy

- `pytest tests/` — unit tests for extraction tools, VLM wrapper, TTS, webapp
  - **Status**: Pierre's shop extraction tool has 8/8 tests passing (2026-03-20)
  - Fixture: `tests/fixtures/pierre_shop_001.png` (1600×1200 screenshot)
  - Coverage: template matching, OCR, field parsing, error handling
- End-to-end: upload test screenshot → verify audio response via webapp
- Evaluation metrics logged to MLFlow are the primary quality signal (not just pytest)
- Test set = real screenshots only (not used in training)
---

**Note**: This is a ROCm devcontainer project. For ROCm-specific troubleshooting (GPU access, dependency conflicts, Python version issues), see `template_docs/CLAUDE.md`.
For now we are using ROCm 7.2  - please make sure to read [notesOnRocm72.md](template_docs/notesOnRocm72.md) to understand some of the best practices when working on AMD Strix Halo and Point computers

## Overall intstructions
## Bash Conventions
- Do not append `| tail -N` or `| head -N` to commands unless the output is expected to exceed 500 lines

