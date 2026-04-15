# Quick Start: Deploy Qwen2.5-VL-7B on OpenShift AI

**Fast-track deployment guide for experienced users.**  
For detailed explanations, see [DEPLOYING_MODELS_KSERVE.md](DEPLOYING_MODELS_KSERVE.md).

---

## Prerequisites Checklist

Verify before starting:

```bash
# ✅ NFD and GPU Operator installed
oc get csv -n openshift-nfd | grep nfd
oc get csv -n nvidia-gpu-operator | grep gpu-operator

# ✅ GPU HardwareProfile exists (CRITICAL!)
oc get hardwareprofiles -n redhat-ods-applications | grep gpu
# Must show GPU profile, not just "default-profile"
# If missing: Fix provisioning script - see full guide

# ✅ GPU MachineSets configured
oc get machineset -n openshift-machine-api | grep gpu

# ✅ RHOAI Project exists (not just namespace)
oc get project stardew-vision
oc get namespace stardew-vision -o yaml | grep opendatahub.io/dashboard
# Should show: opendatahub.io/dashboard: "true"
```

---

## Deployment in 5 Minutes

### 1. Create HuggingFace Connection

**Via RHOAI Dashboard:**
- Project: `stardew-vision` → **Connections** → **Add connection**
- Type: **URI**
- Name: `huggingface-qwen`
- URI: `hf://Qwen/Qwen2.5-VL-7B-Instruct`

**Via CLI:**
```bash
cat <<EOF | oc apply -f -
apiVersion: v1
kind: Secret
metadata:
  name: huggingface-qwen
  namespace: stardew-vision
  labels:
    opendatahub.io/dashboard: "true"
    opendatahub.io/managed: "true"
  annotations:
    opendatahub.io/connection-type: uri
    openshift.io/display-name: huggingface-qwen
stringData:
  URI: hf://Qwen/Qwen2.5-VL-7B-Instruct
type: Opaque
EOF
```

---

### 2. Deploy Model (4-Step Wizard)

**RHOAI Dashboard** → `stardew-vision` project → **"Start by deploying a model"**

| Step | Fields | Values |
|------|--------|--------|
| **1. Model details** | Model location | Existing connection |
| | Connection | `huggingface-qwen` |
| | Model type | Generative AI model (LLM) |
| **2. Model deployment** | Deployment name | `stardew-vlm` |
| | Serving runtime | vLLM NVIDIA GPU ServingRuntime for KServe |
| | Hardware profile | `nvidia-l40s-gpu` ⚠️ **Must be GPU profile** |
| | Replicas | `1` |
| | Model route | ❌ **UNCHECK** (internal only) |
| | Token auth | ❌ **UNCHECK** (no auth) |
| **3. Advanced settings** | Add as AI asset endpoint | ☑️ Check (optional) |
| | Custom runtime arguments | `--max-model-len=4096 --limit-mm-per-prompt={"image":1} --enable-auto-tool-choice --tool-call-parser=hermes` |
| | Environment variables | Leave defaults (or add HF_TOKEN if needed) |
| **4. Review** | | Verify settings, click **Deploy** |

**Timeline:** ~25-35 min total (GPU provisioning + download + load)

---

### 3. Verify Deployment

```bash
# Watch status
oc get inferenceservice stardew-vlm -n stardew-vision -w
# Wait for READY=True

# Check pod is running
oc get pods -n stardew-vision -l serving.kserve.io/inferenceservice=stardew-vlm

# Test internal endpoint
oc run curl-test --image=curlimages/curl -n stardew-vision --rm -it -- \
  curl http://stardew-vlm-predictor:8080/v1/models

# Expected: {"object":"list","data":[{"id":"stardew-vlm",...}]}
```

**Internal endpoint:** `http://stardew-vlm-predictor:8080/v1`

**Important:** 
- Service name includes `-predictor` suffix
- Model ID is deployment name (`stardew-vlm`), not HuggingFace model name

---

### 4. Deploy Microservices

Update coordinator config with vLLM endpoint:

```yaml
# configs/serving/openshift/30-deployment-coordinator.yaml
env:
  - name: VLLM_ENDPOINT
    value: "http://stardew-vlm-predictor:8080/v1"  # No token needed
```

Deploy stack:

```bash
oc apply -f configs/serving/openshift/10-deployment-pierres-buying-tool.yaml
oc apply -f configs/serving/openshift/20-deployment-tts-tool.yaml
oc apply -f configs/serving/openshift/30-deployment-coordinator.yaml
oc apply -f configs/serving/openshift/40-deployment-webapp.yaml
```

---

### 5. Create External Route

```bash
# Webapp only - all other services are internal
oc create route edge stardew-vision-webapp \
  --service=webapp \
  --port=8000 \
  -n stardew-vision

# Get public URL
oc get route stardew-vision-webapp -n stardew-vision -o jsonpath='{.spec.host}'
```

---

## Quick Troubleshooting

### No GPU Option in Hardware Profile Dropdown

```bash
# Check if GPU HardwareProfile exists
oc get hardwareprofiles -n redhat-ods-applications

# If only "default-profile" shown, create GPU profile:
# See full guide: DEPLOYING_MODELS_KSERVE.md#missing-gpu-hardwareprofile
```

### Pod Stuck Pending

```bash
# Check GPU nodes
oc get nodes -l node-role.kubernetes.io/gpu-worker

# If no nodes, scale GPU MachineSet
oc scale machineset <gpu-machineset-name> --replicas=1 -n openshift-machine-api
# Wait 15-20 min
```

### vLLM Fails to Start

```bash
# Check logs
oc logs -n stardew-vision \
  -l serving.kserve.io/inferenceservice=stardew-vlm \
  -c kserve-container --tail=50

# Common issues:
# - "Failed to infer device type" → Pod on CPU node (wrong hardware profile)
# - OOM → Increase memory in hardware profile
```

---

## Architecture Quick Reference

```
┌─ stardew-vision namespace (all internal) ──────────────────┐
│                                                             │
│  stardew-vlm-predictor:8080 ← coordinator:8000 ← webapp    │
│  (vLLM inference)              (agent loop)      (FastAPI) │
│                                     ↓                ↓      │
│                              pierres-buying-tool:8002   [External Route]─→ Internet
│                              tts-tool:8000          ↑       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Only webapp has external access. All others are internal-only.**

---

## Connection Options Summary

| Method | Setup | Startup | Best For |
|--------|-------|---------|----------|
| **HF URI** ⭐ | 2 min | ~3.5 min download | Development, MVP |
| **ModelCar** | 1 hour | ~30 sec | Production |
| **S3 Storage** | 30 min | ~3 min | Custom models |

**For this project:** Use HF URI (simplest, no extra infrastructure).

---

## Key Configuration Values

| Parameter | Value | Notes |
|-----------|-------|-------|
| **Deployment name** | `stardew-vlm` | Determines service name |
| **Service name** | `stardew-vlm-predictor` | Deployment name + `-predictor` |
| **Internal endpoint** | `http://stardew-vlm-predictor:8080/v1` | For coordinator |
| **Model ID** | `stardew-vlm` | Use in API calls, NOT HF model name |
| **Model download time** | ~3.5 min | 14GB @ ~65 MB/s |
| **Total first deploy** | 25-35 min | GPU provision + download + load |
| **vLLM args** | `--max-model-len=4096 --limit-mm-per-prompt={"image":1} --enable-auto-tool-choice --tool-call-parser=hermes` | Correct format! |
| **No dtype flag** | (auto) | NVIDIA auto-selects (FP16 AMD-specific) |

---

## Optional: Faster Downloads with HF Token

```bash
# Create secret
oc create secret generic huggingface-token \
  --from-literal=token=hf_your_token_here \
  -n stardew-vision

# In wizard Advanced Settings:
# ☑️ Add custom runtime environment variables
# Name: HF_TOKEN
# Value from secret: huggingface-token, key: token
```

Authenticated requests may download faster (~2-3 min instead of ~3.5 min).

---

## Next Steps

1. ✅ Deploy vLLM (this guide)
2. Test endpoint with curl
3. Deploy microservices
4. Test end-to-end with screenshot upload
5. Monitor GPU utilization
6. Consider ModelCar for production (optional)

---

**Full documentation:** [DEPLOYING_MODELS_KSERVE.md](DEPLOYING_MODELS_KSERVE.md)

**Troubleshooting:** See full guide for detailed diagnostics and fixes.
