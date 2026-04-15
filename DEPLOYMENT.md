# Deployment Guide: Stardew Vision to OpenShift AI

This document summarizes the deployment artifacts created for migrating Stardew Vision from local Docker to OpenShift AI.

## What Was Created

### Build & Deployment Scripts
- **`deploy/build-images.sh`** - Builds all 3 container images and provides push instructions
- **`deploy/deploy-to-openshift.sh`** - Automated deployment script with guided workflow

### Kubernetes Manifests (`configs/serving/openshift/`)

| File | Purpose | Size |
|------|---------|------|
| `00-namespace.yaml` | Creates `stardew-vision` namespace | 98 bytes |
| `01-configmap-templates.yaml` | OCR template assets (base64-encoded) | 2.3 MB |
| `02-configmap-chat-template.yaml` | vLLM tool-calling Jinja2 template | 4.3 KB |
| `03-pvc-hf-cache.yaml` | TTS model cache (2Gi) | 185 bytes |
| `04-pvc-errors.yaml` | Error screenshot storage (5Gi) | 194 bytes |
| `05-objectbucketclaim.yaml` | ODF bucket for model weights | 220 bytes |
| `10-deployment-pierres-buying-tool.yaml` | OCR service deployment + service | 1.4 KB |
| `20-deployment-tts-tool.yaml` | TTS service deployment + service | 2.0 KB |
| `30-deployment-coordinator.yaml` | Main app deployment + service + route | 2.1 KB |
| `40-serving-runtime.yaml` | vLLM runtime with NVIDIA GPU support | 1.2 KB |
| `41-inference-service.yaml` | Qwen2.5-VL InferenceService (KServe) | 1 KB |
| `README.md` | Detailed deployment documentation | 7.0 KB |

## Architecture Overview

```
┌──────────────────┐
│  OpenShift Route │ HTTPS (external access)
│  stardew-vision  │
└────────┬─────────┘
         │
┌────────▼─────────┐
│   Coordinator    │ FastAPI orchestrator (3 replicas, CPU)
│   Port 8000      │
└──┬────┬──────┬───┘
   │    │      │
   │    │      └─────────────────────┐
   │    │                            │
   │    └────────────┐               │
   │                 │               │
┌──▼──────────┐ ┌────▼──────┐ ┌─────▼────────────┐
│  OCR Tool   │ │ TTS Tool  │ │  vLLM (KServe)   │
│  Port 8002  │ │ Port 8003 │ │  Qwen2.5-VL-7B   │
│ 2 replicas  │ │ 2 replicas│ │  1-2 replicas    │
│    CPU      │ │    CPU    │ │  NVIDIA L40s GPU │
└─────────────┘ └───────────┘ └──────────────────┘
```

## Key Differences: Local vs OpenShift

| Component | Local (Docker) | OpenShift AI |
|-----------|----------------|--------------|
| **vLLM** | Host machine, AMD ROCm | KServe InferenceService, NVIDIA L40s |
| **Image** | `rocm/vllm:rocm7.12.0_gfx1151...` | `vllm/vllm-openai:v0.6.4.post1` |
| **Networking** | `host.docker.internal:8001` | `vllm-qwen-predictor-default.svc.cluster.local` |
| **Storage** | Local volumes | PVCs + ODF S3 bucket |
| **Scaling** | Manual (docker-compose scale) | Kubernetes autoscaling |
| **TLS** | HTTP only | HTTPS via OpenShift Route |

## Deployment Workflow

### Step 1: Build Images (Host Machine)

⚠️ **IMPORTANT**: All Docker build and push commands **MUST be run on the host machine**, NOT inside the devcontainer. The devcontainer does not have Docker-in-Docker configured for image building and pushing.

```bash
# Run these commands on your HOST machine (outside devcontainer)
./deploy/build-images.sh v0.1.0
docker login ghcr.io
docker push ghcr.io/thesteve0/stardew-coordinator:v0.1.0
docker push ghcr.io/thesteve0/stardew-pierres-buying-tool:v0.1.0
docker push ghcr.io/thesteve0/stardew-tts-tool:v0.1.0
docker push ghcr.io/thesteve0/stardew-coordinator:latest
docker push ghcr.io/thesteve0/stardew-pierres-buying-tool:latest
docker push ghcr.io/thesteve0/stardew-tts-tool:latest
```

