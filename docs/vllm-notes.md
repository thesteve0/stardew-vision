# vLLM Notes and Reference

Operational notes, known issues, and reference URLs for vLLM as used in this project.
This file travels with the repo so the context is available on any machine.

---

## Reference URLs

### Qwen2.5-VL Tool Calling
https://docs.vllm.ai/en/latest/features/tool_calling/#qwen-models

How to configure `--tool-call-parser`, `--enable-auto-tool-choice`, and custom chat
templates for Qwen models. Required reading if tool calls stop working after an upgrade.

### Qwen2.5-VL on AMD ROCm (Recipes)
https://docs.vllm.ai/projects/recipes/en/latest/Qwen/Qwen2.5-VL.html#amd-rocm-mi300x-mi325x-mi355x

AMD-specific serving recipe for Qwen2.5-VL. Covers image choice, dtype, and flags
validated on MI300X/MI325X/MI355X. Our gfx1151 (Strix Halo) is a consumer RDNA GPU,
not MI-series, so some settings differ — but this is the closest official reference.

### PaddleOCR-VL via vLLM (Future Option)
https://docs.vllm.ai/projects/recipes/en/latest/PaddlePaddle/PaddleOCR-VL.html

PaddleOCR-VL can be served via vLLM as a vision-language model. For Phase 2+, this
could replace our CPU PaddleOCR extraction pipeline with a GPU-accelerated VLM-based
OCR approach — potentially better accuracy on complex or degraded UI panels.

---

## Known Issues

### gfx1151 OOM in vLLM V1 Engine Encoder Profiling
**Affects:** `vllm/vllm-openai-rocm:nightly` (0.17+), any image using the V1 engine  
**Does NOT affect:** `rocm/vllm:rocm7.12.0_gfx1151_*` (0.16, V0 engine)  
**GitHub issue:** vllm-project/vllm#37472  
**Fix PR:** vllm-project/vllm#38555 (unmerged as of 2026-04-04)

**What happens:** vLLM V1 engine runs an encoder cache profiling step at startup
(`gpu_model_runner.py: profile_run()`). It runs the ViT with a maximum-size dummy
image to measure memory usage. On gfx1151, MIOpen has no pre-compiled solver database
for this GPU, so it attempts exhaustive kernel autotuning. This causes the ViT SDPA
attention to try to allocate 256 GiB (a worst-case profiling tensor), crashing with
`torch.OutOfMemoryError: HIP out of memory. Tried to allocate 256.00 GiB`.

**Root cause:** Missing MIOpen solver DB for gfx1151 + new encoder profiling in V1 engine.

**Workaround:** Use the AMD image with V0 engine (see `scripts/start_vllm_host.sh`).
Once PR #38555 merges, the nightly image should work.

**When we tried the nightly (2026-04-04):**
- `vllm/vllm-openai-rocm:nightly` (0.19.1rc1) — FAILS with above OOM
- `rocm/vllm:rocm7.12.0_gfx1151_ubuntu24.04_py3.12_pytorch_2.9.1_vllm_0.16.0` — WORKS

---

## Image Syntax Differences

The two images have different entrypoints — the command syntax is NOT the same:

**AMD image (0.16) — `rocm/vllm:rocm7.12.0_gfx1151_*`:**
- Entrypoint is a shell; you must include `vllm serve` explicitly
- Model is a positional argument (no `--model` flag)
```bash
docker run ... rocm/vllm:rocm7.12.0_gfx1151_... \
  vllm serve Qwen/Qwen2.5-VL-7B-Instruct \
  --dtype float16 ...
```

**vLLM project image (0.17+) — `vllm/vllm-openai-rocm:nightly`:**
- Entrypoint is already `vllm serve`; do NOT add it again
- Model is passed with `--model` flag (positional also works but warns)
```bash
docker run ... vllm/vllm-openai-rocm:nightly \
  --model Qwen/Qwen2.5-VL-7B-Instruct \
  --dtype float16 ...
```

---

## finish_reason Bug (Fixed in 0.17+)

In vLLM 0.16, when the model generates a tool call, `finish_reason` is returned as
`"stop"` instead of `"tool_calls"`. This violates the OpenAI spec.

**Our fix** in `src/stardew_vision/serving/inference.py`: check `if msg.tool_calls:`
instead of `if choice.finish_reason == "tool_calls"`. This is safe to keep even after
upgrading — it's strictly more robust.

GitHub issue: vllm-project/vllm#34792
