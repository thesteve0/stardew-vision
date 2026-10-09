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
- VLM: fine-tuned `Qwen/Qwen2.5-VL-7B-Instruct` + pinned private LoRA adapter (current); SmolVLM2 appears in historical comparison plans
- TTS: Kokoro (current CPU microservice); MeloTTS appears only in historical design notes
- Serving: vLLM 0.13 + KServe on OpenShift AI (current production); local ROCm experiments use a separate AMD runtime
- Training scale-out: Ray Train on OpenShift AI via KubeRay
- Experiment tracking: MLFlow
- Web framework: FastAPI + static HTML
- Feature store: Filesystem/JSONL for MVP; Feast Phase 2

**Current deployment**: See [the canonical OpenShift guide](configs/serving/openshift/README.md). [`docs/plan.md`](docs/plan.md) preserves historical planning, not current deployment instructions.
**Architecture decisions**: See [`docs/adr/`](docs/adr/) — ADRs preserve the rationale and history; superseded implementation details are not current deployment instructions.

## Related Repositories

**[stardew-vision-training](https://github.com/thesteve0/stardew-vision-training)**: Model fine-tuning, dataset preparation, and evaluation
- **Purpose**: VLM LoRA training, synthetic data generation, evaluation metrics
- **Contains**: datasets/, fine_tuning/, evaluation/, annotation scripts
- **Output**: Fine-tuned LoRA adapters uploaded to HuggingFace Hub, consumed by this application repo

## Codebase Structure

```
services/
├── coordinator/     # Agent loop runtime (FastAPI)
│   └── stardew_coordinator/
├── ocr-tools/       # Unified Pierre's shop, TV dialog, caught-fish OCR
│   └── assets/      # Extraction assets baked into container
└── tts-tool/        # Text-to-speech synthesis
    └── stardew_tts/
deploy/              # Deployment wrapper and image/local runtime scripts
configs/             # Serving configs (KServe, vLLM, output schemas)
docs/                # ADRs, historical plans and development notes
demos/               # Conference demo examples
tests/               # Pytest suite
```

**Note**: This repo contains **application/serving code only**. Training, datasets, and evaluation tools live in the separate [`stardew-vision-training`](https://github.com/thesteve0/stardew-vision-training) repository.

**Key files**:
Main model architecture
- `main.py` - The driver program when this is run from the CLI. 
- The rest are to be built out and updated as we work together

## Development Workflow

**Common commands**:

```bash
# Start vLLM server (on host machine, outside devcontainer)
bash deploy/start_vllm_host.sh

# Test extraction tools and data collection workflows:
# See stardew-vision-training repo
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

- **Pipeline**: Fine-tuned Qwen classifies the screenshot using baked-in tool schemas. The coordinator parses `<tool_call>` output, injects the image, and calls unified OCR over HTTP. Pierre's shop/TV then use a separate correction/narration call without tools; caught-fish narration is deterministic. The coordinator calls Kokoro directly, not as a Qwen tool.
- **Error handling**: The coordinator tracks extraction failures and saves failing screenshots to the mounted error PVC. Historical structured-final-JSON and four-turn diagrams in ADRs do not describe the current fine-tuned path.

- **Extraction layer**: OpenCV template matching for UI region location; PaddleOCR (PP-OCRv5) for text extraction; both CPU-only. Chosen over EasyOCR for faster CPU throughput, SOTA accuracy, and correct capitalization preservation. See [ADR-010](docs/adr/010-screen-region-extraction.md) and [docs/ocr-choice.md](docs/ocr-choice.md).
- **MVP screen type**: Pierre's General Store detail panel — name, description, price per unit, quantity selected, total cost.
- **Fine-tuning**: Orchestrator VLM fine-tuned on `(screenshot, tool_call_response)` pairs. LoRA via PEFT for Qwen2.5-VL-7B; TRL SFTTrainer for SmolVLM2-2.2B. Both in FP16. See [ADR-001](docs/adr/001-vlm-selection.md).
- **Configuration**: YAML files in `configs/training/` for hyperparameters; `configs/output_schema.json` for per-screen-type extraction JSON schemas.
- **Checkpointing**: LoRA adapters saved to `models/fine-tuned/{run_name}/` (host volume). Naming: `{model_short_name}-{run_type}-v{N}`.
- **Experiment tracking**: MLFlow; local `mlruns/`; run naming `{model_short_name}-{run_type}-v{N}`.
- **Serving**: Production vLLM 0.13 at `stardew-vlm-finetuned-predictor:8080/v1`, model ID `stardew-vlm-finetuned`; coordinator on 8000, unified OCR on 8004, Kokoro on 8003. One replica per service. Port 8001 is a local host convention only.
- **Feature store**: Filesystem/JSONL for MVP. Feast in Phase 2 (see [ADR-006](docs/adr/006-feature-store-strategy.md)). Annotation schema is Feast-compatible from day 1 (UUID image_id, timestamps).

## Important Patterns

**Package Management (CRITICAL — enforced project rule):**
- **ALWAYS use `uv add <package>`** to add a new dependency
- **ALWAYS use `uv sync`** to install from the lockfile
- **NEVER use `pip install`** — it silently overwrites ROCm-provided packages (torch, numpy, scipy, etc.) and breaks GPU access permanently for the session
- Exception: `pip install uv` is acceptable only as a Dockerfile bootstrap step before the project venv exists

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
- `models/` is a host volume — not committed to git; already in `.gitignore`

## External Dependencies

- **Base models**: Downloaded from HuggingFace Hub (cached on host or in OpenShift PVC)
- **HuggingFace Hub**: Fine-tuned LoRA adapters uploaded from training repo, consumed by vLLM serving
- **No external APIs** at runtime (everything runs locally or on OpenShift AI)

## Testing Strategy

- `pytest tests/` — unit tests for microservices (OCR tool, TTS tool, coordinator)
  - **Status**: Pierre's shop extraction tool has 8/8 tests passing (2026-03-20)
  - Fixture: `tests/fixtures/pierre_shop_001.png` (1600×1200 screenshot)
  - Coverage: template matching, OCR, field parsing, error handling
- End-to-end: upload test screenshot → verify audio response via webapp
- **Evaluation metrics**: See stardew-vision-training repo for model quality evaluation
---

**Note**: This is a ROCm devcontainer project. For ROCm-specific troubleshooting (GPU access, dependency conflicts, Python version issues), see `template_docs/CLAUDE.md`.
For now we are using ROCm 7.2  - please make sure to read [notesOnRocm72.md](template_docs/notesOnRocm72.md) to understand some of the best practices when working on AMD Strix Halo and Point computers

## Local Development Architecture (ROCm experiments, not production)

**vLLM Serving (on host machine):**
- vLLM runs in a Docker container on the **host machine** (not in devcontainer)
- Uses AMD image: `rocm/vllm:rocm7.12.0_gfx1151_ubuntu24.04_py3.12_pytorch_2.9.1_vllm_0.16.0`
- We tested `vllm/vllm-openai-rocm:nightly` (0.19) but reverted — the V1 engine it uses has a known OOM bug on gfx1151 during encoder profiling (vllm-project/vllm#37472, fix in PR #38555 unmerged). See `docs/vllm-notes.md`.
- Serves Qwen2.5-VL-7B-Instruct on port 8001
- Why host: Avoids vLLM ROCm compatibility issues inside devcontainer, uses native GPU access

**FastAPI Webapp (in devcontainer):**
- Runs inside devcontainer on port 8000
- Connects to vLLM at `http://localhost:8001/v1` (via forwarded port)
- Manages agent loop, executes extraction tools, returns audio

### Starting vLLM Server (on host)

For experimental AMD development only, use `deploy/start_vllm_host.sh` with
`BASE_MODEL_DIR` and `LORA_ADAPTER_DIR` exported to the downloaded pinned model
and adapter directories. It verifies identities and serves the LoRA ID
`stardew-vlm-finetuned`; this AMD runtime is not the production environment.
Use `deploy/run-local.sh` or `deploy/docker-compose.yml` for local client services.
Production always uses `./deploy/deploy-to-openshift.sh`.

```bash
curl http://localhost:8001/v1/models
```

The response must list both `qwen-base` and the adapter `stardew-vlm-finetuned`.

---

## Current Verified OpenShift Deployment

The canonical deployment is **fine-tuned Qwen2.5-VL-7B-Instruct**, served by
**vLLM 0.13** through KServe. Tool schemas are baked into the classification
system prompt to match training; the coordinator parses `<tool_call>` output
rather than sending an OpenAI `tools=` schema. It dispatches OCR over HTTP, then
produces narration (a separate correction/narration model call for Pierre's shop
and TV; deterministic narration for caught fish) and calls Kokoro TTS directly.

```text
Original Route stardew-vision → coordinator-finetuned:8000 (1 replica)
  ├─ stardew-vlm-finetuned-predictor:8080/v1 (vLLM 0.13, 1 replica, GPU)
  ├─ ocr-tools:8004 (unified OCR, 1 replica, CPU)
  └─ tts-tool:8003 (Kokoro, 1 replica, CPU)
```

- Private Hugging Face LoRA adapter: `TheSteve0/stardew-vision-qwen-tool-select-v1`
  at revision **`73cb70b1718e2a09af55d823701fcd26b3c6a333`**. An operator-provided
  `huggingface-adapter` Secret with a `token` key must have access to this repo;
  never commit credentials.
- API/model ID: `stardew-vlm-finetuned` (not `qwen-base`).
- Digest-pinned application images in the manifests: coordinator **v0.8.2**,
  unified OCR **v0.3.5**, TTS **v0.4.0**. Use the committed digests, not `latest`.
- Model manifests: `configs/serving/openshift/vllm-finetuned/`; shared chat
  template: `configs/serving/openshift/02-configmap-chat-template.yaml`.
- `31-deployment-coordinator-finetuned.yaml` owns the sole primary Route
  `stardew-vision`, targeting `coordinator-finetuned`; no separate route-switch
  manifest or base-model deployment is needed.

From the repository root, after completing the prerequisites in the
[canonical OpenShift deployment guide](configs/serving/openshift/README.md):

```bash
./deploy/deploy-to-openshift.sh
```

This wrapper invokes `configs/serving/openshift/deploy.sh`. Follow that guide for
storage topology, download/hash verification, readiness checks, and migration.
Do not recursively apply the manifest directory. Hash verification establishes
artifact identity, not model quality; historical evaluation accuracy must not be
attributed to this pinned adapter without fresh evaluation.


Historical OpenShift permission, OneDNN, and model caching lessons are retained
in [LESSONS_LEARNED.md](LESSONS_LEARNED.md). Their old image tags and timings are
not current deployment configuration or newly measured performance.

## Overall intstructions
## Bash Conventions
- Do not append `| tail -N` or `| head -N` to commands unless the output is expected to exceed 500 lines

