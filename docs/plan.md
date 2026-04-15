# Stardew Vision: Project Plan

**Last updated**: 2026-04-13
**Talk deadline**: ~1 month
**Status**: ✅ **Phase 1 MVP DEPLOYED TO PRODUCTION** — Full agent loop operational on OpenShift AI. Pierre's shop OCR working end-to-end with audio output. Performance: ~5-7s per request (models cached in memory). **NEXT**: Phase 2 fine-tuning — train Qwen on multi-screen recognition and improved narration quality.

**Phase 1 Completion Summary**:
- ✅ Extraction tool: PaddleOCR + OpenCV template matching (93% field accuracy, 9/9 tests passing)
- ✅ Agentic loop: FastAPI runtime + Qwen reasoner via vLLM (ADR-009, ADR-011)
- ✅ TTS integration: Kokoro TTS with natural-sounding voice
- ✅ OpenShift deployment: Microservices architecture on OpenShift AI (ADR-012)
- ✅ Model caching: PaddleOCR instance cached in memory (~2s per request after warmup)
- ✅ Error handling: Screenshots saved to PVC, comprehensive timing logs
- ✅ Tool calling: Custom chat template for Qwen via KServe ConfigMap

**CURRENT FOCUS**: Phase 2 Fine-Tuning
- Collect multi-screen-type training data (Pierre's shop, TV dialog, inventory tooltip)
- Annotate screenshots with expected tool calls and narrations
- Fine-tune Qwen2.5-VL-7B on screen classification + tool dispatch
- Evaluate fine-tuned model vs. zero-shot baseline
- Deploy fine-tuned model to OpenShift AI (replace base model)

**Note**: Training, dataset preparation, and evaluation now live in the **[stardew-vision-training](https://github.com/thesteve0/stardew-vision-training)** repository. This repo contains application/serving code only.

## vLLM Start Command (Run on Host Machine)

**Architecture Decision (2026-04-03):** vLLM runs in Docker container on the **host machine** (not in devcontainer) due to gfx1151 (Strix Halo) ROCm compatibility. The devcontainer connects to vLLM via forwarded port 8001.

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
  -e HF_TOKEN=$HF_TOKEN \
  rocm/vllm:rocm7.12.0_gfx1151_ubuntu24.04_py3.12_pytorch_2.9.1_vllm_0.16.0 \
  vllm serve Qwen/Qwen2.5-VL-7B-Instruct \
  --dtype float16 \
  --port 8000 \
  --max-model-len 4096 \
  --limit-mm-per-prompt '{"image": 1}' \
  --enable-auto-tool-choice \
  --tool-call-parser hermes
```

**Startup time:** ~5-8 minutes (model loading + encoder cache profiling for VLM)

**Test server is running:**
```bash
# From host
curl http://localhost:8001/v1/models

# From devcontainer (after rebuild with forwarded ports)
curl http://localhost:8001/v1/models
```

Expected response: JSON with `"id": "Qwen/Qwen2.5-VL-7B-Instruct"`

If tool calls don't fire during testing, try `--tool-call-parser qwen2_5`.

This is the authoritative project plan. It is referenced from `CLAUDE.md`. Update this document as decisions change; use the ADRs in `docs/adr/` to document *why* each decision was made.

---

## Project Goals

1. **Accessibility tool**: Visually impaired (but not blind) Stardew Valley players encounter UI panels they cannot read clearly. They take a screenshot, upload it, and hear the panel contents read aloud.
2. **Conference talk artifact**: A live demo and complete codebase used in talks/workshops teaching AI practitioners how to apply VLMs, agent/tool-calling patterns, OCR, and TTS for accessibility use cases.

**Primary user**: A player whose vision impairment makes reading small game text difficult. They take a screenshot on their iPad or PC, upload it, and hear the panel contents described in audio.

**MVP target**: Pierre's General Store — when a player is looking at an item to purchase, the app reads the item name, description, price per unit, quantity selected, and total cost.

---

## Architecture Overview

FastAPI is the **agent runtime** — it manages the loop, executes tool calls, holds the base64 image, and handles error logging. Qwen is the **reasoner** — it decides what to call, evaluates results, applies corrections, and assembles narration. This is the same relationship as Claude Code (shell/runtime) and Claude LLM (reasoner).

```
User uploads screenshot (iPad or browser)
  |
  v
FastAPI POST /analyze  (port 8000)
  encodes image → base64, holds it for the request lifetime
  |
  v
═══════════════════════════════════════════════════════════════
  AGENT LOOP  (raw OpenAI client; no agent framework)
═══════════════════════════════════════════════════════════════

  Turn 1 — Screen recognition + extraction (or immediate fallback)
  FastAPI → Qwen: image + system prompt + tool list

  Path A — Recognized screen:
  Qwen → tool_call: crop_pierres_detail_panel  ─────> OpenCV + PaddleOCR [Phase 1 MVP ✓]
                                                        Returns: {name, description,
                                                                  price_per_unit,
                                                                  quantity_selected,
                                                                  total_cost,
                                                                  energy, health}
  Turn 2 — Quality check + correction (Path A only)
  Qwen reviews OCR result:
    • Silently fixes recoverable typos using language knowledge
    • If unresolvable: sets has_errors=true in final JSON
  Qwen → FastAPI: {"narration": "...", "has_errors": false|true}

  Path B — Unrecognized screen (no tool call):
  Qwen → FastAPI: {"narration": "I have not been trained to recognize that screen...",
                   "has_errors": false}

  LOOP ENDS
  |
  v
FastAPI:
  • has_errors=true → save screenshot → datasets/errors/<timestamp>_<uuid>.png + log
  • Call MeloTTS directly with narration text ─────> WAV bytes
  |
  v
FastAPI response  (audio/wav, autoplay)
  |
  v
Browser <audio> element plays immediately
```

Phase 2 and 3 tools slot into the same loop:
- `crop_tv_dialog(image_b64)` → `{"text": str}` [Phase 2]
- `crop_inventory_tooltip(image_b64)` → `{"name", "description", "sell_price"}` [Phase 3]

**Key architectural properties**:
- The orchestrator VLM uses GPU for vision reasoning only. Text extraction (OpenCV + PaddleOCR) and TTS (MeloTTS) run on CPU.
- TTS is called directly by FastAPI — it is not a Qwen tool call. Qwen's only job is to return `{"narration": "...", "has_errors": bool}`.
- Qwen returns structured JSON enforced by fine-tuning. FastAPI handles `has_errors` logging and MeloTTS dispatch deterministically.
- New screen types are added by writing one extraction function and adding training examples — no loop changes needed.
- See [ADR-011](adr/011-agent-loop-refinements.md) for the rationale behind these design choices.

---

## Key Architectural Decisions

Full rationale in `docs/adr/`. Summary:

| Decision | Choice | ADR |
|---|---|---|
| VLM Orchestrator | `Qwen/Qwen2.5-VL-7B-Instruct` (FP16, LoRA via PEFT) — screen classifier + tool dispatcher | [ADR-001](adr/001-vlm-selection.md), [ADR-009](adr/009-agent-tool-calling-architecture.md) |
| VLM Comparison | `HuggingFaceTB/SmolVLM2-2.2B-Instruct` — same orchestrator task, smaller model | [ADR-001](adr/001-vlm-selection.md) |
| Pipeline architecture | Agent/tool-calling: orchestrator VLM + CPU extraction agents | [ADR-009](adr/009-agent-tool-calling-architecture.md), [ADR-011](adr/011-agent-loop-refinements.md) |
| Extraction layer | OpenCV template matching + PaddleOCR PP-OCRv5 (CPU-only) | [ADR-010](adr/010-screen-region-extraction.md), [docs/ocr-choice.md](ocr-choice.md) |
| TTS | MeloTTS-English (local, CPU/GPU-optional, MIT) | [ADR-003](adr/003-tts-selection.md) |
| Repo structure | Single monorepo | [ADR-004](adr/004-repo-structure.md) |
| Serving | vLLM locally (port 8001, tool-calling); KServe on OpenShift AI | [ADR-005](adr/005-serving-strategy.md) |
| Distributed training | Ray Train on OpenShift AI (KubeRay); KFP post-MVP | [ADR-005](adr/005-serving-strategy.md) |
| Feature store | Filesystem/JSONL for MVP; Feast Phase 2 | [ADR-006](adr/006-feature-store-strategy.md) |
| Experiment tracking | MLFlow (local dev + OpenShift AI) | Confirmed |
| Fine-tuning method | LoRA (PEFT), FP16 only — ROCm 7.2 constraint | Confirmed |
| Web framework | FastAPI + static HTML (no JS framework) | Confirmed |

---

## Hardware and Environment

- **Hardware**: AMD Strix Halo (gfx1151) — up to ~128GB unified memory
- **ROCm**: 7.2 (see `template_docs/notesOnRocm72.md` for all constraints)
- **PyTorch**: 2.9.1 (ROCm-optimized, Flash Attention v2 support)
- **Python**: 3.12 (fixed by devcontainer)
- **CRITICAL**: FP16 is the only officially validated precision. No BF16 (except as experimental test for SmolVLM2), no INT4, no INT8.
- **Required env vars** (already in devcontainer.json): `ROCBLAS_USE_HIPBLASLT=1`, `HIP_VISIBLE_DEVICES=0`
- **torch.compile**: Use `mode="reduce-overhead"` for inference; reduces cold-start from ~60s to ~15s
- **PaddleOCR compatibility**: Use `paddlepaddle==3.2.0` with `paddleocr>=3.4.0` (PaddlePaddle 3.3.0 has OneDNN PIR conversion bug)

---

## Repository Structure

**This repository** (application/serving):

```
stardew-vision/
├── .devcontainer/             # ROCm devcontainer config (local development)
├── services/                  # Microservices architecture
│   ├── coordinator/           # Agent loop runtime (FastAPI)
│   │   ├── Dockerfile
│   │   ├── pyproject.toml
│   │   └── stardew_coordinator/
│   ├── ocr-tool/              # Pierre's shop OCR extraction
│   │   ├── Dockerfile
│   │   ├── pyproject.toml
│   │   ├── assets/templates/  # OpenCV templates (self-contained)
│   │   └── stardew_ocr/
│   └── tts-tool/              # Text-to-speech synthesis
│       ├── Dockerfile
│       ├── pyproject.toml
│       └── stardew_tts/
├── deploy/                    # OpenShift manifests, Docker configs
├── configs/                   # Serving configs (KServe, vLLM, output schemas)
│   └── serving/
│       └── openshift/
├── docs/                      # ADRs, deployment guides
│   ├── adr/                   # Architecture Decision Records
│   ├── plan.md                # This file
│   └── ...
├── tests/                     # Pytest suite
│   └── fixtures/              # Test screenshots
├── demos/                     # Conference demo examples
├── models/                    # Host volume — fine-tuned checkpoints (not in git)
├── pyproject.toml             # Dev dependencies
└── CLAUDE.md                  # Claude Code context
```

**Training repository** ([stardew-vision-training](https://github.com/thesteve0/stardew-vision-training)):

```
stardew-vision-training/
├── datasets/                  # Screenshots, annotations, sprites
├── fine_tuning/               # LoRA training scripts (Qwen2.5-VL)
├── evaluation/                # Quality metrics, benchmarks
├── synthetic_data/            # LLM-based data augmentation
├── experiments/               # MLFlow tracking
└── scripts/                   # Annotation, data prep tools
```

---

## Data Strategy

Full detail in `docs/data-collection-plan.md`.

**Track 1 — Pierre's shop screenshots** (Phase 1, immediate): Collect screenshots of Pierre's shop with various items selected. Annotate with expected extracted fields (name, description, price, quantity, total). Used to evaluate OCR extraction accuracy and train orchestrator.

**Track 2 — Screen-type diversity screenshots** (Phase 1 + 2): Collect screenshots of different screen types (Pierre's shop, TV, inventory tooltip, crafting menu, chest) for orchestrator classifier training. Label: `{ image_id, screen_type }`. Minimum 50 examples per screen type for the orchestrator fine-tuning set.

**Annotation schema**:
```json
{
  "image_hash": "<sha256>",
  "original_file_name": "pierre_shop_001.png",
  "screen_type": "pierre_shop",
  "expected_extraction": {
    "name": "Parsnip Seeds",
    "description": "Plant these in the spring. Takes 4 days to mature.",
    "price_per_unit": 20,
    "quantity_selected": 5,
    "total_cost": 100
  }
}
```

Note: `image_hash` is SHA256 (content-based ID), not UUID4. `original_file_name` is required for traceability.

**Dataset splits**: 65% train / 20% val / 15% test. Test set must include images where left panel selection ≠ right panel detail (critical edge case — use `--manual-test-images` in `scripts/generate_splits.py`). Split manifests are plain `.txt` files in `datasets/splits/pierre_shop/` — one filename per line (not JSONL). Training code joins against `datasets/annotated/annotations.jsonl`.

---

## Evaluation Framework

Full detail in `docs/evaluation-rubric.md`.

### Metrics

| Metric | Description | MVP Target |
|---|---|---|
| Screen classification accuracy | % of screenshots where correct tool is dispatched | >= 95% (fine-tuned) |
| Field extraction accuracy | % of extracted fields matching ground truth (exact for int, fuzzy >= 90 for str) | >= 90% |
| JSON validity rate | % of extraction calls producing schema-valid JSON | >= 99% |
| End-to-end narration quality | Human spot-check: audio correctly describes panel | Pass/fail spot check |

All metrics logged to MLFlow. Baseline (zero-shot orchestrator) vs. fine-tuned comparison is the core talk narrative.

---

## Fine-Tuning

### Qwen2.5-VL-7B (LoRA via PEFT) — Orchestrator

Config: `configs/training/finetune_config.yaml`

**Task**: Screen classification + tool dispatch. Training data: `(screenshot_image, tool_call_response)` pairs.

Key settings:
- `dtype: float16` — FP16 only (ROCm 7.2 constraint)
- `bf16: false` — not validated on Strix Halo
- LoRA: `r=16, alpha=32`, target modules: all attention + FFN projection layers
- Effective batch size 16 (batch=2, grad_accum=8)
- Apply `torch.compile(mode="reduce-overhead")` after LoRA init

### SmolVLM2-2.2B (TRL SFTTrainer) — Comparison Orchestrator

Config: `configs/training/finetune_config_smolvlm2.yaml`

**Task**: Same orchestrator task. Research question: does 81-token image compression prevent reliable screen type classification?

Key differences:
- Uses TRL `SFTTrainer` (wraps PEFT internally)
- LoRA: `r=8, alpha=8` (smaller rank for smaller model)
- Prefers BF16 but will be tested FP16 first; document result in ADR-001 update

### Training Infrastructure

- Local: devcontainer (first runs, hyperparameter search)
- Scale-out: Ray Train on OpenShift AI via KubeRay (post-MVP)
- MLFlow tracking: local `mlruns/` → remote MLFlow server on OpenShift for scale-out runs
- Checkpoints: saved to `models/fine-tuned/` (host volume, persists across container rebuilds)

---

## Local vs. OpenShift AI

| Component | Devcontainer (local) | OpenShift AI |
|---|---|---|
| Screenshot collection + annotation | Primary | — |
| Zero-shot baseline eval | Primary | — |
| First fine-tuning runs (LoRA) | Primary | — |
| Scale-out fine-tuning (Ray Train) | — | Post-MVP |
| MLFlow tracking | Dev | Production |
| vLLM serving (dev/test) | Port 8001 | — |
| vLLM serving (production) | — | KServe |
| Web app (dev) | Port 8000 | — |
| Web app (production) | — | OpenShift AI |
| Jupyter notebooks | Port 8888 | — |

**Conference talk demo**: runs entirely locally. OpenShift AI appears in the architecture diagram; live deployment is post-MVP.

---

## Implementation Sequence

### Phase 1: Pierre's Shop MVP

1. ✅ Rename `src/stardew-vision/` → `src/stardew_vision/` (already done)
2. ✅ Update `pyproject.toml` with new dependencies (opencv-python, paddleocr, openai) (2026-03-20)
3. 🔄 Collect Pierre's shop screenshots and screen-type diversity screenshots (see `docs/data-collection-plan.md`) (1 screenshot collected)
4. ✅ Build anchor template: `datasets/assets/templates/pierres_detail_panel_corner.png` (2026-03-20)
5. ✅ Write `src/stardew_vision/tools/crop_pierres_detail_panel.py` (OpenCV crop + PaddleOCR + parser) (2026-03-20)
6. ✅ Write unit tests: `tests/test_tools.py` with fixture screenshots (8/8 tests passing) (2026-03-20)
7. ✅ Add `ocr_raw` structured debug output to `crop_pierres_detail_panel` (debug=True mode) (2026-04-03)
8. 🔄 Write `src/stardew_vision/tts/synthesize.py` (MeloTTS wrapper) — **stubbed, not wired**
9. ✅ Write `src/stardew_vision/serving/inference.py` (FastAPI agent loop: raw OpenAI client, multi-turn dispatch, error logging) (2026-04-03)
10. ✅ Write tool definitions in OpenAI function-calling format (`src/stardew_vision/tools/__init__.py`) — `image_b64` NOT in definitions, FastAPI injects at dispatch (2026-04-03)
11. 🔄 Run zero-shot baseline: does Qwen2.5-VL-7B run the full loop correctly zero-shot? (**NOT YET TESTED — desktop**)
12. Fine-tune orchestrator on multi-turn conversation training data; log to MLFlow
13. ✅ Write `src/stardew_vision/webapp/app.py` + `routes.py` + `index.html` (2026-04-03)
14. End-to-end integration test: upload Pierre's shop screenshot → audio plays
15. Add ports 8000, 8001 to `devcontainer.json` `forwardPorts`

### Phase 2: TV Screen Dialog

14. Collect TV screen screenshots; annotate with expected text
15. Write `src/stardew_vision/tools/crop_tv_dialog.py`
16. Add `crop_tv_dialog` to orchestrator tool list; add training examples
17. Fine-tune or few-shot the orchestrator on expanded tool set

### Phase 3: Inventory Tooltips

18. Collect inventory tooltip screenshots; annotate
19. Write `src/stardew_vision/tools/crop_inventory_tooltip.py`
20. Add to orchestrator; fine-tune

### Serve + Polish (all phases)

21. Configure vLLM local serving with tool-calling support
22. Write `src/stardew_vision/models/finetune_smolvlm.py` (TRL SFTTrainer)
23. Run SmolVLM2 baseline + fine-tuning; add to comparison notebook
24. Polish `notebooks/04_evaluation_results.ipynb` for talk
25. Write `scripts/push_to_hf.py`; push dataset + model to HuggingFace
26. Write OpenShift AI serving manifests

### Post-MVP

- Ray Train on OpenShift AI for distributed fine-tuning
- KubeFlow Pipelines for orchestration
- Feast feature store (Phase 2 per ADR-006)
- Chest/inventory grid reading (revisit ADR-007, ADR-008 if prioritized)

---

## Dependencies

Add to `pyproject.toml`:

```toml
# VLM fine-tuning
"transformers>=4.46.0",
"peft>=0.13.0",
"accelerate>=1.0.0",
"trl>=0.12.0",            # SmolVLM2 SFTTrainer
"datasets>=3.0.0",
"huggingface-hub>=0.25.0",
# Experiment tracking
"mlflow>=2.17.0",
# TTS
# MeloTTS (install from GitHub - see ADR-003)
"soundfile>=0.12.0",
# Web app
"fastapi>=0.115.0",
"uvicorn[standard]>=0.32.0",
"python-multipart>=0.0.12",
# vLLM client (tool-calling format)
"openai>=1.50.0",
# Extraction agents
"opencv-python>=4.9.0",
"paddlepaddle==3.2.0",   # DO NOT UPGRADE - 3.3.0 has OneDNN PIR bug
"paddleocr>=3.4.0",
# Data / evaluation
"rapidfuzz>=3.9.0",
"jsonschema>=4.23.0",
"evaluate>=0.4.0",
"Pillow>=10.0.0",         # also in ROCm container — keep in exclude-dependencies
```

Preserve all entries in `[tool.uv] exclude-dependencies` — these are ROCm-provided packages that must not be overwritten.

---

## HuggingFace Hub Deliverables

- **Dataset**: `{username}/stardew-screen-vision-dataset` — annotated screenshots + dataset card
- **Model**: `{username}/stardew-vision-vlm` — merged fine-tuned orchestrator + model card with eval metrics

Both managed via `scripts/push_to_hf.py`. Model card auto-generated from MLFlow run metadata.

---

## End-to-End Verification Checklist

The MVP is working when all of the following pass:

- [x] `src/stardew_vision/tools/crop_pierres_detail_panel.py` extracts correct fields from a fixture screenshot (2026-03-20)
- [x] `pytest tests/test_tools.py` — all extraction unit tests pass (9/9 passing, 2026-04-03)
- [x] Agent loop files created and import-verified: `tools/__init__.py`, `serving/inference.py`, `webapp/app.py`, `webapp/routes.py`, `webapp/static/index.html` (2026-04-03)
- [ ] Zero-shot orchestrator runs full agentic loop (extract → check → correct → TTS) for a Pierre's shop screenshot (**next**)
- [ ] Real MeloTTS wired in `src/stardew_vision/tts/synthesize.py`; TTS stub replaced
- [ ] `/analyze` returns `audio/wav` (currently returns JSON)
- [ ] Fine-tuned orchestrator: screen classification accuracy >= 95%, correction accuracy >= 80% on validation set
- [x] Field extraction accuracy >= 90% on Pierre's shop validation screenshots (93% across 22 images, 2026-04-03)
- [ ] `vllm serve Qwen/Qwen2.5-VL-7B-Instruct --dtype float16 --port 8001 --enable-auto-tool-choice --tool-call-parser hermes` starts
- [ ] `uvicorn src.stardew_vision.webapp.app:app --port 8000` starts
- [ ] Browser upload of a Pierre's shop screenshot → audio plays with correct item description
- [x] `pytest tests/` — all tests pass (9/9 tests passing, 2026-04-03)
