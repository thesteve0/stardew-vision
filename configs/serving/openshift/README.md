# OpenShift AI Deployment Manifests

This directory contains Kubernetes manifests to deploy Stardew Vision to OpenShift AI.

## Architecture

- **Coordinator** (3 replicas, CPU-only): FastAPI orchestrator, manages agent loop
- **OCR Tool** (2 replicas, CPU-only): PaddleOCR extraction service
- **TTS Tool** (2 replicas, CPU-only): Kokoro TTS synthesis
- **vLLM** (1-2 replicas, GPU): Qwen2.5-VL-7B via KServe InferenceService

## Prerequisites

1. OpenShift AI cluster with GPU nodes (NVIDIA L40s or similar)
2. OpenShift Data Foundation (ODF) installed for object storage
3. Container images pushed to GHCR and marked public
4. `oc` or `kubectl` CLI configured to access your cluster

## Quick Start

### 1. Build and Push Images

⚠️ **CRITICAL**: Run these commands on your **HOST machine**, NOT inside the devcontainer. The devcontainer does not have Docker-in-Docker configured.

```bash
# From repository root ON HOST MACHINE (exit devcontainer first)
./deploy/build-images.sh v0.1.0

# Login to GHCR
docker login ghcr.io

# Push images
docker push ghcr.io/thesteve0/stardew-coordinator:v0.1.0
docker push ghcr.io/thesteve0/stardew-pierres-buying-tool:v0.1.0
docker push ghcr.io/thesteve0/stardew-tts-tool:v0.1.0
docker push ghcr.io/thesteve0/stardew-coordinator:latest
docker push ghcr.io/thesteve0/stardew-pierres-buying-tool:latest
docker push ghcr.io/thesteve0/stardew-tts-tool:latest
```

**IMPORTANT**: After pushing, make packages public at https://github.com/thesteve0?tab=packages

### 2. Deploy Foundation

```bash
cd configs/serving/openshift

# Create namespace and storage
oc apply -f 00-namespace.yaml
oc apply -f 01-configmap-templates.yaml
oc apply -f 02-configmap-chat-template.yaml
oc apply -f 03-pvc-hf-cache.yaml
oc apply -f 04-pvc-errors.yaml
oc apply -f 05-objectbucketclaim.yaml

# Wait for OBC to be bound
oc wait --for=jsonpath='{.status.phase}'=Bound obc/stardew-model-storage -n stardew-vision --timeout=300s

# Extract ODF credentials
export AWS_ACCESS_KEY_ID=$(oc get secret stardew-model-storage -n stardew-vision -o jsonpath='{.data.AWS_ACCESS_KEY_ID}' | base64 -d)
export AWS_SECRET_ACCESS_KEY=$(oc get secret stardew-model-storage -n stardew-vision -o jsonpath='{.data.AWS_SECRET_ACCESS_KEY}' | base64 -d)
export BUCKET_NAME=$(oc get cm stardew-model-storage -n stardew-vision -o jsonpath='{.data.BUCKET_NAME}')
export BUCKET_HOST=$(oc get cm stardew-model-storage -n stardew-vision -o jsonpath='{.data.BUCKET_HOST}')

echo "S3 Endpoint: https://${BUCKET_HOST}"
echo "Bucket: ${BUCKET_NAME}"
```

### 3. Upload Model to ODF

```bash
# Install s3cmd
pip install s3cmd

# Configure s3cmd
cat > ~/.s3cfg << EOF
[default]
access_key = ${AWS_ACCESS_KEY_ID}
secret_key = ${AWS_SECRET_ACCESS_KEY}
host_base = ${BUCKET_HOST}
host_bucket = ${BUCKET_HOST}
use_https = True
EOF

# Download and upload base model
python -c "
from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
model = Qwen2VLForConditionalGeneration.from_pretrained('Qwen/Qwen2.5-VL-7B-Instruct', torch_dtype='float16')
processor = AutoProcessor.from_pretrained('Qwen/Qwen2.5-VL-7B-Instruct')
model.save_pretrained('./qwen-upload')
processor.save_pretrained('./qwen-upload')
"

s3cmd put -r qwen-upload/ s3://${BUCKET_NAME}/models/qwen2.5-vl-7b/

# Verify
s3cmd ls s3://${BUCKET_NAME}/models/qwen2.5-vl-7b/
```

### 4. Deploy vLLM Serving

