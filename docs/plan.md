# Stardew Vision: Project Plan

**Last updated**: 2026-03-20
**Talk deadline**: 1-2 months
**Status**: Phase 1 extraction tool complete — Pierre's shop OCR working with 85-99% confidence

This is the authoritative project plan. It is referenced from `CLAUDE.md`. Update this document as decisions change; use the ADRs in `docs/adr/` to document *why* each decision was made.

---

## Project Goals

1. **Accessibility tool**: Visually impaired (but not blind) Stardew Valley players encounter UI panels they cannot read clearly. They take a screenshot, upload it, and hear the panel contents read aloud.
2. **Conference talk artifact**: A live demo and complete codebase used in talks/workshops teaching AI practitioners how to apply VLMs, agent/tool-calling patterns, OCR, and TTS for accessibility use cases.

**Primary user**: A player whose vision impairment makes reading small game text difficult. They take a screenshot on their iPad or PC, upload it, and hear the panel contents described in audio.

**MVP target**: Pierre's General Store — when a player is looking at an item to purchase, the app reads the item name, description, price per unit, quantity selected, and total cost.

---

## Architecture Overview

```
User uploads screenshot (iPad or browser)
  |
  v
FastAPI POST /analyze  (port 8000)
  |
  v
Orchestrator VLM  (Qwen2.5-VL-7B-Instruct, FP16, ROCm, vLLM port 8001)
  Classifies screen type; returns tool_call response
  |
  +-- tool_call: crop_pierres_detail_panel  -----> OpenCV crop + PaddleOCR  [Phase 1 MVP ✓]
  |                                                  {"name", "description",
  |                                                   "price_per_unit",
  |                                                   "quantity_selected",
  |                                                   "total_cost"}
  |
  +-- tool_call: crop_tv_dialog  ----------------> OpenCV crop + PaddleOCR  [Phase 2]
  |                                                  {"text"}
  |
  +-- tool_call: crop_inventory_tooltip  --------> OpenCV crop + PaddleOCR  [Phase 3]
                                                     {"name", "description",
                                                      "sell_price"}
  |
  v
Narration template (Python string formatting)
  "You are looking at Parsnip Seeds. Plant these in the spring.
   It costs 20 gold each. You have selected 5. Total cost: 100 gold."
  |
  v
MeloTTS synthesis  (CPU, WAV output)
  |
  v
FastAPI response  (audio/wav)
  |
  v
Browser <audio> element plays immediately
```

**Key architectural property**: The orchestrator VLM uses GPU for vision classification only. Text extraction (OpenCV + PaddleOCR) runs on CPU. New screen types are added by writing one extraction function and adding training examples — no architectural changes.

---

## Key Architectural Decisions

Full rationale in `docs/adr/`. Summary:

| Decision | Choice | ADR |
|---|---|---|
| VLM Orchestrator | `Qwen/Qwen2.5-VL-7B-Instruct` (FP16, LoRA via PEFT) — screen classifier + tool dispatcher | [ADR-001](adr/001-vlm-selection.md), [ADR-009](adr/009-agent-tool-calling-architecture.md) |
| VLM Comparison | `HuggingFaceTB/SmolVLM2-2.2B-Instruct` — same orchestrator task, smaller model | [ADR-001](adr/001-vlm-selection.md) |
| Pipeline architecture | Agent/tool-calling: orchestrator VLM + CPU extraction agents | [ADR-009](adr/009-agent-tool-calling-architecture.md) |
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

