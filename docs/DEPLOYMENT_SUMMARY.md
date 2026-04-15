# OpenShift AI Deployment Summary

**Project:** Stardew Vision  
**Date:** 2026-04-12  
**Status:** ✅ **Production Deployed and Working**

---

## Deployment Architecture

### Deployed Services

All services running in `stardew-vision` namespace on OpenShift AI:

| Service | Replicas | Image Version | Status | Purpose |
|---------|----------|---------------|--------|---------|
| **vLLM Predictor** | 1/1 | Qwen2.5-VL-7B-Instruct | ✅ Running | VLM inference with tool calling |
| **Coordinator** | 3/3 | ghcr.io/thesteve0/stardew-coordinator:v0.3.0 | ✅ Running | Agent loop runtime |
| **OCR Tool** | 2/2 | ghcr.io/thesteve0/stardew-pierres-buying-tool:v0.4.0 | ✅ Running | PaddleOCR + OpenCV extraction |
| **TTS Tool** | 2/2 | ghcr.io/thesteve0/stardew-tts-tool:v0.4.0 | ✅ Running | Kokoro TTS synthesis |

### Internal Networking

```
┌─────────────────────────────────────────────────────────┐
│  stardew-vision namespace                               │
│                                                          │
│  http://stardew-vlm-predictor:8080/v1                  │
│  (Qwen2.5-VL-7B via vLLM + KServe)                     │
│  - GPU-accelerated inference                            │
│  - Tool calling enabled                                 │
│  - Internal-only (no external route)                    │
│                    ↓                                     │
│  http://coordinator:8000                                │
│  (Agent loop orchestrator)                              │
│  - Manages conversation state                           │
│  - Executes tool calls                                  │
│  - Holds base64 image in memory                         │
│         ↓                    ↓                           │
│  http://pierres-buying-tool:8002   http://tts-tool:8003           │
│  (PaddleOCR)            (Kokoro TTS)                    │
│                                                          │
│  https://stardew-vision-....apps.....opentlc.com        │
│  (External Route - ONLY public endpoint)                │
└─────────────────────────────────────────────────────────┘
```

**Key Design Decisions:**
- ✅ All services in same namespace (simple internal networking)
- ✅ Only coordinator exposed externally via OpenShift Route
- ✅ No authentication between internal services (trust namespace boundary)
- ✅ Service URLs injected via ConfigMap environment variables
- ✅ Static assets (templates, etc.) baked into container images

---

## Issues Fixed During Deployment

### 1. vLLM Argument Format Error

**Error:**
```
api_server.py: error: unrecognized arguments: --limit-mm-per-prompt '{"image": 1}'
```

**Root Cause:** Incorrect argument format with quotes and spaces in JSON.

**Fix:**
```yaml
# WRONG:
args:
  - --limit-mm-per-prompt '{"image": 1}'

# CORRECT:
args:
  - --limit-mm-per-prompt={"image":1}
```

**Rules:**
- Use `=` between flag and value
- No spaces in JSON
- No quotes around the entire argument

---

### 2. UV Cache Permission Denied

**Error:**
```
Failed to initialize cache at /.cache/uv - Permission denied (os error 13)
```

**Root Cause:** OpenShift runs containers as non-root with random UID, cannot write to `/.cache`.

**Fix Applied to All Services:**
```dockerfile
ENV UV_CACHE_DIR=/tmp/.uv
```

**Affected Services:**
- Coordinator (v0.2.0)
- OCR Tool (v0.2.0)
- TTS Tool (v0.2.0)

---

### 3. Path Resolution IndexError

**Error:**
```python
Path(__file__).parents[3]  # IndexError: 3
```

**Root Cause:** Container structure `/app/service/module.py` cannot go up 3 levels to repository root.

**Fix Applied:**

**Coordinator (`agent_loop.py`):**
```python
# OLD (broken in container):
ERRORS_DIR = Path(__file__).parents[3] / "datasets" / "errors"

# NEW (works in container):
import os
ERRORS_DIR = Path(os.getenv("ERRORS_DIR", "/app/datasets/errors"))
```

