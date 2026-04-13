# ADR-012: OpenShift AI Deployment Architecture

**Date**: 2026-04-13
**Status**: Accepted
**Deciders**: Project team

## Context

The application was initially developed in a local devcontainer with:
- vLLM running on the host machine (AMD Strix Halo GPU)
- OCR, TTS, and coordinator services in Docker Compose
- Relaxed filesystem permissions
- Direct GPU access

For production deployment on OpenShift AI, we needed to:
- Serve the Qwen VLM via KServe InferenceService with vLLM runtime
- Deploy microservices (OCR, TTS, coordinator) in a distributed environment
- Handle OpenShift's strict security constraints (random UIDs, restricted permissions)
- Manage model downloads and caching for offline operation
- Scale services independently

## Decision

Deploy as a microservices architecture on OpenShift AI with the following components:

### Architecture Overview

```
Internet
  |
  v
OpenShift Route (haproxy, 3m timeout)
  |
  v
Coordinator Service (port 8000)
  |  manages agent loop, holds image_b64
  |  dispatches to:
  |
  +---> OCR Tool Service (port 8002)
  |       | PaddleOCR + OpenCV
  |       | Models cached in PVC
  |       | CPU-only
  |
  +---> TTS Tool Service (port 8003)
  |       | Kokoro TTS
  |       | Models in PVC
  |       | CPU-only
  |
  +---> vLLM Predictor (KServe InferenceService, port 8080)
          | Qwen2.5-VL-7B-Instruct
          | NVIDIA GPU
          | Custom chat template in ConfigMap
```

### Component Details

#### 1. vLLM Serving (KServe InferenceService)

**Deployment**: KServe `InferenceService` with `ServingRuntime`
- Runtime: `vllm-cuda-runtime-template` from Red Hat AI Inference Service (RHAI IS)
- Model: `hf://Qwen/Qwen2.5-VL-7B-Instruct` (auto-downloaded from HuggingFace)
- GPU: 1× NVIDIA GPU, 32Gi memory, tolerations for `nvidia.com/gpu`
- Custom chat template: Mounted from ConfigMap at `/mnt/chat-template/chat_template.jinja`
- vLLM args:
  - `--max-model-len=4096`
  - `--limit-mm-per-prompt={"image":1}`
  - `--enable-auto-tool-choice`
  - `--tool-call-parser=hermes`
  - `--chat-template=/mnt/chat-template/chat_template.jinja`

**Why KServe**: Native integration with OpenShift AI, handles model lifecycle, provides Prometheus metrics, supports autoscaling.

**Custom Chat Template**: Qwen's default template doesn't work with vLLM's Hermes tool call parser. We provide a custom Jinja template that formats tools in `<tools></tools>` XML tags and tool calls in `<tool_call></tool_call>` format.

#### 2. OCR Tool Service

**Deployment**: Standard Kubernetes Deployment (1 replica)
- Image: `ghcr.io/thesteve0/stardew-ocr-tool:v0.12.0`
- Resources: 1000m CPU request, 2500m limit, 4Gi memory request, 8Gi limit
- PVC: `paddlex-cache` (2Gi) mounted at `/cache`
- Init Container: Pre-downloads PaddleOCR models on first pod startup
- Model caching: PaddleOCR instance cached in memory (`_OCR_INSTANCE` module variable)

**Environment Variables**:
```yaml
HF_HOME: /cache/huggingface
PADDLEX_HOME: /cache/paddlex
PADDLE_PDX_CACHE_HOME: /cache/paddlex
PADDLE_OCR_BASE_DIR: /cache/paddleocr
FLAGS_use_mkldnn: "0"  # Disable OneDNN optimizations for CPU portability
FLAGS_use_xdnn: "0"
```

**Why PVC for models**: Models persist across pod restarts. First pod startup takes ~2 minutes to download models from HuggingFace/aistudio. Subsequent restarts are fast.