```
stardew-vision/
├── .devcontainer/             # ROCm devcontainer config (do not modify casually)
├── docs/
│   ├── adr/                   # Architecture Decision Records
│   │   ├── 001-vlm-selection.md
│   │   ├── 002-vlm-role-architecture.md  (Superseded by 009)
│   │   ├── 003-tts-selection.md
│   │   ├── 004-repo-structure.md
│   │   ├── 005-serving-strategy.md
│   │   ├── 006-feature-store-strategy.md
│   │   ├── 007-overlay-detection-strategy.md  (Deferred)
│   │   ├── 008-grid-detection-strategy.md     (Deferred)
│   │   ├── 009-agent-tool-calling-architecture.md
│   │   └── 010-screen-region-extraction.md
│   ├── plan.md                # This file
│   ├── talk-abstract.md       # Conference talk abstract
│   ├── evaluation-rubric.md   # Metrics and thresholds
│   ├── data-collection-plan.md  # Data strategy (screen-type screenshots)
│   └── dataset-guide.md       # Annotation schema + contribution guide
├── datasets/                  # Host volume mount — NOT committed to git
│   ├── assets/
│   │   ├── templates/         # OpenCV anchor templates per screen type
│   │   └── ...
│   ├── raw/                   # Screenshots (screen-type labeled)
│   ├── annotated/             # JSONL annotation files
│   └── splits/                # train/val/test manifests
├── models/                    # Host volume mount — NOT committed to git
│   ├── base/                  # Downloaded base checkpoints
│   └── fine-tuned/            # LoRA adapter checkpoints
├── configs/
│   ├── training/
│   │   ├── finetune_config.yaml           # Qwen2.5-VL-7B LoRA config
│   │   └── finetune_config_smolvlm2.yaml  # SmolVLM2 TRL config
│   ├── output_schema.json                 # Per-screen-type JSON schemas
│   └── serving/
│       ├── vllm_local.yaml
│       └── openshift/
│           ├── serving_runtime.yaml
│           └── inference_service.yaml
├── notebooks/
│   ├── 01_dataset_exploration.ipynb
│   ├── 02_vlm_baseline_comparison.ipynb   # Key talk artifact
│   ├── 03_finetuning_analysis.ipynb
│   └── 04_evaluation_results.ipynb
├── scripts/
│   ├── resolve-dependencies.py  # (exists)
│   ├── collect_screen_screenshots.py  # Guided screenshot collection tool
│   ├── validate_dataset.py
│   ├── run_baseline_eval.py
│   └── push_to_hf.py
├── src/
│   └── stardew_vision/          # Main Python package
│       ├── tools/
│       │   ├── __init__.py          # Tool registry
│       │   ├── crop_pierres_detail_panel.py  # OpenCV crop + EasyOCR
│       │   ├── crop_tv_dialog.py             # Phase 2
│       │   └── crop_inventory_tooltip.py     # Phase 3
│       ├── models/
│       │   ├── vlm_wrapper.py       # Orchestrator VLM inference (tool-calling)
│       │   ├── finetune.py          # LoRA training loop (Qwen)
│       │   └── finetune_smolvlm.py  # TRL SFTTrainer (SmolVLM2)
│       ├── tts/
│       │   └── synthesize.py        # text → WAV bytes via MeloTTS
│       ├── serving/
│       │   └── inference.py         # vLLM OpenAI-client wrapper + tool dispatch
│       └── webapp/
│           ├── app.py               # FastAPI app
│           ├── routes.py            # POST /analyze → audio/wav
│           └── static/
│               └── index.html       # Upload form + audio player
├── tests/
│   ├── fixtures/                    # Test screenshots for unit tests
│   ├── test_tools.py                # Extraction agent unit tests
│   ├── test_vlm_wrapper.py
│   ├── test_tts.py
│   └── test_webapp.py
├── main.py                          # CLI entrypoint
├── pyproject.toml                   # Dependencies (preserve exclude-dependencies)
└── CLAUDE.md                        # Claude Code context (references this file)
```

---

## Data Strategy

Full detail in `docs/data-collection-plan.md`.

**Track 1 — Pierre's shop screenshots** (Phase 1, immediate): Collect screenshots of Pierre's shop with various items selected. Annotate with expected extracted fields (name, description, price, quantity, total). Used to evaluate OCR extraction accuracy and train orchestrator.

**Track 2 — Screen-type diversity screenshots** (Phase 1 + 2): Collect screenshots of different screen types (Pierre's shop, TV, inventory tooltip, crafting menu, chest) for orchestrator classifier training. Label: `{ image_id, screen_type }`. Minimum 50 examples per screen type for the orchestrator fine-tuning set.

**Annotation schema**:
```json
{
  "image_id": "uuid4",
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

**Dataset splits**: 70% train / 15% val / 15% test. Test set = held-out screenshots not used in training.

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
7. Write `src/stardew_vision/models/vlm_wrapper.py` (Qwen2.5-VL-7B orchestrator, tool-calling format)
8. Run zero-shot baseline: does Qwen2.5-VL-7B dispatch the correct tool zero-shot?
9. Fine-tune orchestrator on screen-type training data; log to MLFlow
10. Write `src/stardew_vision/tts/synthesize.py` (MeloTTS)
11. Write `src/stardew_vision/webapp/app.py` + `routes.py` + `index.html`
12. End-to-end integration test: upload Pierre's shop screenshot → audio plays
13. Add ports 8000, 8001 to `devcontainer.json` `forwardPorts`

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
- [x] `pytest tests/test_tools.py` — all extraction unit tests pass (8/8 passing, 2026-03-20)
- [ ] Zero-shot orchestrator correctly dispatches `crop_pierres_detail_panel` for a Pierre's shop screenshot
- [ ] Fine-tuned orchestrator: screen classification accuracy >= 95% on validation set
- [x] Field extraction accuracy >= 90% on Pierre's shop validation screenshots (85-99% OCR confidence, 2026-03-20)
- [ ] `vllm serve models/fine-tuned/...` starts on port 8001 with tool-calling enabled
- [ ] `uvicorn src.stardew_vision.webapp.app:app --port 8000` starts
- [ ] Browser upload of a Pierre's shop screenshot → audio plays with correct item description
- [x] `pytest tests/` — all tests pass (8/8 tests passing, 2026-03-20)