**OCR Tool (`crop_pierres_detail_panel.py`):**
```python
# OLD (broken):
_TEMPLATES_DIR = Path(__file__).parents[3] / "datasets" / "assets" / "templates"

# NEW (works):
import os
_TEMPLATES_DIR = Path(os.getenv("TEMPLATES_DIR", "/app/datasets/assets/templates"))
```

**Version:** v0.3.0 for both services.

---

### 4. OCR Tool Missing System Libraries

**Error:**
```
ImportError: libGL.so.1: cannot open shared object file
```

**Root Cause:** `python:3.12-slim` doesn't include OpenCV system dependencies.

**Fix Added to Dockerfile:**
```dockerfile
# Install system dependencies for OpenCV and PaddleOCR
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*
```

**Version:** OCR Tool v0.4.0

---

### 5. TTS Tool HF_HOME Path Inconsistency

**Error:**
```
PermissionError: [Errno 13] Permission denied: '/root/.cache/huggingface/token'
```

**Root Cause:** Deployment YAML had init container using `/cache` but main container using `/root/.cache/huggingface` (not writable by non-root user).

**Fix Applied to `20-deployment-tts-tool.yaml`:**
```yaml
# BOTH containers now use /cache:
containers:
  - name: tts
    env:
      - name: HF_HOME
        value: /cache  # Changed from /root/.cache/huggingface
    volumeMounts:
      - name: hf-cache
        mountPath: /cache  # Changed from /root/.cache/huggingface
```

**Version:** Deployment YAML updated (no image rebuild needed).

---

### 6. TTS Tool Missing spaCy Model

**Error:**
```
error: Failed to install: en_core_web_sm-3.8.0-py3-none-any.whl
  Caused by: failed to create directory: Permission denied (os error 13)
```

**Root Cause:** Kokoro TTS tries to download spaCy model at runtime and can't write to venv (OpenShift non-root).

**Fix Added to Dockerfile:**
```dockerfile
# Pre-download spaCy model (needed by Kokoro) to avoid runtime permission errors
RUN uv run python -m spacy download en_core_web_sm
```

**Version:** TTS Tool v0.4.0

---

### 7. vLLM Missing Tool Calling Flags ⚠️ **CRITICAL**

**Error:**
```
openai.BadRequestError: Error code: 400 - {'error': {'message': '"auto" tool choice requires --enable-auto-tool-choice and --tool-call-parser to be set'}}
```

**Root Cause:** The vLLM InferenceService was missing the tool calling flags that were present in local host deployment.

**Fix Applied to `03-inferenceservice.yaml`:**
```yaml
args:
  - --max-model-len=4096
  - --limit-mm-per-prompt={"image":1}
  - --enable-auto-tool-choice     # ADDED
  - --tool-call-parser=hermes     # ADDED
```

**Impact:** Without these flags, the agent loop cannot call tools (OCR/TTS), making the entire application non-functional.

**Version:** InferenceService updated (required vLLM pod restart and ~10 minute model reload).

---

## Final Working Configuration

### vLLM InferenceService

**File:** `configs/serving/openshift/vllm/03-inferenceservice.yaml`

**Critical Arguments:**
```yaml
args:
  - --max-model-len=4096
  - --limit-mm-per-prompt={"image":1}
  - --enable-auto-tool-choice
  - --tool-call-parser=hermes
```

**Resources:**
```yaml
resources:
  requests:
    cpu: "4"
    memory: 24Gi
    nvidia.com/gpu: "1"
  limits:
    cpu: "8"
    memory: 32Gi
    nvidia.com/gpu: "1"
```

**Service Endpoint:** `http://stardew-vlm-predictor:8080/v1`

---

### Coordinator

**File:** `configs/serving/openshift/30-deployment-coordinator.yaml`

**Image:** `ghcr.io/thesteve0/stardew-coordinator:v0.3.0`

**Environment Variables (from ConfigMap):**
```yaml
envFrom:
  - configMapRef:
      name: service-endpoints

# ConfigMap content:
data:
  PIERRES_BUYING_TOOL_URL: "http://pierres-buying-tool:8002"
  TTS_TOOL_URL: "http://tts-tool:8003"
  VLLM_BASE_URL: "http://stardew-vlm-predictor:8080/v1"
  VLLM_MODEL: "stardew-vlm"
```

