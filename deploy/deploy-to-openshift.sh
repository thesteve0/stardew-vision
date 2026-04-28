#!/bin/bash
set -e

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Stardew Vision OpenShift AI Deployment${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if oc or kubectl is available
if command -v oc &> /dev/null; then
    KUBECTL="oc"
    echo -e "${GREEN}✓${NC} Using OpenShift CLI (oc)"
elif command -v kubectl &> /dev/null; then
    KUBECTL="kubectl"
    echo -e "${GREEN}✓${NC} Using kubectl"
else
    echo -e "${RED}✗${NC} Neither 'oc' nor 'kubectl' found. Please install one."
    exit 1
fi

cd "$(dirname "$0")/../configs/serving/openshift"

# Phase 1: Foundation
echo ""
echo -e "${YELLOW}Phase 1: Deploying Foundation (namespace, ConfigMaps, PVCs, OBC)${NC}"
echo ""

$KUBECTL apply -f 00-namespace.yaml
$KUBECTL apply -f 01-configmap-templates.yaml
$KUBECTL apply -f 02-configmap-chat-template.yaml
$KUBECTL apply -f 03-pvc-hf-cache.yaml
$KUBECTL apply -f 04-pvc-errors.yaml
$KUBECTL apply -f 02-pvc-paddlex-cache-ocr-tools.yaml
$KUBECTL apply -f 05-objectbucketclaim.yaml

echo ""
echo -e "${YELLOW}Waiting for ObjectBucketClaim to be bound...${NC}"
$KUBECTL wait --for=jsonpath='{.status.phase}'=Bound obc/stardew-model-storage -n stardew-vision --timeout=300s || {
    echo -e "${RED}✗${NC} ObjectBucketClaim failed to bind. Check ODF installation."
    exit 1
}

echo ""
echo -e "${GREEN}✓${NC} Foundation deployed successfully!"
echo ""
echo -e "${YELLOW}Extracting ODF credentials:${NC}"

export AWS_ACCESS_KEY_ID=$($KUBECTL get secret stardew-model-storage -n stardew-vision -o jsonpath='{.data.AWS_ACCESS_KEY_ID}' | base64 -d)
export AWS_SECRET_ACCESS_KEY=$($KUBECTL get secret stardew-model-storage -n stardew-vision -o jsonpath='{.data.AWS_SECRET_ACCESS_KEY}' | base64 -d)
export BUCKET_NAME=$($KUBECTL get cm stardew-model-storage -n stardew-vision -o jsonpath='{.data.BUCKET_NAME}')
export BUCKET_HOST=$($KUBECTL get cm stardew-model-storage -n stardew-vision -o jsonpath='{.data.BUCKET_HOST}')

echo "  S3 Endpoint: https://${BUCKET_HOST}"
echo "  Bucket: ${BUCKET_NAME}"
echo ""
echo -e "${YELLOW}Save these credentials - you'll need them to upload the model:${NC}"
echo ""
echo "export AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}"
echo "export AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}"
echo "export BUCKET_NAME=${BUCKET_NAME}"
echo "export BUCKET_HOST=${BUCKET_HOST}"
echo ""

# Pause for user to upload model
echo -e "${RED}========================================${NC}"
echo -e "${RED}ACTION REQUIRED${NC}"
echo -e "${RED}========================================${NC}"
echo ""
echo "Before continuing, you must upload the model to ODF:"
echo ""
echo "1. Install s3cmd: pip install s3cmd"
echo "2. Configure s3cmd with the credentials above"
echo "3. Download and upload the model:"
echo ""
echo "   python -c \""
echo "from transformers import Qwen2VLForConditionalGeneration, AutoProcessor"
echo "model = Qwen2VLForConditionalGeneration.from_pretrained('Qwen/Qwen2.5-VL-7B-Instruct', torch_dtype='float16')"
echo "processor = AutoProcessor.from_pretrained('Qwen/Qwen2.5-VL-7B-Instruct')"
echo "model.save_pretrained('./qwen-upload')"
echo "processor.save_pretrained('./qwen-upload')"
echo "\""
echo ""
echo "   s3cmd put -r qwen-upload/ s3://\${BUCKET_NAME}/models/qwen2.5-vl-7b/"
echo ""
echo "4. Verify: s3cmd ls s3://\${BUCKET_NAME}/models/qwen2.5-vl-7b/"
echo ""
read -p "Press ENTER once the model is uploaded to continue..."

# Phase 2: vLLM Serving
echo ""
echo -e "${YELLOW}Phase 2: Deploying vLLM Serving (this may take 5-10 minutes)${NC}"
echo ""

$KUBECTL apply -f 40-serving-runtime.yaml
envsubst < 41-inference-service.yaml | $KUBECTL apply -f -

echo ""
echo -e "${YELLOW}Waiting for InferenceService to be ready...${NC}"
$KUBECTL wait --for=condition=Ready inferenceservice/vllm-qwen -n stardew-vision --timeout=15m || {
    echo -e "${RED}✗${NC} InferenceService failed to become ready. Check logs:"
    echo "  $KUBECTL logs -n stardew-vision -l serving.kserve.io/inferenceservice=vllm-qwen -c kserve-container"
    exit 1
}

echo ""
echo -e "${GREEN}✓${NC} vLLM serving deployed successfully!"

# Phase 3: Microservices
echo ""
echo -e "${YELLOW}Phase 3: Deploying Microservices${NC}"
echo ""

$KUBECTL apply -f 10-deployment-pierres-buying-tool.yaml
$KUBECTL apply -f 20-deployment-tts-tool.yaml
$KUBECTL apply -f 30-deployment-coordinator.yaml
$KUBECTL apply -f 40-deployment-ocr-tools.yaml

echo ""
echo -e "${YELLOW}Waiting for deployments to be ready...${NC}"
$KUBECTL rollout status deployment/pierres-buying-tool -n stardew-vision
$KUBECTL rollout status deployment/tts-tool -n stardew-vision
$KUBECTL rollout status deployment/coordinator -n stardew-vision
$KUBECTL rollout status deployment/ocr-tools -n stardew-vision

echo ""
echo -e "${GREEN}✓${NC} All microservices deployed successfully!"

# Get external URL
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}DEPLOYMENT COMPLETE!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

EXTERNAL_URL=$($KUBECTL get route stardew-vision -n stardew-vision -o jsonpath='{.spec.host}')
echo -e "${GREEN}Application URL:${NC} https://${EXTERNAL_URL}"
echo ""
echo -e "${YELLOW}Verification:${NC}"
echo "  $KUBECTL get pods -n stardew-vision"
echo "  $KUBECTL logs -n stardew-vision -l component=coordinator -f"
echo ""
echo -e "${GREEN}Next steps:${NC}"
echo "  1. Open https://${EXTERNAL_URL} in your browser"
echo "  2. Upload tests/fixtures/pierre_shop_001.png"
echo "  3. Verify audio playback"
echo ""
