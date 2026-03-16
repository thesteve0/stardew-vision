# Stardew Vision: Project Plan

**Last updated**: 2026-03-03
**Talk deadline**: 1-2 months
**Status**: Pre-implementation — documentation complete, coding not yet started

This is the authoritative project plan. It is referenced from `CLAUDE.md`. Update this document as decisions change; use the ADRs in `docs/adr/` to document *why* each decision was made.

---

## Project Goals

1. **Accessibility tool**: Visually impaired (but not blind) Stardew Valley players upload a screenshot of their loot box and receive an audio file describing what is in each occupied cell.
2. **Conference talk artifact**: A live demo and complete codebase used in talks/workshops teaching AI practitioners how to apply VLMs + TTS for accessibility use cases.

**Primary user**: A player whose vision impairment makes reading small pixel-art item sprites difficult. They take a screenshot on their iPad, upload it, and hear the contents read aloud.

---

## Architecture Overview

```
User uploads screenshot (iPad or browser)
  ↓
FastAPI POST /analyze (port 8000)
  ↓
VLM Inference via vLLM (port 8001, OpenAI-compatible API)
  Fine-tuned Qwen2.5-VL-7B-Instruct (FP16, ROCm)
  ↓ JSON output
  {"cells": [{"row":0,"col":0,"item":"Copper Bar","quantity":5,"quality":"silver"}, ...]}
  ↓
Description template (Python string formatting)
  → "In your treasure chest: top row has Copper Bar ×5, Ancient Sword, empty..."
  ↓
MeloTTS synthesis (CPU real-time, GPU-optional)
  ↓ WAV audio bytes
FastAPI response (audio/wav)
  ↓
Browser <audio> element plays immediately
```

---

## Key Architectural Decisions

Full rationale in `docs/adr/`. Summary:

| Decision | Choice | ADR |
|---|---|---|
| VLM Candidate A | `Qwen/Qwen2.5-VL-7B-Instruct` (FP16, LoRA via PEFT) | [ADR-001](adr/001-vlm-selection.md) |
| VLM Candidate B | `HuggingFaceTB/SmolVLM2-2.2B-Instruct` (FP16/BF16, TRL SFTTrainer) | [ADR-001](adr/001-vlm-selection.md) |
| VLM role | Structured JSON output → template → TTS (not end-to-end description) | [ADR-002](adr/002-vlm-role-architecture.md) |
| TTS | MeloTTS-English (local, CPU/GPU-optional, MIT) | [ADR-003](adr/003-tts-selection.md) |
| Repo structure | Single monorepo | [ADR-004](adr/004-repo-structure.md) |
| Serving | vLLM locally (port 8001); KServe on OpenShift AI | [ADR-005](adr/005-serving-strategy.md) |
| Distributed training | Ray Train on OpenShift AI (KubeRay); KFP post-MVP | [ADR-005](adr/005-serving-strategy.md) |
| Feature store | Filesystem/JSONL for MVP; Feast Phase 2 | [ADR-006](adr/006-feature-store-strategy.md) |
| Grid detection | VLM-first (no preprocessing); accepts dual-grid screenshots | [ADR-008](adr/008-grid-detection-strategy.md) |
| Overlay detection | VLM detects quality stars + stack counts | [ADR-007](adr/007-overlay-detection-strategy.md) |
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

---

## Repository Structure

