#!/usr/bin/env bash
# Development only. Requires a host vLLM serving the pinned LoRA ID.
# Production: ./deploy/deploy-to-openshift.sh
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export OCR_TOOL_URL=http://localhost:8004
export TTS_TOOL_URL=http://localhost:8003
export VLLM_BASE_URL=${VLLM_BASE_URL:-http://localhost:8001/v1}
export VLLM_MODEL=stardew-vlm-finetuned
export AGENT_MODE=finetuned
PIDS=()
trap 'kill "${PIDS[@]}" 2>/dev/null || true' EXIT
for entry in 'ocr-tools:stardew_ocr_tools.app:8004' 'tts-tool:stardew_tts.app:8003' 'coordinator:stardew_coordinator.app_finetuned:8000'; do
  directory=${entry%%:*}; rest=${entry#*:}; module=${rest%%:*}; port=${rest##*:}
  (cd "$ROOT/services/$directory" && exec uv run python -m uvicorn "$module:app" --port "$port") &
  PIDS+=("$!")
done
echo 'Local fine-tuned coordinator: http://localhost:8000 (vLLM must already serve stardew-vlm-finetuned)'
wait