**Volume Mounts:**
```yaml
volumeMounts:
  - name: errors
    mountPath: /app/datasets/errors

volumes:
  - name: errors
    persistentVolumeClaim:
      claimName: error-screenshots
```

---

### OCR Tool

**File:** `configs/serving/openshift/10-deployment-pierres-buying-tool.yaml`

**Image:** `ghcr.io/thesteve0/stardew-pierres-buying-tool:v0.4.0`

**Key Changes:**
- ✅ System libraries for OpenCV (libgl1, libglib2.0-0, libgomp1)
- ✅ Templates baked into image at `/app/datasets/assets/templates/`
- ✅ UV cache at `/tmp/.uv`
- ✅ Environment variable path resolution

**No ConfigMap needed** - all assets self-contained in image.

---

### TTS Tool

**File:** `configs/serving/openshift/20-deployment-tts-tool.yaml`

**Image:** `ghcr.io/thesteve0/stardew-tts-tool:v0.4.0`

**Key Changes:**
- ✅ spaCy model pre-downloaded during build
- ✅ HF_HOME consistent at `/cache` for both init and main container
- ✅ UV cache at `/tmp/.uv`

**Init Container:**
```yaml
initContainers:
  - name: download-kokoro
    image: ghcr.io/thesteve0/stardew-tts-tool:v0.4.0
    env:
      - name: HF_HOME
        value: /cache
    volumeMounts:
      - name: hf-cache
        mountPath: /cache
```

**Main Container:**
```yaml
containers:
  - name: tts
    image: ghcr.io/thesteve0/stardew-tts-tool:v0.4.0
    env:
      - name: HF_HOME
        value: /cache  # MUST match init container
    volumeMounts:
      - name: hf-cache
        mountPath: /cache
```

---

## Deployment Timeline

| Event | Duration | Notes |
|-------|----------|-------|
| **Initial vLLM Deploy** | ~30 min | GPU provisioning + model download + cache profiling |
| **Fix 1-3 (UV cache, paths)** | ~15 min | Rebuild coordinator + OCR (v0.2.0 → v0.3.0) |
| **Fix 4 (OCR libraries)** | ~10 min | Rebuild OCR (v0.3.0 → v0.4.0) |
| **Fix 5-6 (TTS paths, spaCy)** | ~15 min | Rebuild TTS (v0.3.0 → v0.4.0) |
| **Fix 7 (vLLM tool calling)** | ~10 min | Update InferenceService, vLLM pod restart |
| **Total** | ~80 min | From first deploy to fully working |

**Lesson:** Always include tool calling flags in initial vLLM configuration to avoid late-stage redeployment.

---

## Verification Commands

### Check All Services

```bash
oc get pods -n stardew-vision
```

**Expected Output:**
```
NAME                                     READY   STATUS    RESTARTS   AGE
coordinator-78cfc7f7f8-6bnw8             1/1     Running   0          66m
coordinator-78cfc7f7f8-qxfnf             1/1     Running   0          66m
coordinator-78cfc7f7f8-t4j75             1/1     Running   0          66m
pierres-buying-tool-85c555cbcb-k79fg                1/1     Running   0          45m
pierres-buying-tool-85c555cbcb-zkdfg                1/1     Running   0          44m
stardew-vlm-predictor-8456665bd9-nsczg   1/1     Running   0          10m
tts-tool-5496969749-phbbh                1/1     Running   0          21m
tts-tool-5496969749-pnz6g                1/1     Running   0          20m
```

### Check Service Endpoints

```bash
oc get svc -n stardew-vision
```

**Expected Output:**
```
NAME                    TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)    AGE
coordinator             ClusterIP   172.30.248.47   <none>        8000/TCP   70m
pierres-buying-tool                ClusterIP   172.30.56.158   <none>        8002/TCP   71m
stardew-vlm-predictor   ClusterIP   None            <none>        80/TCP     161m
tts-tool                ClusterIP   172.30.92.27    <none>        8003/TCP   71m
```

### Test vLLM Tool Calling

```bash
oc exec -n stardew-vision deployment/coordinator -- \
  curl -s http://stardew-vlm-predictor:8080/v1/models | jq .
```

**Expected:** Model ID `stardew-vlm` with tool calling enabled.

### Check External Route

```bash
oc get route -n stardew-vision
```