```
stardew-vision/
├── .devcontainer/             # ROCm devcontainer config (do not modify casually)
├── docs/
│   ├── adr/                   # Architecture Decision Records
│   │   ├── 000-adr-template.md
│   │   ├── 001-vlm-selection.md
│   │   ├── 002-vlm-role-architecture.md
│   │   ├── 003-tts-selection.md
│   │   ├── 004-repo-structure.md
│   │   ├── 005-serving-strategy.md
│   │   ├── 006-feature-store-strategy.md
│   │   ├── 007-overlay-detection-strategy.md
│   │   └── 008-grid-detection-strategy.md
│   ├── plan.md                # This file
│   ├── talk-abstract.md       # Conference talk abstract (user need)
│   ├── evaluation-rubric.md   # VLM scoring metrics and thresholds
│   ├── data-collection-plan.md  # Todo lists for synthetic + real data
│   ├── user-submission-guide.md  # User-facing screenshot submission instructions
│   └── dataset-guide.md       # Annotation schema + contribution guide
├── datasets/                  # Host volume mount — NOT committed to git
│   ├── assets/                # Sprite sheet, item manifest
│   ├── raw/                   # Images (synthetic + real)
│   ├── annotated/             # JSONL annotation files
│   └── splits/                # train/val/test manifests
├── models/                    # Host volume mount — NOT committed to git
│   ├── base/                  # Downloaded base checkpoints
│   └── fine-tuned/            # LoRA adapter checkpoints
├── configs/
│   ├── training/
│   │   ├── finetune_config.yaml         # Qwen2.5-VL-7B LoRA config
│   │   └── finetune_config_smolvlm2.yaml  # SmolVLM2 TRL config
│   ├── output_schema.json               # JSON schema for VLM output validation
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
│   ├── generate_synthetic_data.py
│   ├── validate_dataset.py
│   ├── annotate_dataset.py      # Model-assisted annotation review tool
│   ├── run_baseline_eval.py
│   └── push_to_hf.py
├── src/
│   └── stardew_vision/          # Main Python package
│       ├── data/
│       │   ├── dataset.py        # PyTorch Dataset class
│       │   ├── preprocessing.py  # Cell extraction from screenshots
│       │   └── item_taxonomy.py  # Item name → category mapping
│       ├── models/
│       │   ├── vlm_wrapper.py    # Unified VLM inference interface (FP16)
│       │   ├── finetune.py       # LoRA training loop (Qwen)
│       │   ├── finetune_smolvlm.py  # TRL SFTTrainer (SmolVLM2)
│       │   └── evaluate.py       # All 8 metrics + JSON schema validation
│       ├── tts/
│       │   └── synthesize.py     # text → WAV bytes via MeloTTS
│       ├── serving/
│       │   └── inference.py      # vLLM OpenAI-client wrapper
│       └── webapp/
│           ├── app.py            # FastAPI app
│           ├── routes.py         # POST /analyze → audio/wav
│           └── static/
│               └── index.html    # Upload form + audio player
├── tests/
│   ├── test_data_pipeline.py
│   ├── test_vlm_wrapper.py
│   ├── test_tts.py
│   └── test_webapp.py
├── main.py                       # CLI entrypoint
├── pyproject.toml                # Dependencies (preserve exclude-dependencies)
└── CLAUDE.md                     # Claude Code context (references this file)
```

**Note**: `src/stardew-vision/` (hyphen) must be renamed to `src/stardew_vision/` (underscore) — Python package names cannot contain hyphens.

---

## Data Strategy

Full detail in `docs/data-collection-plan.md`.

**Track 1 — Synthetic data** (Week 1): Generate 500 labeled images from the Stardew Valley sprite sheet. Script: `scripts/generate_synthetic_data.py`. Perfect ground truth, zero annotation cost. Unblocks everything.

**Track 2 — Community screenshots** (Weeks 2-5): Collect 100-200 real screenshots via Reddit/Discord outreach. Annotate using model-assisted review. The final test set must be real screenshots only.

**Annotation schema**: JSONL per image. Fields include `image_id` (UUID4), `source`, `loot_type`, `grid`, `cells` (item_name, quantity, occupied, category), `created_at`. Schema is Feast-compatible from day 1.

**Dataset splits**: 70% train / 15% val / 15% test. Test = real screenshots only.

---

## Evaluation Framework

Full detail in `docs/evaluation-rubric.md`.

### Two-Stage Evaluation

**Stage 1 — JSON Validity**: Parse VLM output; validate against `configs/output_schema.json` using `jsonschema`. Invalid output = 0 on all cell metrics. Track `JSON Validity Rate` separately.

**Stage 2 — Content Metrics** (using `rapidfuzz` for fuzzy matching):