**Why model caching in memory**: Loading PaddleOCR models from disk takes ~30s. Caching the instance in a module-level variable keeps models resident in memory. First request after pod startup is slow (model loading), subsequent requests are fast (~2s OCR processing).

**Why disable MKLDNN**: PaddlePaddle is compiled with Intel MKLDNN (OneDNN) optimizations that require specific CPU instruction sets (AVX, AVX2). OpenShift nodes may have incompatible CPUs, causing `SIGTERM` during OneDNN kernel execution. Disabling MKLDNN sacrifices 2-4x CPU performance but ensures portability across all cluster nodes.

#### 3. TTS Tool Service

**Deployment**: Standard Kubernetes Deployment (1 replica)
- Image: `ghcr.io/thesteve0/stardew-tts-tool:v0.4.0`
- Resources: 1000m CPU request, 2000m limit, 1Gi memory request, 2Gi limit
- PVC: `hf-cache` (2Gi, shared with coordinator for model storage)
- Init Container: Pre-downloads Kokoro TTS models

**Why Init Container**: Kokoro downloads models on first use. Without init container, first TTS request would timeout. Init container downloads models during pod startup, before the main container becomes ready.

#### 4. Coordinator Service

**Deployment**: Standard Kubernetes Deployment (1 replica)
- Image: `ghcr.io/thesteve0/stardew-coordinator:v0.6.0`
- Resources: 500m CPU request, 1000m limit, 512Mi memory request, 1Gi limit
- ConfigMap: `service-endpoints` (OCR_TOOL_URL, TTS_TOOL_URL, VLLM_BASE_URL, VLLM_MODEL)
- PVC: `error-screenshots` mounted at `/app/datasets/errors`

**Route Configuration**:
```yaml
annotations:
  haproxy.router.openshift.io/timeout: 3m
```

**Why 3m timeout**: First request after OCR pod restart takes ~35-40s (VLM 1s + OCR model loading 30s + TTS 3s). Default OpenShift Route timeout is 30s, causing 504 Gateway Timeout errors. 3m allows for cold start while being reasonable for user experience.

**Timing logging**: All agent loop phases log with ⏱️ emoji prefix:
- VLM inference time
- OCR tool execution time
- TTS synthesis time
- Total request time

### Persistent Volumes

1. **paddlex-cache** (2Gi, RWO): PaddleOCR + PaddleX models for OCR service
2. **hf-cache** (2Gi, RWO): HuggingFace models for TTS service
3. **error-screenshots** (5Gi, RWO): Failed extraction screenshots with OCR debug output

### Security Constraints

**OpenShift Random UID**: All containers run as random UIDs (e.g., 1000860000) in the root group (GID 0). Cannot write to root-owned directories.

**Writable Locations**:
- `/tmp` (always writable)
- Mounted PVCs (writable if fsGroup or securityContext configured)
- Never assume write access to `/.cache`, `/.paddlex`, `/root`

**Environment Variable Handling**: Some libraries (PaddleX, HuggingFace) ignore Dockerfile `ENV` statements and read environment variables during module import. Must set via `os.environ.setdefault()` in Python code **before** imports:

```python
import os
os.environ.setdefault('PADDLEX_HOME', '/cache/paddlex')
os.environ.setdefault('HF_HOME', '/cache/huggingface')
# NOW safe to import
from paddleocr import PaddleOCR
```

### Image Registry

All images pushed to GitHub Container Registry (ghcr.io):
- `ghcr.io/thesteve0/stardew-ocr-tool:v0.12.0`
- `ghcr.io/thesteve0/stardew-tts-tool:v0.4.0`
- `ghcr.io/thesteve0/stardew-coordinator:v0.6.0`

### Deployment Order