**Expected Output:**
```
NAME             HOST/PORT
stardew-vision   stardew-vision-stardew-vision.apps...opentlc.com
```

### Test End-to-End

Upload a Pierre's shop screenshot via the web interface:
```
https://stardew-vision-stardew-vision.apps.stardew-vision.sandbox5291.opentlc.com
```

**Expected:**
1. ✅ Image uploaded successfully
2. ✅ Qwen VLM analyzes screenshot
3. ✅ OCR tool extracts panel data
4. ✅ Qwen generates narration
5. ✅ TTS tool synthesizes audio
6. ✅ WAV file plays in browser

**Result:** ✅ **All steps working as of 2026-04-12**

---

## Key Lessons Learned

### 1. OpenShift Non-Root Constraints

**Problem:** Many development patterns assume root access and writable home directories.

**Solutions:**
- ✅ Use `/tmp` for caches (writable by all users)
- ✅ Use environment variables for paths (not `__file__.parents[N]`)
- ✅ Pre-install all models/dependencies during build (avoid runtime downloads)

### 2. vLLM Tool Calling Configuration

**Problem:** Local development used `--enable-auto-tool-choice` and `--tool-call-parser=hermes`, but these were omitted from OpenShift deployment.

**Solution:**
- ✅ Document ALL vLLM flags in deployment guides
- ✅ Add tool calling flags to InferenceService YAML from the start
- ✅ Test with actual tool calls early, not just text completion

### 3. Container Image Architecture

**Problem:** Initial approach used ConfigMaps for templates (2.3MB base64 PNG files).

**Solution:**
- ✅ Bake all static assets into container images
- ✅ Use ConfigMaps only for configuration (URLs, settings)
- ✅ Keep images self-contained for portability

### 4. Path Consistency in Multi-Container Pods

**Problem:** TTS init container used `/cache` but main container used `/root/.cache/huggingface`.

**Solution:**
- ✅ Use same paths for same volumes across all containers
- ✅ Document environment variable → path mappings
- ✅ Test init containers separately from main containers

### 5. System Library Dependencies

**Problem:** `python:3.12-slim` is missing libraries that "just work" in development.

**Solution:**
- ✅ Document all system dependencies in Dockerfiles
- ✅ Test builds from scratch (not cached layers)
- ✅ Use multi-stage builds if needed to minimize image size

---

## Production Readiness

### Current Status

✅ **Functionally Complete:**
- All services deployed and running
- End-to-end agent loop working
- External route accessible
- Health checks passing

### Recommended Next Steps

1. **Monitoring:**
   - Add Prometheus metrics export
   - Set up Grafana dashboards for GPU utilization
   - Configure alerts for pod failures

2. **Scaling:**
   - Test coordinator autoscaling (current: fixed 3 replicas)
   - Implement request queuing for vLLM (avoid overload)
   - Add rate limiting to external route

3. **Reliability:**
   - Implement PVC for vLLM model cache (avoid re-downloads on restart)
   - Add retries with backoff in agent loop
   - Test failover scenarios (what happens if OCR tool goes down?)

4. **Performance:**
   - Benchmark end-to-end latency
   - Optimize vLLM context window (currently 4096 tokens)
   - Consider ModelCar image for faster vLLM cold starts

5. **Security:**
   - Add authentication to external route (OAuth, token)
   - Implement rate limiting per user
   - Scan container images for vulnerabilities
   - Review RBAC permissions

---

## References

- **Main Deployment Guide:** [docs/DEPLOYING_MODELS_KSERVE.md](DEPLOYING_MODELS_KSERVE.md)
- **Quick Start:** [docs/DEPLOYING_MODELS_QUICKSTART.md](DEPLOYING_MODELS_QUICKSTART.md)
- **Architecture Decisions:** [docs/adr/009-agent-tool-calling-architecture.md](adr/009-agent-tool-calling-architecture.md)
- **OCR Choice:** [docs/ocr-choice.md](ocr-choice.md)
- **vLLM Configuration:** https://github.com/vllm-project/vllm/blob/main/vllm/engine/arg_utils.py

---

**Deployment Status:** ✅ **Production Ready**  
**Last Updated:** 2026-04-12  
**Next Review:** After 7 days of production usage
