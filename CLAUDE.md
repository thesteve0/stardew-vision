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
├── ocr-tool/        # Pierre's shop OCR extraction (self-contained microservice)
│   ├── stardew_ocr/
│   └── assets/templates/  # OpenCV templates (baked into container)
└── tts-tool/        # Text-to-speech synthesis
    └── stardew_tts/
deploy/              # OpenShift manifests, Docker configs
configs/             # Serving configs (KServe, vLLM, output schemas)
docs/                # ADRs, plan, deployment guides
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

- **Pipeline**: Full agentic loop. FastAPI is the agent runtime (manages the loop, executes tools, holds base64 image, logs errors). Qwen2.5-VL-7B is the reasoner (classifies screen, calls extraction tool, checks for failures/typos, applies corrections, assembles narration, calls TTS). The loop runs until Qwen signals done — at most 4 turns for the happy path. See [ADR-009](docs/adr/009-agent-tool-calling-architecture.md).
- **Agent loop tools**: `crop_pierres_detail_panel(image_b64, debug=False)` → OCR JSON; `crop_pierres_detail_panel(image_b64, debug=True)` → OCR JSON + `ocr_raw`; `text_to_speech(text)` → WAV bytes.
- **Error handling**: Qwen silently corrects recoverable typos. For unresolvable failures Qwen sets `has_errors=True`; coordinator service saves the screenshot to mounted PVC and logs the failure. Narration always includes whatever partial data was extracted.
- **Extraction layer**: OpenCV template matching for UI region location; PaddleOCR (PP-OCRv5) for text extraction; both CPU-only. Chosen over EasyOCR for faster CPU throughput, SOTA accuracy, and correct capitalization preservation. See [ADR-010](docs/adr/010-screen-region-extraction.md) and [docs/ocr-choice.md](docs/ocr-choice.md).
- **MVP screen type**: Pierre's General Store detail panel — name, description, price per unit, quantity selected, total cost.
- **Fine-tuning**: Orchestrator VLM fine-tuned on `(screenshot, tool_call_response)` pairs. LoRA via PEFT for Qwen2.5-VL-7B; TRL SFTTrainer for SmolVLM2-2.2B. Both in FP16. See [ADR-001](docs/adr/001-vlm-selection.md).
- **Configuration**: YAML files in `configs/training/` for hyperparameters; `configs/output_schema.json` for per-screen-type extraction JSON schemas.
- **Checkpointing**: LoRA adapters saved to `models/fine-tuned/{run_name}/` (host volume). Naming: `{model_short_name}-{run_type}-v{N}`.
- **Experiment tracking**: MLFlow; local `mlruns/`; run naming `{model_short_name}-{run_type}-v{N}`.
- **Serving**: vLLM on port 8001 (OpenAI-compatible API with tool-calling); FastAPI web app on port 8000. Client uses `openai` library — same code works for local and OpenShift AI endpoints. See [ADR-005](docs/adr/005-serving-strategy.md).
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

## Local Development Architecture

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

Use `deploy/start_vllm_host.sh` or run directly:

```bash
# Run this on your host machine (outside devcontainer)
docker run --rm \
  --device=/dev/kfd \
  --device=/dev/dri \
  --group-add=video \
  --cap-add=SYS_PTRACE \
  --security-opt seccomp=unconfined \
  --ipc=host \
  -p 8001:8000 \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  -v "${PWD}/configs/serving/qwen2_5_vl_tool_template.jinja":/chat_template.jinja \
  -e HF_TOKEN=$HF_TOKEN \
  rocm/vllm:rocm7.12.0_gfx1151_ubuntu24.04_py3.12_pytorch_2.9.1_vllm_0.16.0 \
  vllm serve Qwen/Qwen2.5-VL-7B-Instruct \
  --dtype float16 \
  --port 8000 \
  --max-model-len 4096 \
  --limit-mm-per-prompt '{"image": 1}' \
  --enable-auto-tool-choice \
  --tool-call-parser hermes \
  --chat-template /chat_template.jinja
```

**Startup time:** ~5-8 minutes (model loading + encoder cache profiling)

**vLLM Configuration Reference:** https://raw.githubusercontent.com/vllm-project/vllm/refs/heads/main/vllm/engine/arg_utils.py (for `--limit-mm-per-prompt` and other engine args)

**Test from host:**
```bash
curl http://localhost:8001/v1/models
```

**Test from devcontainer (after rebuild with forwarded ports):**
```bash
curl http://localhost:8001/v1/models
```

Expected response: JSON with model info including `"id": "Qwen/Qwen2.5-VL-7B-Instruct"`

---

## OpenShift AI Deployment Architecture

**Status**: Deployed and operational as of 2026-04-13

The application is deployed on OpenShift AI as a microservices architecture with the following components:

### Architecture Overview

```
Internet → OpenShift Route (3m timeout)
  ↓
Coordinator Service (port 8000, 1 replica)
  ├→ OCR Tool Service (port 8002, 1 replica, CPU-only)
  ├→ TTS Tool Service (port 8003, 1 replica, CPU-only)
  └→ vLLM Predictor (KServe InferenceService, GPU)
```

### Services

**1. vLLM Serving (KServe InferenceService)**
- Model: `Qwen/Qwen2.5-VL-7B-Instruct` from HuggingFace
- Runtime: Red Hat AI Inference Service (RHAI IS) vLLM CUDA runtime
- GPU: 1× NVIDIA GPU, 32Gi memory
- Port: 8080 (internal), served at `http://stardew-vlm-predictor:8080/v1`
- Custom chat template: Mounted from ConfigMap (Hermes-compatible tool calling format)
- vLLM args: `--max-model-len=4096 --limit-mm-per-prompt={"image":1} --enable-auto-tool-choice --tool-call-parser=hermes`

