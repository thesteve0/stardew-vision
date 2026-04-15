# Deploying Vision-Language Models with KServe on OpenShift AI

**Deployment Guide for Qwen2.5-VL-7B-Instruct on Red Hat OpenShift AI 3.2+**

This guide covers deploying a vision-language model (VLM) using vLLM serving runtime and KServe on Red Hat OpenShift AI (RHOAI). The deployment uses internal-only networking for microservice communication with a single external endpoint for the web application.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Architecture Overview](#architecture-overview)
3. [Understanding RHOAI Projects vs Namespaces](#understanding-rhoai-projects-vs-namespaces)
4. [Model Connection Options](#model-connection-options)
5. [Deployment Steps](#deployment-steps)
6. [Troubleshooting](#troubleshooting)
7. [References](#references)

---

## Prerequisites

### Required Cluster Components

Before deploying models, verify these components are installed and configured:

#### 1. **Node Feature Discovery (NFD) Operator**
```bash
oc get csv -n openshift-nfd
# Expected: nfd.4.x.x in "Succeeded" phase
```

#### 2. **NVIDIA GPU Operator**
```bash
oc get csv -n nvidia-gpu-operator
# Expected: gpu-operator-certified.vXX.X.X in "Succeeded" phase

# Verify ClusterPolicy
oc get clusterpolicy -n nvidia-gpu-operator
```

#### 3. **GPU MachineSets** (with autoscaling)
```bash
oc get machineset -n openshift-machine-api | grep gpu
# Should show GPU machinesets (e.g., g6e.2xlarge for L40S GPUs)
```

#### 4. **GPU HardwareProfile** (Critical!)

RHOAI 3.2+ requires a GPU `HardwareProfile` to expose GPU options in the web UI:

```bash
oc get hardwareprofiles -n redhat-ods-applications
```

**Expected output:**
- `default-profile` (CPU/Memory)
- `nvidia-l40s-gpu` (or similar GPU profile)

**If missing:** Your cluster provisioning script needs to create the GPU HardwareProfile. See [Troubleshooting](#missing-gpu-hardwareprofile) below.

---

## Architecture Overview

### Internal Networking Strategy

All services in this project run in the **same namespace** (`stardew-vision`) with internal-only access:

```
┌─────────────────────────────────────────────────────────┐
│  stardew-vision namespace (OpenShift AI Project)        │
│                                                          │
│  ┌────────────────────────────────────────────┐         │
│  │  stardew-vlm-predictor:8080                │         │
│  │  (Qwen2.5-VL-7B via vLLM + KServe)        │         │
│  │  - InferenceService (RawDeployment)        │         │
│  │  - No external route                       │         │
│  │  - No token authentication                 │         │
│  └───────────────┬────────────────────────────┘         │
│                  │                                       │
│  ┌───────────────▼────────────────────────────┐         │
│  │  coordinator:8000                          │         │
│  │  (Agent loop, tool dispatch)               │         │
│  │  - Calls VLM for reasoning                 │         │
│  │  - Executes extraction/TTS tools           │         │
│  └───────┬──────────────────┬─────────────────┘         │
│          │                  │                            │
│  ┌───────▼─────┐    ┌──────▼──────┐                    │
│  │ pierres-buying-tool    │    │  tts-tool   │                    │
│  │ :8000       │    │  :8000      │                    │
│  └─────────────┘    └─────────────┘                    │
│          │                  │                            │
│  ┌───────▼──────────────────▼─────────────────┐         │
│  │  webapp:8000                               │         │
│  │  (FastAPI + static HTML)                   │         │
│  └────────────────┬───────────────────────────┘         │
│                   │                                      │
└───────────────────┼──────────────────────────────────────┘
                    │
             [External Route] ← ONLY public access point
                    │
                 Internet
```

### Benefits of Internal Networking

- ✅ **Security**: Only webapp exposed externally (minimal attack surface)
- ✅ **Simple DNS**: Services use Kubernetes DNS (e.g., `http://stardew-vlm:8080`)
- ✅ **No Authentication**: Internal services trust namespace boundary
- ✅ **Lower Latency**: Traffic stays within cluster network

---

## Understanding RHOAI Projects vs Namespaces

### What is an RHOAI Project?

An **OpenShift AI (RHOAI) Project** is a namespace with additional metadata that makes it visible in the RHOAI dashboard:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: stardew-vision
  labels:
    opendatahub.io/dashboard: "true"  # Makes it appear in RHOAI UI
    modelmesh-enabled: "false"        # Using KServe, not ModelMesh
  annotations:
    openshift.io/display-name: "Stardew Vision"
    openshift.io/description: "VLM-powered accessibility for Stardew Valley UI"
```

### Creating an RHOAI Project

**Option 1: Via RHOAI Dashboard**
1. Navigate to **Data Science Projects** tab
2. Click **Create data science project**
3. Enter project name and description
4. RHOAI automatically adds required labels

**Option 2: Via CLI**
```bash
oc new-project stardew-vision \
  --display-name="Stardew Vision" \
  --description="VLM-powered accessibility for Stardew Valley UI"

# Add RHOAI labels
oc label namespace stardew-vision opendatahub.io/dashboard=true
oc label namespace stardew-vision modelmesh-enabled=false
```

### Key Differences

| Feature | Regular Namespace | RHOAI Project |
|---------|-------------------|---------------|
| Kubernetes namespace | ✅ | ✅ |
| Visible in OpenShift Console | ✅ | ✅ |
| Visible in RHOAI Dashboard | ❌ | ✅ |
| Model deployment UI | ❌ | ✅ |
| Notebook spawning | ❌ | ✅ |
| Pipeline integration | ❌ | ✅ |

**Important:** Your provisioning scripts should create an RHOAI Project (not just a namespace) to enable model deployment features.

---

## Model Connection Options

OpenShift AI supports three methods for providing models to KServe InferenceServices:

### Option A: HuggingFace URI (Direct Download) ⭐ **Recommended**

**How it works:**
- Model downloads directly from HuggingFace Hub during init container phase
- No manual upload or S3 bucket needed
- Cached to ephemeral storage (or PVC if configured)

**Connection setup:**
```yaml
Connection Type: URI
Name: huggingface-qwen
URI: hf://Qwen/Qwen2.5-VL-7B-Instruct
```

**Pros:**
- ✅ Simplest setup (no external storage needed)
- ✅ Automatic model versioning (tracks HF repo)
- ✅ Works with public and gated models (via HF token)
- ✅ No S3 bucket costs

**Cons:**
- ❌ Downloads ~14GB on first startup (~3.5 min with good connection)
- ❌ Re-downloads if pod restarts (unless PVC cache configured)
- ❌ Requires outbound internet access from cluster

**Download Performance:**
- **Without HF token**: ~3.5 minutes (14GB @ ~65 MB/s)
- **With HF token**: Potentially faster (authenticated requests prioritized)

**To use HF token for faster downloads:**
```bash
# Create secret with HF token
oc create secret generic huggingface-token \
  --from-literal=token=hf_xxxxxxxxxxxx \
  -n stardew-vision

# Reference in InferenceService (Advanced Settings → Environment Variables):
# HF_TOKEN → secret:huggingface-token:token
```

---

### Option B: ModelCar Container Image (Pre-packaged)

**How it works:**
- Model baked into OCI container image using ModelCar tools
- Image stored in registry (Quay.io, Harbor, etc.)
- No download at runtime - model is in the image layers

**Connection setup:**
```yaml
Connection Type: URI
Name: qwen-modelcar
URI: oci://quay.io/youruser/qwen-modelcar:latest
Registry credentials: (if private registry)
```

**Pros:**
- ✅ Fastest startup (no download - model in image)
- ✅ Version control via image tags
- ✅ Works in air-gapped environments
- ✅ Consistent model across deployments

**Cons:**
- ❌ Requires building and pushing large images (~15-20GB)
- ❌ Registry storage costs
- ❌ More complex build pipeline
- ❌ Slower iteration (rebuild image for each model change)

**When to use:**
- Production deployments requiring fast cold starts
- Air-gapped or restricted network environments
- Compliance requiring model artifact control

**Build example:**
See [Red Hat Developer: Build and deploy a ModelCar container](https://developers.redhat.com/articles/2025/01/30/build-and-deploy-modelcar-container-openshift-ai)

---

### Option C: S3-Compatible Storage (MinIO, AWS S3)

**How it works:**
- Model files uploaded to S3 bucket
- Init container downloads from S3 at startup
- Useful for models not on HuggingFace or for caching

**Connection setup:**
```yaml
Connection Type: S3 compatible object storage
Name: s3-models
Endpoint: https://s3.us-east-1.amazonaws.com (or MinIO endpoint)
Bucket: my-models
Access Key: AKIA...
Secret Key: (secret)
Path: models/qwen2.5-vl-7b-instruct/
```

**Pros:**
- ✅ Works with custom/fine-tuned models
- ✅ Centralized model storage
- ✅ Multi-model deployments can share storage
- ✅ Version control via bucket paths

**Cons:**
- ❌ Requires S3 setup and management
- ❌ Storage costs (AWS/MinIO)
- ❌ Manual model upload process
- ❌ Network bandwidth costs (AWS egress)

**When to use:**
- Custom fine-tuned models
- Internal model registry requirements
- Multi-region deployments with S3 replication

---

### Comparison Table

| Criterion | HF URI | ModelCar | S3 Storage |
|-----------|--------|----------|------------|
| **Setup complexity** | 🟢 Simple | 🟡 Medium | 🟡 Medium |
| **First startup time** | 🟡 ~3.5 min | 🟢 ~30 sec | 🟡 ~3 min |
| **Restart time** | 🔴 ~3.5 min | 🟢 ~30 sec | 🟡 ~3 min* |
| **Storage cost** | 🟢 Free | 🟡 Registry | 🔴 S3 costs |
| **Air-gapped support** | 🔴 No | 🟢 Yes | 🟢 Yes |
| **Model updates** | 🟢 Auto | 🟡 Rebuild | 🟡 Re-upload |
| **Best for** | Development | Production | Custom models |

*With PVC cache

**Recommendation for Stardew Vision:** Use **Option A (HuggingFace URI)** for development and MVP. Consider ModelCar for production if cold-start time becomes critical.

---

## Deployment Steps

### Step 1: Verify Prerequisites

```bash
# Check RHOAI project exists
oc get project stardew-vision

# Check GPU HardwareProfile exists
oc get hardwareprofiles -n redhat-ods-applications

# Check GPU MachineSet autoscaler
oc get machineset -n openshift-machine-api | grep gpu
```

---

### Step 2: Create HuggingFace Connection

1. Navigate to **OpenShift AI Dashboard** → **Data Science Projects**
2. Select **stardew-vision** project
3. Click **Connections** tab
4. Click **Add connection**

**Configuration:**

| Field | Value |
|-------|-------|
| **Connection type** | URI |
| **Name** | `huggingface-qwen` |
| **URI** | `hf://Qwen/Qwen2.5-VL-7B-Instruct` |
| **Description** | "Qwen2.5-VL-7B for multimodal UI analysis" |

5. Click **Add connection**

**Optional - Add HuggingFace Token for Faster Downloads:**

1. Create secret with HF token:
   ```bash
   oc create secret generic huggingface-token \
     --from-literal=token=hf_your_token_here \
     -n stardew-vision
   ```

2. You'll reference this secret in Advanced Settings during deployment

---

### Step 3: Deploy Model via 4-Step Wizard

#### Launch Wizard

1. In `stardew-vision` project, scroll to **"Serve models"** section
2. Click **"Start by deploying a model"**

---

#### Wizard Step 1: Model Details

| Field | Value |
|-------|-------|
| **Model location** | Existing connection |
| **Connection** | `huggingface-qwen` |
| **Model type** | Generative AI model (Example, LLM) |

Click **Next** →

---

#### Wizard Step 2: Model Deployment

| Field | Value | Notes |
|-------|-------|-------|
| **Model deployment name** | `stardew-vlm` | Internal service will be `stardew-vlm-predictor` |
| **Serving runtime** | vLLM NVIDIA GPU ServingRuntime for KServe | |
| **Model framework** | PyTorch | (auto-detected) |
| **Deployment mode** | Standard | RawDeployment - simpler, fixed replicas |
| **Hardware profile** | `nvidia-l40s-gpu` | **Critical**: Must select GPU profile |
| **Number of replicas** | `1` | Fixed replica for MVP |
| **Model route** | ❌ **UNCHECK** | Internal-only access |
| **Token authentication** | ❌ **UNCHECK** | No auth for internal services |

**Important Notes:**
- ✅ **Hardware profile** must show a GPU option (e.g., `nvidia-l40s-gpu`)
- ❌ If only `default-profile` appears, your GPU HardwareProfile is missing - see [Troubleshooting](#missing-gpu-hardwareprofile)
- ✅ Unchecking "Model route" prevents external exposure
- ✅ Internal endpoint: `http://stardew-vlm-predictor:8080/v1` (based on deployment name)

Click **Next** →

---

#### Wizard Step 3: Advanced Settings

**Model playground availability:**
- ☑️ **Check** "Add as AI asset endpoint" (enables testing in Gen AI Playground)
- **Use case** field: "Multimodal vision-language model for UI screen analysis"

**Model access:**
- ❌ **UNCHECK** "Make model deployment available through an external route"

**Token authentication:**
- ❌ **UNCHECK** "Require token authentication"

**Configuration parameters:**

1. ☑️ **Check** "Add custom runtime arguments"
   
   **Additional serving runtime arguments:**
   ```
   --max-model-len=4096 --limit-mm-per-prompt={"image":1} --enable-auto-tool-choice --tool-call-parser=hermes
   ```
   
   **What these do:**
   - `--max-model-len=4096`: Context window size (4K tokens)
   - `--limit-mm-per-prompt={"image":1}`: Enable vision input (1 image per prompt)
   - `--enable-auto-tool-choice`: Enable automatic tool calling mode (required for agent loops)
   - `--tool-call-parser=hermes`: Use Hermes parser for tool call extraction
   
   **Critical formatting rules:**
   - ✅ Use `=` between flag and value: `--flag=value`
   - ✅ No spaces in JSON: `{"image":1}` not `{"image": 1}`
   - ✅ No quotes around the entire argument
   - ❌ Wrong: `--limit-mm-per-prompt '{"image": 1}'`
   - ✅ Correct: `--limit-mm-per-prompt={"image":1}`
   
   **Note:** We do NOT specify `--dtype=float16` here. That was specific to AMD ROCm accelerators (Strix Halo). NVIDIA GPUs auto-select the optimal precision.

2. ⬜ **UNCHECK** "Add custom runtime environment variables" (defaults are fine)
   
   **Optional - If using HF token for faster downloads:**
   - ☑️ **Check** "Add custom runtime environment variables"
   - Add variable:
     - Name: `HF_TOKEN`
     - Value: Reference secret `huggingface-token`, key `token`

**Deployment strategy:**
- ⦿ **Select** "Rolling update" (default)

Click **Next** →

---

#### Wizard Step 4: Review

1. Review all settings
2. **Verify:**
   - Deployment name: `stardew-vlm`
   - Hardware profile: GPU profile selected
   - Model route: **DISABLED**
   - Token auth: **DISABLED**

3. Click **Deploy** 🚀

---

### Step 4: Monitor Deployment

#### Timeline

| Phase | Duration | Description |
|-------|----------|-------------|
| **Creating** | ~30 seconds | Pod scheduling |
| **GPU Node Provisioning** | 15-20 min | If autoscaler needs to scale up GPU MachineSet (first deployment only) |
| **Downloading** | ~3.5 min | Init container downloads 14GB model from HuggingFace (~65 MB/s) |
| **Loading** | ~5-8 min | vLLM loads model into GPU memory |
| **Ready** ✅ | Total: ~25-35 min | Internal endpoint active |

**With HF token:** Download may be slightly faster due to authenticated request prioritization.

#### Monitor via Dashboard

1. Stay on **Deployments** tab (or **Overview** page)
2. Watch status progression:
   - Creating → Downloading → Loading → Ready ✅

#### Monitor via Logs (Optional)

**Check init container (download progress):**
```bash
oc logs -n stardew-vision \
  -l serving.kserve.io/inferenceservice=stardew-vlm \
  -c storage-initializer -f
```

**Example output:**
```
INFO:root:Copying contents of hf://Qwen/Qwen2.5-VL-7B-Instruct to local
Downloading model files: 100%|██████████| 14.2G/14.2G [03:37<00:00, 65.2MB/s]
Model downloaded in 217.60 seconds
```

**Check vLLM startup:**
```bash
oc logs -n stardew-vision \
  -l serving.kserve.io/inferenceservice=stardew-vlm \
  -c kserve-container -f
```

**Expected output:**
```
INFO:     vllm.engine.llm_engine - Initializing an LLM engine with config: ...
INFO:     vllm.engine.llm_engine - # GPU blocks: 2048, # CPU blocks: 512
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8080
```

---

### Step 5: Verify Internal Endpoint

#### Internal Service DNS

Based on deployment name `stardew-vlm`, the internal endpoint is:

- **Full DNS**: `http://stardew-vlm-predictor.stardew-vision.svc.cluster.local:8080/v1`
- **Short form** (same namespace): `http://stardew-vlm-predictor:8080/v1`

**For coordinator configuration:**
```yaml
env:
  - name: VLLM_ENDPOINT
    value: "http://stardew-vlm-predictor:8080/v1"  # No token needed!
```

**Note:** The service name is `<deployment-name>-predictor`, NOT just the deployment name. Always use the `-predictor` suffix.

#### Test from Cluster

Create a debug pod to test internal connectivity:

```bash
# Start debug pod
oc run curl-test --image=curlimages/curl -n stardew-vision --rm -it -- sh

# Test 1: Check model is loaded
curl http://stardew-vlm-predictor:8080/v1/models

# Expected output:
# {"object":"list","data":[{"id":"stardew-vlm",...}]}
# Note: Model ID is the deployment name, not the HuggingFace model name

# Test 2: Simple text inference
curl -X POST http://stardew-vlm-predictor:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "stardew-vlm",
    "messages": [
      {"role": "user", "content": "What is 2+2?"}
    ],
    "max_tokens": 50
  }'

# Expected: JSON response with completion
```

**No authentication needed** - internal services trust the namespace boundary.

**Important:** The model ID in API requests is the deployment name (`stardew-vlm`), not the HuggingFace model name (`Qwen/Qwen2.5-VL-7B-Instruct`).

---

### Step 6: Deploy Microservices

Once vLLM is verified, deploy the rest of the stack:

```bash
# OCR extraction tool (internal only)
oc apply -f configs/serving/openshift/10-deployment-pierres-buying-tool.yaml

# TTS synthesis tool (internal only)
oc apply -f configs/serving/openshift/20-deployment-tts-tool.yaml

# Coordinator agent runtime (internal only)
# Update VLLM_ENDPOINT to: http://stardew-vlm-predictor:8080/v1
oc apply -f configs/serving/openshift/30-deployment-coordinator.yaml

# Webapp frontend (will have external route)
oc apply -f configs/serving/openshift/40-deployment-webapp.yaml
```

---

### Step 7: Create External Route (Webapp Only)

```bash
# Create route for webapp
oc create route edge stardew-vision-webapp \
  --service=webapp \
  --port=8000 \
  -n stardew-vision

# Get the public URL
oc get route stardew-vision-webapp -n stardew-vision \
  -o jsonpath='{.spec.host}'
```

**Result:** Users access only the webapp URL. All other services are internal-only.

---

## Troubleshooting

### Missing GPU HardwareProfile

**Symptom:** Hardware profile dropdown only shows `default-profile` (CPU/Memory). No GPU options.

**Cause:** GPU `HardwareProfile` not created during cluster provisioning.

**Diagnosis:**
```bash
oc get hardwareprofiles -n redhat-ods-applications

# If only "default-profile" appears, GPU profile is missing
```

**Fix:** Update your cluster provisioning script to create GPU HardwareProfile:

```yaml
apiVersion: infrastructure.opendatahub.io/v1
kind: HardwareProfile
metadata:
  name: nvidia-l40s-gpu
  namespace: redhat-ods-applications
  annotations:
    opendatahub.io/description: "NVIDIA L40S GPU with 8 CPUs and 32 GiB memory"
    opendatahub.io/display-name: "NVIDIA L40S GPU"
    opendatahub.io/disabled: "false"
  labels:
    app.kubernetes.io/part-of: hardwareprofile
    app.opendatahub.io/hardwareprofile: "true"
spec:
  identifiers:
    - identifier: cpu
      displayName: CPU
      resourceType: CPU
      defaultCount: 4
      minCount: 2
      maxCount: 8
    - identifier: memory
      displayName: Memory
      resourceType: Memory
      defaultCount: 24Gi
      minCount: 16Gi
      maxCount: 64Gi
    - identifier: nvidia.com/gpu
      displayName: NVIDIA GPU
      resourceType: GPU
      defaultCount: 1
      minCount: 1
      maxCount: 1
  nodeSelector:
    nvidia.com/gpu.present: "true"
  tolerations:
    - key: nvidia.com/gpu
      operator: Exists
      effect: NoSchedule
```

**Verify:**
```bash
oc get hardwareprofiles -n redhat-ods-applications
# Should now show: default-profile, nvidia-l40s-gpu
```

**After creating HardwareProfile:** Refresh the RHOAI dashboard and retry model deployment.

---

### Pod Scheduled to CPU Node (No GPU)

**Symptom:** Pod starts but vLLM fails with:
```
RuntimeError: Failed to infer device type
```

**Cause:** Pod scheduled to CPU-only node. InferenceService missing GPU resource request or tolerations.

**Diagnosis:**
```bash
# Check pod spec for GPU resources
oc get pod -n stardew-vision \
  -l serving.kserve.io/inferenceservice=stardew-vlm \
  -o jsonpath='{.items[0].spec.containers[*].resources}'

# Expected: nvidia.com/gpu: "1" in both requests and limits
# If missing, InferenceService wasn't configured correctly
```

**Fix:** Delete InferenceService and redeploy, ensuring you select a **GPU hardware profile** in Step 2 of the wizard.

---

### GPU Node Not Available

**Symptom:** Pod stuck in `Pending` state.

**Diagnosis:**
```bash
oc get pod -n stardew-vision \
  -l serving.kserve.io/inferenceservice=stardew-vlm

# If STATUS = Pending, check events:
oc describe pod -n stardew-vision \
  -l serving.kserve.io/inferenceservice=stardew-vlm \
  | grep -A 10 Events

# Look for: "0/X nodes are available: insufficient nvidia.com/gpu"
```

**Cause:** GPU MachineSet scaled to 0 or autoscaler hasn't triggered yet.

**Fix:**
```bash
# Check GPU MachineSet status
oc get machineset -n openshift-machine-api | grep gpu

# Manually scale up if autoscaler is slow
oc scale machineset <gpu-machineset-name> \
  --replicas=1 \
  -n openshift-machine-api

# Wait 15-20 min for GPU node provisioning
oc get machines -n openshift-machine-api -w
```

---

### Slow Model Download

**Symptom:** Init container takes >5 minutes to download model.

**Possible causes:**
- Network bandwidth limitations
- HuggingFace Hub rate limiting (unauthenticated requests)
- Cluster egress restrictions

**Solutions:**

1. **Add HuggingFace token for authenticated downloads:**
   ```bash
   oc create secret generic huggingface-token \
     --from-literal=token=hf_your_token_here \
     -n stardew-vision
   ```
   
   Then add environment variable in InferenceService (Advanced Settings):
   - Name: `HF_TOKEN`
   - Value from secret: `huggingface-token`, key `token`

2. **Configure PVC for model caching** (avoids re-downloads on restart):
   - In Advanced Settings, add volume mount
   - PVC path: `/cache`
   - Environment variable: `HF_HUB_CACHE=/cache`

3. **Consider ModelCar image** for production (no download at runtime)

---

### InferenceService Shows "Ready" but Endpoint Fails

**Symptom:** `oc get inferenceservice` shows `READY=True`, but curl to endpoint fails.

**Diagnosis:**
```bash
# Check if predictor pod is actually running
oc get pods -n stardew-vision -l serving.kserve.io/inferenceservice=stardew-vlm

# Check vLLM logs for errors
oc logs -n stardew-vision \
  -l serving.kserve.io/inferenceservice=stardew-vlm \
  -c kserve-container --tail=100
```

**Common issues:**
- vLLM crashed after startup (OOM, GPU error)
- Model file corruption during download
- Incorrect vLLM arguments

**Fix:** Check logs for specific error, adjust resources or arguments, redeploy.

---

## References

### Official Documentation

- [How to deploy language models with Red Hat OpenShift AI](https://developers.redhat.com/articles/2025/09/10/how-deploy-language-models-red-hat-openshift-ai) (Sept 2025)
- [OpenShift AI 3.2 - Deploying Models](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.2/html-single/deploying_models/index)
- [OpenShift AI 3.3 - Working with Model Catalog](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.3/pdf/working_with_the_model_catalog/)
- [Build and deploy ModelCar container](https://developers.redhat.com/articles/2025/01/30/build-and-deploy-modelcar-container-openshift-ai)
- [Autoscaling vLLM with OpenShift AI](https://developers.redhat.com/articles/2025/10/02/autoscaling-vllm-openshift-ai)

### Model Information

- **Model**: [Qwen/Qwen2.5-VL-7B-Instruct](https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct)
- **Size**: ~14GB
- **License**: Apache 2.0
- **Capabilities**: Vision-language understanding, OCR, image reasoning

### vLLM Configuration Reference

- [vLLM Engine Arguments](https://github.com/vllm-project/vllm/blob/main/vllm/engine/arg_utils.py)
- [vLLM OpenAI-Compatible Server](https://docs.vllm.ai/en/latest/serving/openai_compatible_server.html)

---

## Next Steps

1. ✅ Deploy vLLM with Qwen2.5-VL-7B (this guide)
2. Test internal endpoint with curl
3. Deploy microservices (OCR, TTS, coordinator)
4. Create external route for webapp
5. Test end-to-end workflow with Pierre's shop screenshot
6. Monitor GPU utilization and adjust resources if needed
7. Consider ModelCar image for production (faster cold starts)
8. Implement PVC model cache (reduce restarts to ~30 seconds)

---

**Deployment successful!** 🎉

Your VLM is now serving at `http://stardew-vlm-predictor:8080/v1` for internal microservice calls.

**Key Facts:**
- Service name: `stardew-vlm-predictor` (deployment name + `-predictor` suffix)
- Model ID for API calls: `stardew-vlm` (deployment name, not HuggingFace model name)
- No authentication required for internal traffic
