#!/bin/bash
set -e

# vLLM Deployment Script for OpenShift AI
# Deploys Qwen2.5-VL-7B-Instruct via KServe InferenceService

NAMESPACE="stardew-vision"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=================================================="
echo "vLLM Deployment for Stardew Vision"
echo "=================================================="
echo ""

# Step 1: Verify prerequisites
echo "Step 1: Verifying prerequisites..."

# Check if GPU HardwareProfile exists
if ! oc get hardwareprofiles nvidia-l40s-gpu -n redhat-ods-applications &>/dev/null; then
    echo "⚠️  WARNING: GPU HardwareProfile not found!"
    echo "   Creating HardwareProfile in redhat-ods-applications namespace..."
    oc apply -f "${SCRIPT_DIR}/01-gpu-hardwareprofile.yaml"
    echo "   ✅ HardwareProfile created"
else
    echo "   ✅ GPU HardwareProfile exists"
fi

# Check if namespace exists
if ! oc get namespace ${NAMESPACE} &>/dev/null; then
    echo "   ❌ Namespace ${NAMESPACE} does not exist"
    echo "   Run: oc new-project ${NAMESPACE}"
    exit 1
fi
echo "   ✅ Namespace ${NAMESPACE} exists"

# Check GPU operators
if ! oc get csv -n openshift-nfd 2>/dev/null | grep -q nfd; then
    echo "   ⚠️  WARNING: Node Feature Discovery operator not found"
fi

if ! oc get csv -n nvidia-gpu-operator 2>/dev/null | grep -q gpu-operator; then
    echo "   ⚠️  WARNING: NVIDIA GPU Operator not found"
fi

echo ""

# Step 2: Create HuggingFace connection
echo "Step 2: Creating HuggingFace connection..."
oc apply -f "${SCRIPT_DIR}/00-huggingface-connection.yaml"
echo "   ✅ HuggingFace connection created"
echo ""

# Step 3: Create ServingRuntime
echo "Step 3: Creating vLLM ServingRuntime..."
oc apply -f "${SCRIPT_DIR}/02-vllm-servingruntime.yaml"
echo "   ✅ ServingRuntime created"
echo ""

# Step 4: Deploy InferenceService
echo "Step 4: Deploying InferenceService..."
oc apply -f "${SCRIPT_DIR}/03-inferenceservice.yaml"
echo "   ✅ InferenceService created"
echo ""

# Step 5: Monitor deployment
echo "Step 5: Monitoring deployment..."
echo "   This may take 25-35 minutes (GPU provision + download + load)"
echo ""
echo "   You can monitor progress with:"
echo "   - Watch status: oc get inferenceservice stardew-vlm -n ${NAMESPACE} -w"
echo "   - Download logs: oc logs -n ${NAMESPACE} -l serving.kserve.io/inferenceservice=stardew-vlm -c storage-initializer -f"
echo "   - Startup logs: oc logs -n ${NAMESPACE} -l serving.kserve.io/inferenceservice=stardew-vlm -c kserve-container -f"
echo ""

# Optional: Wait for ready
read -p "Wait for deployment to be ready? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "   Waiting for InferenceService to be ready..."
    oc wait --for=condition=Ready \
      inferenceservice/stardew-vlm \
      -n ${NAMESPACE} \
      --timeout=40m

    echo ""
    echo "✅ Deployment successful!"
    echo ""

    # Test endpoint
    echo "Testing endpoint..."
    POD=$(oc get pods -n ${NAMESPACE} -l serving.kserve.io/inferenceservice=stardew-vlm -o jsonpath='{.items[0].metadata.name}')

    if [ -n "$POD" ]; then
        echo "   Testing /v1/models endpoint..."
        oc exec -n ${NAMESPACE} ${POD} -- curl -s http://localhost:8080/v1/models | head -1
        echo "   ✅ Endpoint responding"
    fi
fi

echo ""
echo "=================================================="
echo "Deployment Complete!"
echo "=================================================="
echo ""
echo "Internal endpoint: http://stardew-vlm-predictor:8080/v1"
echo "Model ID: stardew-vlm"
echo ""
echo "Update your coordinator configuration:"
echo "  VLLM_BASE_URL: http://stardew-vlm-predictor:8080/v1"
echo "  VLLM_MODEL: stardew-vlm"
echo ""
