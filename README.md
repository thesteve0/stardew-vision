# Stardew Vision

An accessibility tool that lets visually impaired Stardew Valley players upload a screenshot of an in-game UI panel and hear its contents read aloud. Built as a conference talk artifact demonstrating VLMs, agentic tool-calling, OCR, and TTS for practical accessibility use cases.

## Problem Statement

Stardew Valley's UI text is small and rendered in pixel-art fonts. Players with vision impairments can read the game but struggle with small details — item names, prices, descriptions. They take a screenshot and want to hear those details narrated back to them.

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

## Historical Phase 1 Dataset

Training, dataset preparation, and current evaluation live in
[stardew-vision-training](https://github.com/thesteve0/stardew-vision-training).
The following describes the original Phase 1 local dataset:

- **Source**: Screenshots taken from Stardew Valley gameplay (Pierre's shop, iPad + PC)
- **Size**: 22 annotated Pierre's shop screenshots (Phase 1)
- **Location**: `datasets/pierre_shop/` (host volume — not committed to git)
- **Annotation schema**: JSONL with `image_id`, `screen_type`, `expected_extraction` fields

## Project Structure

```
services/
  coordinator/  # Fine-tuned classification, OCR dispatch, narration, TTS
  ocr-tools/    # Unified Pierre's shop, TV dialog, caught-fish extraction
  tts-tool/     # Kokoro synthesis
src/stardew_vision/  # Historical local implementation
  tools/        # Extraction agents: crop_pierres_detail_panel, etc.
  tts/          # Historical local TTS wrapper
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

Use the [canonical deployment guide](configs/serving/openshift/README.md) and
`./deploy/deploy-to-openshift.sh`. The verified architecture and pinned adapter
are described above. The original `stardew-vision` Route serves the fine-tuned
coordinator; OCR, TTS, and the predictor remain internal-only.

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

### Run the current application

For the complete fine-tuned application, follow
[QUICKSTART.md](QUICKSTART.md). Historical local ROCm experiments are documented
in [vLLM notes](docs/vllm-notes.md); they are not the production deployment.

## Status

| Component | Status |
|-----------|--------|
| Pierre's shop OCR extraction | ✅ Complete — 8/8 tests passing |
| Agent loop (FastAPI + Qwen) | ✅ Complete — deployed to production |
| TTS tool (Kokoro) | ✅ Complete — deployed to production |
| Web app | ✅ Complete — deployed to production |
| Fine-tuning (LoRA) | Deployed — pinned private Hugging Face adapter |
| **Production Deployment** | ✅ **Live on OpenShift AI** |

**Deployment URL:** Obtain the current host from the original Route:

```bash
oc get route stardew-vision -n stardew-vision -o jsonpath='{.spec.host}'
```

See the [canonical deployment guide](configs/serving/openshift/README.md) for complete deployment details.

## Key Technical Decisions

| Decision | Choice |
|----------|--------|
| VLM orchestrator | Fine-tuned Qwen2.5-VL-7B-Instruct + pinned LoRA adapter |
| Agent loop | Raw OpenAI client — no framework |
| OCR | PaddleOCR PP-OCRv5, CPU-only |
| TTS | Kokoro (CPU, MIT license) |
| Serving | vLLM 0.13 + KServe on OpenShift AI (production) |
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