**CRITICAL**: Make packages public at https://github.com/thesteve0?tab=packages

### Step 2: Deploy to OpenShift
```bash
./deploy/deploy-to-openshift.sh
```

This script will:
1. Create namespace and storage resources
2. Extract ODF S3 credentials
3. Pause for you to upload the model
4. Deploy vLLM serving (5-10 min wait)
5. Deploy microservices
6. Provide the external HTTPS URL

### Step 3: Upload Model to ODF

During the deployment script, you'll be prompted to upload the model:

```bash
# Install s3cmd
pip install s3cmd

# Configure with ODF credentials (displayed by script)
cat > ~/.s3cfg << EOF
[default]
access_key = <from script>
secret_key = <from script>
host_base = <from script>
host_bucket = <from script>
use_https = True
EOF

# Download and save model
python -c "
from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
model = Qwen2VLForConditionalGeneration.from_pretrained('Qwen/Qwen2.5-VL-7B-Instruct', torch_dtype='float16')
processor = AutoProcessor.from_pretrained('Qwen/Qwen2.5-VL-7B-Instruct')
model.save_pretrained('./qwen-upload')
processor.save_pretrained('./qwen-upload')
"

# Upload to ODF
s3cmd put -r qwen-upload/ s3://${BUCKET_NAME}/models/qwen2.5-vl-7b/
```

## Resource Requirements

| Resource | Minimum |
|----------|---------|
| **CPU** | 7 cores |
| **Memory** | 20 Gi |
| **GPU** | 1x NVIDIA L40s (or T4, A10, V100) |
| **Storage** | 7 Gi (PVCs) + 15 Gi (S3 bucket) |
| **Pods** | 8 (3 coordinator + 2 OCR + 2 TTS + 1 vLLM) |

## Verification Checklist

After deployment, verify:

- [ ] All pods running: `oc get pods -n stardew-vision`
- [ ] InferenceService ready: `oc get inferenceservice -n stardew-vision`
- [ ] Route accessible: `oc get route -n stardew-vision`
- [ ] vLLM responds: Port-forward and curl `/v1/models`
- [ ] Web UI loads in browser (HTTPS)
- [ ] End-to-end test: Upload `tests/fixtures/pierre_shop_001.png`
- [ ] Audio playback works correctly

## Troubleshooting

### Common Issues

**vLLM pod pending:**
```bash
oc describe pod -n stardew-vision -l serving.kserve.io/inferenceservice=vllm-qwen
oc get nodes -l nvidia.com/gpu.present=true
```

**OCR templates missing:**
```bash
oc exec -n stardew-vision deployment/pierres-buying-tool -- ls -la /app/datasets/assets/templates
```

**Coordinator can't reach vLLM:**
```bash
oc get svc -n stardew-vision | grep vllm-qwen-predictor
oc logs -n stardew-vision -l component=coordinator --tail=50
```

**View logs:**
```bash
# All components
oc logs -n stardew-vision -l app=stardew-vision --all-containers -f

# Specific component
oc logs -n stardew-vision -l component=coordinator -f
oc logs -n stardew-vision -l serving.kserve.io/inferenceservice=vllm-qwen -c kserve-container -f
```

## Manual Deployment

For step-by-step manual deployment, see `configs/serving/openshift/README.md`

## Cleanup

```bash
# Delete everything
oc delete namespace stardew-vision

# Or selectively
oc delete -f configs/serving/openshift/30-deployment-coordinator.yaml
oc delete -f configs/serving/openshift/20-deployment-tts-tool.yaml
oc delete -f configs/serving/openshift/10-deployment-pierres-buying-tool.yaml
oc delete inferenceservice vllm-qwen -n stardew-vision
```

## References

- **Plan**: `/home/stpousty-devcontainer/.claude/plans/tranquil-forging-barto.md`
- **ADR-005**: `docs/adr/005-serving-strategy.md` (OpenShift AI strategy)
- **ADR-009**: `docs/adr/009-agent-tool-calling-architecture.md` (Agent architecture)
- **OpenShift Docs**: `configs/serving/openshift/README.md`