| Metric | Description | MVP Target (fine-tuned) |
|---|---|---|
| JSON Validity Rate | % calls producing schema-valid JSON | ≥ 95% |
| Grid Detection Accuracy | % dual-grid screenshots where VLM correctly analyzed only the chest grid (ADR-008) | ≥ 95% |
| CIA-Exact | % occupied cells with exact item name match (case-insensitive) | ≥ 80% |
| CIA-Fuzzy | % occupied cells with rapidfuzz ratio ≥ 85 | ≥ 88% |
| CIA-Category | % occupied cells in the correct item category | ≥ 92% |
| FNR-Occupied | % occupied cells reported as empty (worst user failure) | ≤ 8% |
| FPR-Empty | % empty cells reported as occupied (hallucinations) | ≤ 5% |
| Quantity Accuracy | % correct quantity readings for stacked items | ≥ 75% |
| Quality Accuracy | % correct quality readings (normal/silver/gold/iridium) | ≥ 70% |
| Grid Completeness | % runs with correct cell count in output | ≥ 98% |

All metrics logged to MLFlow. Baseline (zero-shot) vs. fine-tuned comparison is the core narrative of the talk.

### Item Difficulty Taxonomy (refined after baseline)

- **Tier 1** (easy): Common, distinctive items — Coal, Wood, Fiber, Stone
- **Tier 2** (medium): Similar-looking items — different ore types, different weapon sprites
- **Tier 3** (hard): Rare items the base model may never have seen

---

## Fine-Tuning

### Qwen2.5-VL-7B (LoRA via PEFT)

Config: `configs/training/finetune_config.yaml`

Key settings:
- `dtype: float16` — FP16 only (ROCm 7.2 constraint)
- `bf16: false` — not validated on Strix Halo
- LoRA: `r=16, alpha=32`, target modules: all attention + FFN projection layers
- Effective batch size 16 (batch=2, grad_accum=8)
- Apply `torch.compile(mode="reduce-overhead")` after LoRA init

### SmolVLM2-2.2B (TRL SFTTrainer)

Config: `configs/training/finetune_config_smolvlm2.yaml`

Key differences:
- Uses TRL `SFTTrainer` (wraps PEFT internally)
- LoRA: `r=8, alpha=8` (smaller rank for smaller model)
- Prefers BF16 but will be tested FP16 first; document result in ADR-001 update
- Images compressed to 81 tokens via SigLIP — fast but potentially lower detail
- Keep JSON output schema flat (SmolVLM2 degrades on deep nesting)

### Training Infrastructure

- Local: devcontainer (first runs, hyperparameter search)
- Scale-out: Ray Train on OpenShift AI via KubeRay (post-MVP)
- MLFlow tracking: local `mlruns/` → remote MLFlow server on OpenShift for scale-out runs
- Checkpoints: saved to `models/fine-tuned/` (host volume, persists across container rebuilds)

---

## Local vs. OpenShift AI

| Component | Devcontainer (local) | OpenShift AI |
|---|---|---|
| Synthetic data generation | ✅ primary | — |
| Zero-shot baseline eval | ✅ primary | — |
| First fine-tuning runs (LoRA) | ✅ primary | — |
| Scale-out fine-tuning (Ray Train) | — | ✅ post-MVP |
| MLFlow tracking | ✅ dev | ✅ production |
| vLLM serving (dev/test) | ✅ port 8001 | — |
| vLLM serving (production) | — | ✅ KServe |
| Web app (dev) | ✅ port 8000 | — |
| Web app (production) | — | ✅ |
| Jupyter notebooks | ✅ port 8888 | — |

**Conference talk demo**: runs entirely locally. OpenShift AI appears in the architecture diagram; live deployment is post-MVP.

---

## 6-Week Implementation Sequence

### Week 1: Foundation + Synthetic Data

