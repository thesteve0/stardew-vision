# Training Pipeline (Post-MVP)

This directory is a placeholder for the fine-tuning pipeline.

When training work begins, this will move to a separate repository:
**`stardew-vision-training`**

That repo will contain:
- `scripts/data_prep/` — annotation and data preparation tools (currently in `data/scripts/annotation/`)
- `scripts/eval/` — model quality evaluation (currently in `data/scripts/evaluation/`)
- `configs/` — training hyperparameters (LoRA configs for Qwen2.5-VL and SmolVLM2)
- `notebooks/` — exploration and experiment notebooks

## Why a separate repo?

Training has fundamentally different dependencies (`trl`, `peft`, KubeRay), runs on
different hardware (full GPU cluster via OpenShift AI), and has a different team workflow
than the inference serving code in this repo. Keeping them separate avoids dependency
conflicts and makes it clear what needs to be deployed for the accessibility tool to run.

## Current training plan

See [`docs/plan.md`](../docs/plan.md) for the fine-tuning strategy (Phase 2+).
Key decisions: ADR-001 (VLM selection), ADR-005 (serving strategy).
