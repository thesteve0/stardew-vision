#!/usr/bin/env bash
# Run all three Stardew Vision services locally without Docker.
# Requires espeak-ng to be installed for Kokoro TTS:
#   sudo apt-get install espeak-ng
#
# Services started:
#   OCR tool   → http://localhost:8002
#   TTS tool   → http://localhost:8003
#   Coordinator → http://localhost:8000
#
# vLLM (Qwen) must be running on the host machine at port 8001.
# See deploy/start_vllm_host.sh

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="${REPO_ROOT}/services/coordinator:${REPO_ROOT}/services/ocr-tool:${REPO_ROOT}/services/tts-tool"
export OCR_TOOL_URL="http://localhost:8002"
export TTS_TOOL_URL="http://localhost:8003"
export VLLM_BASE_URL="${VLLM_BASE_URL:-http://localhost:8001/v1}"

echo "Starting OCR tool on :8002..."
python -m uvicorn stardew_ocr.app:app --port 8002 --log-level info &
OCR_PID=$!

echo "Starting TTS tool on :8003 (Kokoro model loads on first request)..."
python -m uvicorn stardew_tts.app:app --port 8003 --log-level info &
TTS_PID=$!

# Give tools a moment to bind their ports
sleep 2

echo "Starting coordinator on :8000..."
python -m uvicorn stardew_coordinator.app:app --port 8000 --log-level info &
COORD_PID=$!

echo ""
echo "All services running. Press Ctrl+C to stop."
echo "  OCR tool:    http://localhost:8002/health"
echo "  TTS tool:    http://localhost:8003/health"
echo "  Coordinator: http://localhost:8000/health"

trap "kill $OCR_PID $TTS_PID $COORD_PID 2>/dev/null; echo 'Stopped.'" EXIT
wait
