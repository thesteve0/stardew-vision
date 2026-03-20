# ADR-001: Vision Language Model Selection

**Date**: 2026-03-03
**Status**: Accepted
**Deciders**: Project team

## Context

We need to select Vision Language Models (VLMs) to evaluate for the Stardew Valley accessibility pipeline. The task requires a model to look at a game screenshot, classify which UI panel is active, and dispatch the correct tool call to an extraction agent (see ADR-009). This is a screen classification and tool-dispatch task, not grid-cell item recognition.

Constraints:
- Hardware: AMD Strix Halo (gfx1151), ROCm 7.2, PyTorch 2.9.1
- **Only FP16 is officially validated** on this hardware (BF16/INT4 are not)
- Must support HuggingFace PEFT fine-tuning via LoRA
- Must work with vLLM 0.7.x on ROCm for serving
- 1-2 month timeline — two candidates must be evaluable quickly
- Models must be open-weight with permissive licenses (project is a public GitHub repo + HuggingFace deliverable)
- The comparison between two models is pedagogically important for the conference talk

## Decision

**Candidate A (Primary)**: `Qwen/Qwen2.5-VL-7B-Instruct`
**Candidate B (Comparison)**: `HuggingFaceTB/SmolVLM2-2.2B-Instruct`

Both will be evaluated zero-shot first, then fine-tuned on the same dataset. Results are compared in `scripts/02_vlm_baseline_comparison.py`.

## Alternatives Considered

| Option | Why not selected |
|--------|----------------|
| **PaliGemma2-3B** (Google) | Strong fine-tuning model but requires gating/agreement on HuggingFace; inconsistent ROCm FP16 reports; less active community support as of early 2026 |
| **InternVL2-8B** | Custom training framework (InternLM-XComposer) adds complexity; HuggingFace PEFT integration less mature |
| **Phi-4-multimodal** (Microsoft) | Newer model with fewer community fine-tuning examples; Phi licensing has been in flux |
| **moondream2** (1.8B) | Too small for reliable game UI understanding without very large dataset; good future comparison point |
| **LLaVA-1.5-7B** | Older architecture; Qwen2.5-VL significantly outperforms on UI understanding tasks |

## Why These Two

**Qwen2.5-VL-7B-Instruct** (Primary — Orchestrator):
- Role: **screen type classifier + tool dispatcher** (see ADR-009). Looks at a screenshot, identifies which UI panel is active, and emits a tool call.
- State-of-the-art on UI/screenshot understanding tasks (trained specifically on document/UI data)
- FP16 native, well-tested on ROCm
- HuggingFace PEFT LoRA support via `Qwen2_5_VLForConditionalGeneration`
- vLLM 0.7.x compatible on ROCm with function/tool calling support
- Apache 2.0 license
- Dynamic resolution: can process variable-size screenshots without fixed cropping

**SmolVLM2-2.2B-Instruct** (Comparison):
- Role: **same orchestrator task** — can a 2.2B model accurately classify screen types and dispatch tool calls?
- 3× smaller than Qwen2.5-VL — natural size/speed contrast for the talk
- Compresses each image to only **81 tokens** via SigLIP (vs. Qwen's dynamic thousands) — fast inference, but hypothesis: 81 tokens may be insufficient to reliably distinguish between similar UI screens
- HuggingFace's own model — TRL SFTTrainer fine-tuning is first-class supported
- Apache 2.0 license
- **Precision note**: SmolVLM2 prefers BF16. Will be tested in FP16 first; BF16 tried if FP16 is unstable. Result documented in ADR update.

## Consequences

**Gets easier**: Clear "small vs. large" and "fast vs. accurate" narrative for the talk; both have excellent HuggingFace ecosystem support; licensing is clean for public release.

**Gets harder**: Two different fine-tuning toolchains (PEFT directly for Qwen, TRL SFTTrainer for SmolVLM2); SmolVLM2's BF16 preference may require testing/workaround on ROCm.

**We are committing to**: Evaluating both zero-shot and fine-tuned, logging all results to MLFlow under the same experiment name for fair comparison. If one model fails to work on ROCm, we fall back to only one candidate.

## Metrics

This decision will be validated by:
- Screen classification accuracy ≥ 70% zero-shot for at least one candidate (confirms the task is learnable from base weights)
- Screen classification accuracy ≥ 95% after fine-tuning for Qwen2.5-VL-7B
- Both models complete fine-tuning without OOM on the devcontainer hardware
- SmolVLM2 inference latency ≤ 50% of Qwen2.5-VL latency (confirming the size/speed tradeoff hypothesis)
- SmolVLM2 comparison question: does 81-token image compression prevent reliable screen type discrimination?