```bash
# 1. Create namespace
kubectl create namespace stardew-vision

# 2. Create PVCs
kubectl apply -f configs/serving/openshift/02-pvc-paddlex-cache.yaml
kubectl apply -f configs/serving/openshift/03-pvc-hf-cache.yaml
kubectl apply -f configs/serving/openshift/04-pvc-errors.yaml

# 3. Create ConfigMaps
kubectl apply -f configs/serving/openshift/01-configmap-endpoints.yaml
kubectl apply -f configs/serving/openshift/vllm/04-configmap-chat-template.yaml

# 4. Deploy vLLM (KServe)
kubectl apply -f configs/serving/openshift/vllm/02-servingruntime-with-template.yaml
kubectl apply -f configs/serving/openshift/vllm/03-inferenceservice.yaml

# 5. Deploy microservices
kubectl apply -f configs/serving/openshift/10-deployment-ocr-tool.yaml
kubectl apply -f configs/serving/openshift/20-deployment-tts-tool.yaml
kubectl apply -f configs/serving/openshift/30-deployment-coordinator.yaml
```

## Alternatives Considered

| Option | Why not selected |
|--------|------------------|
| **All-in-one pod** | Cannot scale OCR, TTS, coordinator independently; harder to debug; single point of failure |
| **Shared filesystem for image transport** | Adds infrastructure complexity; base64 over HTTP is simpler for MVP; works in any Kubernetes environment |
| **Models in container images** | OCR models are 200MB+, bloats images; cannot update models without rebuilding; PVC caching is faster for restarts |
| **MKLDNN enabled** | 2-4x faster CPU inference but requires AVX2 CPU instructions; causes SIGTERM on incompatible nodes; portability more important than performance for MVP |
| **30s default route timeout** | Insufficient for cold start (model loading); 3m allows first request to complete while being reasonable for users |
| **Download models on every request** | 30s per request unacceptable for UX; model caching in memory reduces subsequent requests to ~2s |

## Consequences

**Gets easier**:
- Independent scaling of OCR, TTS, coordinator
- Services can be updated/restarted independently
- GPU resource isolation (only vLLM needs GPU)
- Model updates without rebuilding container images
- Error screenshots automatically saved to PVC for review
- Comprehensive timing logs for performance debugging

**Gets harder**:
- More infrastructure to manage (4 services + 3 PVCs + 2 ConfigMaps)
- Cold start is slow (~35-40s first request after OCR pod restart)
- OCR performance degraded by disabling MKLDNN (2-4x slower than with optimizations)
- Must pre-download models via init containers to avoid timeouts
- Environment variable handling more complex due to OpenShift security constraints

**We are committing to**:
- Microservices architecture on OpenShift AI
- KServe for VLM serving (not standalone vLLM)
- PVC-based model caching (not in-image)
- 3-minute route timeout (acceptable for MVP, may need optimization for production)
- Model instance caching in Python to avoid disk I/O on every request
- Portability over performance (MKLDNN disabled)
- Single replica for each service (no autoscaling in MVP)

## Performance Characteristics

**First request after pod restart**:
- VLM inference: ~1s
- OCR (with model loading): ~30s
- TTS: ~3s
- **Total**: ~35-40s

**Subsequent requests (models cached in memory)**:
- VLM inference: ~1s
- OCR (cached instance): ~2s
- TTS: ~3s
- **Total**: ~5-7s

**Memory usage**:
- OCR service: ~730 MiB (models loaded)
- TTS service: ~500 MiB
- Coordinator: ~200 MiB
- vLLM: ~12 GiB (GPU memory, Qwen2.5-VL-7B FP16)

## References

- [ADR-009](009-agent-tool-calling-architecture.md): Agent/tool-calling architecture
- [ADR-011](011-agent-loop-refinements.md): Agent loop refinements
- [LESSONS_LEARNED.md](../../LESSONS_LEARNED.md): OpenShift permissions and MKLDNN issues
- OpenShift AI documentation: https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/
- KServe documentation: https://kserve.github.io/website/
