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

# Experimental AMD development runtime, not the production deployment.
# Use ./deploy/deploy-to-openshift.sh for the verified NVIDIA/OpenShift stack.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATE="${SCRIPT_DIR}/../configs/serving/qwen2_5_vl_tool_template.jinja"
: "${BASE_MODEL_DIR:?Set BASE_MODEL_DIR to the downloaded pinned base model directory}"
: "${LORA_ADAPTER_DIR:?Set LORA_ADAPTER_DIR to the pinned HF adapter directory}"
python3 - <<'PY'
import hashlib, os
from pathlib import Path
expected = {
    'adapter_model.safetensors': '373c475669049191527b3d8e8a330f347f236855482bb2282f9604177a915a63',
    'adapter_config.json': '449c057c21c46e3bc0d32d4d7a3590112927c756ae4a7e0ec6326cdc91e2e478',
}
for name, digest in expected.items():
    with (Path(os.environ['LORA_ADAPTER_DIR']) / name).open('rb') as stream:
        assert hashlib.file_digest(stream, 'sha256').hexdigest() == digest, name
metadata = list((Path(os.environ['BASE_MODEL_DIR']) / '.cache/huggingface/download').rglob('*.metadata'))
assert metadata and all(p.read_text().splitlines()[0] == 'cc594898137f460bfe9f0759e9844b3ce807cfb5' for p in metadata), 'Base revision mismatch'
PY

docker run --rm \
  --device=/dev/kfd \
  --device=/dev/dri \
  --group-add=video \
  --cap-add=SYS_PTRACE \
  --security-opt seccomp=unconfined \
  --ipc=host \
  -p 8001:8000 \
  -v "${BASE_MODEL_DIR}":/mnt/models:ro \
  -v "${LORA_ADAPTER_DIR}":/mnt/lora-adapter:ro \
  -v "${TEMPLATE}":/chat_template.jinja \
  -e VLLM_DEBUG_LOG_API_SERVER_RESPONSE=True \
  rocm/vllm:rocm7.12.0_gfx1151_ubuntu24.04_py3.12_pytorch_2.9.1_vllm_0.16.0 \
  vllm serve /mnt/models \
  --served-model-name qwen-base \
  --enable-lora \
  --lora-modules stardew-vlm-finetuned=/mnt/lora-adapter \
  --max-lora-rank 16 \
  --dtype float16 \
  --port 8000 \
  --max-model-len 8192 \
  --limit-mm-per-prompt '{"image": 1}' \
  --enable-auto-tool-choice \
  --tool-call-parser hermes \
  --chat-template /chat_template.jinja \
  --uvicorn-log-level debug
