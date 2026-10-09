#!/usr/bin/env bash
# Base predictor only. Fine-tuned serving requires a separately verified adapter.
set -euo pipefail
NAMESPACE=stardew-vision
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

oc get storageclass gp3-csi >/dev/null
oc get crd servingruntimes.serving.kserve.io inferenceservices.serving.kserve.io >/dev/null
if ! oc get nodes -l nvidia.com/gpu.present=true -o name | grep -q .; then
  echo 'No GPU nodes available; refusing deployment.' >&2
  exit 1
fi
oc apply -f "${SCRIPT_DIR}/../00-namespace.yaml"
oc apply -f "${SCRIPT_DIR}/04-configmap-chat-template.yaml"
oc apply -f "${SCRIPT_DIR}/05-pvc-model-cache.yaml"
oc apply -f "${SCRIPT_DIR}/06-job-download-model.yaml"
if ! oc wait --for=condition=Complete job/download-qwen-model -n "${NAMESPACE}" --timeout=30m; then
  oc get pods,pvc -n "${NAMESPACE}"
  oc logs job/download-qwen-model -n "${NAMESPACE}" --tail=80 || true
  exit 1
fi
oc apply -f "${SCRIPT_DIR}/02-servingruntime-with-template.yaml"
oc apply -f "${SCRIPT_DIR}/03-inferenceservice.yaml"
oc wait --for=condition=Ready inferenceservice/stardew-vlm -n "${NAMESPACE}" --timeout=30m
oc get inferenceservice,pods -n "${NAMESPACE}"