```bash
# Apply serving runtime and inference service
oc apply -f 40-serving-runtime.yaml

# Substitute bucket name and apply inference service
envsubst < 41-inference-service.yaml | oc apply -f -

# Wait for model to load (5-10 minutes)
oc wait --for=condition=Ready inferenceservice/vllm-qwen -n stardew-vision --timeout=15m

# Check status
oc get inferenceservice -n stardew-vision
oc logs -n stardew-vision -l serving.kserve.io/inferenceservice=vllm-qwen -c kserve-container -f
```

### 5. Deploy Microservices

```bash
# Deploy all services
oc apply -f 10-deployment-pierres-buying-tool.yaml
oc apply -f 20-deployment-tts-tool.yaml
oc apply -f 30-deployment-coordinator.yaml

# Wait for rollout
oc rollout status deployment/pierres-buying-tool -n stardew-vision
oc rollout status deployment/tts-tool -n stardew-vision
oc rollout status deployment/coordinator -n stardew-vision

# Get external URL
EXTERNAL_URL=$(oc get route stardew-vision -n stardew-vision -o jsonpath='{.spec.host}')
echo "Application URL: https://${EXTERNAL_URL}"
```

### 6. Verify

```bash
# Check all pods
oc get pods -n stardew-vision

# Expected output:
# coordinator-xxx     1/1  Running
# coordinator-xxx     1/1  Running
# coordinator-xxx     1/1  Running
# pierres-buying-tool-xxx        1/1  Running
# pierres-buying-tool-xxx        1/1  Running
# tts-tool-xxx        1/1  Running
# tts-tool-xxx        1/1  Running
# vllm-qwen-xxx       2/2  Running

# Test vLLM endpoint
oc port-forward -n stardew-vision svc/vllm-qwen-predictor-default 8080:80
curl http://localhost:8080/v1/models  # From another terminal

# Access web UI
open https://${EXTERNAL_URL}
```

## File Descriptions

| File | Purpose |
|------|---------|
| `00-namespace.yaml` | Creates `stardew-vision` namespace |
| `01-configmap-templates.yaml` | OCR template images (base64-encoded) |
| `02-configmap-chat-template.yaml` | vLLM tool-calling Jinja2 template |
| `03-pvc-hf-cache.yaml` | TTS model cache (2Gi) |
| `04-pvc-errors.yaml` | Error screenshot storage (5Gi) |
| `05-objectbucketclaim.yaml` | ODF bucket for model weights |
| `10-deployment-pierres-buying-tool.yaml` | OCR service deployment + service |
| `20-deployment-tts-tool.yaml` | TTS service deployment + service |
| `30-deployment-coordinator.yaml` | Main app deployment + service + route |
| `40-serving-runtime.yaml` | vLLM runtime with custom template |
| `41-inference-service.yaml` | Qwen2.5-VL model serving (GPU) |

## Troubleshooting

### vLLM Pod Pending
```bash
oc describe pod -n stardew-vision -l serving.kserve.io/inferenceservice=vllm-qwen
oc get nodes -l nvidia.com/gpu.present=true
```

### OCR Templates Missing
```bash
oc exec -n stardew-vision deployment/pierres-buying-tool -- ls -la /app/datasets/assets/templates
```

### Coordinator Can't Reach vLLM
```bash
oc get svc -n stardew-vision | grep vllm-qwen-predictor
oc logs -n stardew-vision -l component=coordinator --tail=50
```

### Check Logs
```bash
# All services
oc logs -n stardew-vision -l app=stardew-vision --all-containers -f --tail=100

# Specific service
oc logs -n stardew-vision -l component=coordinator -f
oc logs -n stardew-vision -l component=pierres-buying-tool -f
oc logs -n stardew-vision -l component=tts-tool -f
oc logs -n stardew-vision -l serving.kserve.io/inferenceservice=vllm-qwen -c kserve-container -f
```

## Resource Requirements

| Component | CPU | Memory | GPU | Replicas |
|-----------|-----|--------|-----|----------|
| Coordinator | 500m-1000m | 512Mi-1Gi | 0 | 3 |
| OCR Tool | 500m-1000m | 1-2Gi | 0 | 2 |
| TTS Tool | 1000m-2000m | 1-2Gi | 0 | 2 |
| vLLM | 4-8 CPU | 16-20Gi | 1 NVIDIA GPU | 1-2 |

**Total**: ~7 CPU cores, ~20Gi memory, 1 GPU, 7Gi storage

## Cleanup

```bash
# Delete all resources
oc delete namespace stardew-vision

# Or selectively
oc delete -f 30-deployment-coordinator.yaml
oc delete -f 20-deployment-tts-tool.yaml
oc delete -f 10-deployment-pierres-buying-tool.yaml
oc delete inferenceservice vllm-qwen -n stardew-vision
oc delete servingruntime vllm-runtime -n stardew-vision
```
