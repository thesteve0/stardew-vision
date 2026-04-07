#!/usr/bin/env bash
# Run this on the HOST machine (not inside devcontainer).
#
# IMAGE CHOICE: rocm/vllm:rocm7.12.0_gfx1151_ubuntu24.04_py3.12_pytorch_2.9.1_vllm_0.16.0
#
# We tested vllm/vllm-openai-rocm:nightly (0.19.1rc1) on 2026-04-04 and reverted.
# The nightly uses the V1 engine, which added an encoder cache profiling step that
# crashes on gfx1151 (Strix Halo) with "tried to allocate 256 GiB" OOM. This is a
# known bug: github.com/vllm-project/vllm/issues/37472. Fix is in PR #38555 (unmerged).
# The AMD image uses the V0 engine (no encoder profiling) and works correctly.
# See docs/vllm-notes.md for full details and reference URLs.
#
# SYNTAX NOTE: This image's entrypoint is NOT "vllm serve" — the command must
# include "vllm serve" explicitly followed by the model as a positional argument
# (not --model). This differs from the nightly image where the entrypoint is
# already "vllm serve" and the model is passed with --model.
#
# The default Qwen2.5-VL chat template does not support tool calling.
# configs/serving/qwen2_5_vl_tool_template.jinja merges multi-modal +
# tool-call format and is required for vLLM to inject tool definitions
# into the prompt. The same template is used for OpenShift AI serving.
#
# VLLM_DEBUG_LOG_API_SERVER_RESPONSE: logs full request/response bodies
# including raw model output before the hermes parser processes it.
#
# --uvicorn-log-level debug: more verbose HTTP server logs.
#
# CAUTION: VLLM_LOGGING_LEVEL=DEBUG shows the full prompt with tool
# injection but has a known bug that breaks tool calling
# (github.com/vllm-project/vllm/issues/34792). Uncomment only for
# prompt inspection, then remove before testing tool calls.
#   -e VLLM_LOGGING_LEVEL=DEBUG \

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATE="${SCRIPT_DIR}/../configs/serving/qwen2_5_vl_tool_template.jinja"

docker run --rm \
  --device=/dev/kfd \
  --device=/dev/dri \
  --group-add=video \
  --cap-add=SYS_PTRACE \
  --security-opt seccomp=unconfined \
  --ipc=host \
  -p 8001:8000 \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  -v "${TEMPLATE}":/chat_template.jinja \
  -e HF_TOKEN=$HF_TOKEN \
  -e VLLM_DEBUG_LOG_API_SERVER_RESPONSE=True \
  rocm/vllm:rocm7.12.0_gfx1151_ubuntu24.04_py3.12_pytorch_2.9.1_vllm_0.16.0 \
  vllm serve Qwen/Qwen2.5-VL-7B-Instruct \
  --dtype float16 \
  --port 8000 \
  --max-model-len 4096 \
  --limit-mm-per-prompt '{"image": 1}' \
  --enable-auto-tool-choice \
  --tool-call-parser hermes \
  --chat-template /chat_template.jinja \
  --uvicorn-log-level debug