**2. OCR Tool Service**
- Image: `ghcr.io/thesteve0/stardew-ocr-tool:v0.12.0`
- Resources: 1000m CPU, 4Gi memory request, 2500m CPU, 8Gi memory limit
- PVC: `paddlex-cache` (2Gi) for PaddleOCR models
- Init container: Pre-downloads models on pod startup
- Model caching: PaddleOCR instance cached in memory (first request ~30s, subsequent ~2s)
- Environment: `FLAGS_use_mkldnn=0` (OneDNN disabled for CPU portability)

**3. TTS Tool Service**
- Image: `ghcr.io/thesteve0/stardew-tts-tool:v0.4.0`
- Resources: 1000m CPU, 1Gi memory request, 2000m CPU, 2Gi memory limit
- PVC: `hf-cache` (2Gi, shared) for Kokoro TTS models
- Init container: Pre-downloads models on pod startup

**4. Coordinator Service**
- Image: `ghcr.io/thesteve0/stardew-coordinator:v0.6.0`
- Resources: 500m CPU, 512Mi memory request, 1000m CPU, 1Gi memory limit
- ConfigMap: `service-endpoints` (OCR_TOOL_URL, TTS_TOOL_URL, VLLM_BASE_URL, VLLM_MODEL)
- PVC: `error-screenshots` (5Gi) for failed extractions
- Route timeout: 3 minutes (annotation: `haproxy.router.openshift.io/timeout: 3m`)

### Persistent Volumes

1. **paddlex-cache** (2Gi, RWO): PaddleOCR + PaddleX models
2. **hf-cache** (2Gi, RWO): HuggingFace models for TTS
3. **error-screenshots** (5Gi, RWO): Failed extractions with debug output

### Performance Characteristics

**First request after pod restart:**
- VLM inference: ~1s
- OCR (with model loading): ~30s
- TTS: ~3s
- **Total**: ~35-40s

**Subsequent requests (models cached in memory):**
- VLM inference: ~1s
- OCR (cached instance): ~2s
- TTS: ~3s
- **Total**: ~5-7s

### Deployment Commands

```bash
# Create namespace
kubectl create namespace stardew-vision

# Deploy in order (dependencies matter)
kubectl apply -f configs/serving/openshift/02-pvc-paddlex-cache.yaml
kubectl apply -f configs/serving/openshift/03-pvc-hf-cache.yaml
kubectl apply -f configs/serving/openshift/04-pvc-errors.yaml
kubectl apply -f configs/serving/openshift/01-configmap-endpoints.yaml
kubectl apply -f configs/serving/openshift/vllm/04-configmap-chat-template.yaml
kubectl apply -f configs/serving/openshift/vllm/02-servingruntime-with-template.yaml
kubectl apply -f configs/serving/openshift/vllm/03-inferenceservice.yaml
kubectl apply -f configs/serving/openshift/10-deployment-ocr-tool.yaml
kubectl apply -f configs/serving/openshift/20-deployment-tts-tool.yaml
kubectl apply -f configs/serving/openshift/30-deployment-coordinator.yaml
```

### Monitoring and Debugging

**Check pod status:**
```bash
kubectl get pods -n stardew-vision
```

**View coordinator logs with timing:**
```bash
kubectl logs -n stardew-vision deployment/coordinator -f | grep "⏱️"
```

**Check OCR tool logs:**
```bash
kubectl logs -n stardew-vision deployment/ocr-tool -f
```

**Test OCR service directly:**
```bash
python data/scripts/evaluation/test_ocr_service.py datasets/pierre_shop/images/IMG_7710.jpg \
  --url https://stardew-vision-stardew-vision.apps.your-cluster.com
```

**Access web UI:**
Route URL available at: `https://stardew-vision-stardew-vision.apps.<cluster-domain>`

### Critical Lessons Learned

1. **OpenShift Random UID**: Containers run as random UIDs (e.g., 1000860000). Cannot write to root directories. All cache/temp directories must point to `/tmp` or mounted PVCs. Environment variables must be set in Python code via `os.environ.setdefault()` before imports, not just in Dockerfile `ENV`.

2. **MKLDNN/OneDNN CPU Incompatibility**: PaddlePaddle compiled with Intel MKLDNN optimizations causes `SIGTERM` on incompatible CPUs. Must disable with `FLAGS_use_mkldnn=0` for portability. Cost: 2-4x slower CPU inference.

3. **Model Instance Caching**: Loading PaddleOCR from disk takes ~30s per request. Cache the instance in a module-level variable (`_OCR_INSTANCE = None`) to reduce subsequent requests to ~2s.

4. **Route Timeout**: Default OpenShift Route timeout is 30s. First request takes ~35-40s with model loading. Must set `haproxy.router.openshift.io/timeout: 3m` annotation.

5. **HuggingFace Cache**: PaddleX downloads models from HuggingFace. Must set `HF_HOME=/cache/huggingface` or downloads fail with "Permission denied (os error 13)".

See [LESSONS_LEARNED.md](LESSONS_LEARNED.md) for detailed troubleshooting guide and [ADR-012](docs/adr/012-openshift-deployment-architecture.md) for full architecture documentation.

---

## Overall intstructions
## Bash Conventions
- Do not append `| tail -N` or `| head -N` to commands unless the output is expected to exceed 500 lines