1. Rename `src/stardew-vision/` → `src/stardew_vision/`
2. Update `pyproject.toml` with all new dependencies
3. Execute data collection plan Phase A+B+C (see `docs/data-collection-plan.md`)
   - ✅ **Phase A (partial):** Quality stars + font assets extracted from game files (2026-03-06)
     - See [datasets/assets/EXTRACTION_SUMMARY.md](../datasets/assets/EXTRACTION_SUMMARY.md)
   - **Phase A (remaining):** UI frame collection (chest backgrounds)
   - **Phase B:** Implement `scripts/generate_synthetic_data.py`
   - **Phase C:** Generate 500 labeled synthetic images
4. Write `src/stardew_vision/data/dataset.py`
5. Write `src/stardew_vision/data/item_taxonomy.py`

### Week 2: Zero-Shot Baseline

6. Write `src/stardew_vision/models/vlm_wrapper.py` (Qwen2.5-VL-7B, FP16)
7. Write `src/stardew_vision/models/evaluate.py` (all 8 metrics)
8. Run `notebooks/02_vlm_baseline_comparison.ipynb` — log to MLFlow
9. Launch community screenshot outreach

### Week 3: Fine-Tuning Pipeline

10. Write `src/stardew_vision/models/finetune.py` (LoRA + PEFT)
11. First fine-tuning run on synthetic data — log to MLFlow
12. Run post-training evaluation; compare to baseline
13. Write `scripts/annotate_dataset.py`; begin annotating real screenshots

### Week 4: TTS + Web App

14. Write `src/stardew_vision/tts/synthesize.py` (MeloTTS)
15. Write `src/stardew_vision/webapp/app.py` + `routes.py` + `index.html`
16. End-to-end integration test: upload screenshot → audio
17. Add ports 8000, 8001 to `devcontainer.json` `forwardPorts`

### Week 5-6: Serve + Polish

18. Configure vLLM local serving; point webapp at it
19. Retrain with mixed real + synthetic data
20. Write `src/stardew_vision/models/finetune_smolvlm.py` (TRL SFTTrainer)
21. Run SmolVLM2 baseline + fine-tuning; add to comparison notebook
22. Polish `notebooks/04_evaluation_results.ipynb` for talk
23. Write `scripts/push_to_hf.py`; push dataset + model to HuggingFace
24. Write OpenShift AI serving manifests

### Post-MVP

- Ray Train on OpenShift AI for distributed fine-tuning
- KubeFlow Pipelines for orchestration
- Feast feature store (Phase 2 per ADR-006)
- Option B: end-to-end instruct fine-tuning (for talk comparison story)
- XTTS/Coqui for higher-quality TTS

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
# vLLM client
"openai>=1.50.0",
# Data / evaluation
"rapidfuzz>=3.9.0",
"jsonschema>=4.23.0",
"evaluate>=0.4.0",
"Pillow>=10.0.0",         # also in ROCm container — keep in exclude-dependencies
```

Preserve all entries in `[tool.uv] exclude-dependencies` — these are ROCm-provided packages that must not be overwritten.

---

## HuggingFace Hub Deliverables

- **Dataset**: `{username}/stardew-loot-vision-dataset` — annotated screenshots + dataset card
- **Model**: `{username}/stardew-vision-vlm` — merged fine-tuned model + model card with eval metrics

Both managed via `scripts/push_to_hf.py`. Model card auto-generated from MLFlow run metadata.

---

## End-to-End Verification Checklist

The MVP is working when all of the following pass:

- [ ] `python scripts/generate_synthetic_data.py --count 500` produces images + annotations
- [ ] `python scripts/validate_dataset.py datasets/` reports 0 errors
- [ ] `python scripts/run_baseline_eval.py` logs metrics to MLFlow
- [ ] `python src/stardew_vision/models/finetune.py` completes without OOM; checkpoint saved
- [ ] Post-training CIA-Exact ≥ 80% on validation set
- [ ] `vllm serve models/fine-tuned/...` starts on port 8001
- [ ] `uvicorn src.stardew_vision.webapp.app:app --port 8000` starts
- [ ] Browser upload of a test screenshot → audio plays with correct item descriptions
- [ ] `pytest tests/` — all tests pass
