# Session State - OpenShift AI Model Deployment

**Last Updated**: 2026-04-11  
**Current Status**: Debugging cluster provisioning for GPU HardwareProfile

---

## 🔄 **How to Transfer This Context to a New Machine**

### **Option 1: Git Commit and Pull (Recommended)**
```bash
# On current machine (before switching):
cd /workspaces/stardew-vision
git add -A
git commit -m "Session checkpoint: GPU HardwareProfile debugging"
git push

# On new machine:
cd /workspaces/stardew-vision
git pull
# Read SESSION_STATE.md and FIRST_THING.md
```

### **Option 2: Manual File Review**
When starting a new session, read these files in order:
1. **This file** (`SESSION_STATE.md`) - Current state and blockers
2. `FIRST_THING.md` - Original deployment plan
3. `docs/DEPLOYING_MODELS_KSERVE.md` - Production deployment guide
4. `tmp/notes.md` - Session notes and questions

### **Option 3: Claude Memory (If Available)**
If the new machine has Claude Code with memory enabled, these facts should persist:
- User is working on VLM deployment to OpenShift AI
- Deployment uses internal-only networking (no external routes except webapp)
- GPU HardwareProfile is missing from cluster (blocking deployment)
- User prefers HuggingFace URI connection (not ModelCar or S3)

---

## 📍 **Current State: Where We Left Off**

### **Completed**
✅ Researched OpenShift AI deployment documentation  
✅ Created comprehensive deployment guides:
   - `docs/DEPLOYING_MODELS_KSERVE.md` (full guide)
   - `docs/DEPLOYING_MODELS_QUICKSTART.md` (quick start)
✅ Updated `FIRST_THING.md` with pointers to new guides  
✅ Created HuggingFace connection in RHOAI: `huggingface-qwen`  
✅ Identified deployment wizard UI flow (4 steps)  
✅ Attempted first model deployment (failed - see blocker below)  

### **Current Blocker** 🚧

**Problem**: GPU `HardwareProfile` missing from OpenShift AI cluster

**Symptom**: Hardware profile dropdown in model deployment wizard only shows `default-profile` (CPU/Memory). No GPU options available.

**Root Cause**: Cluster provisioning script did not create GPU HardwareProfile in `redhat-ods-applications` namespace.

**Diagnosis**:
```bash
# This command shows only default-profile:
oc get hardwareprofiles -n redhat-ods-applications

# Expected: Should show both default-profile AND nvidia-l40s-gpu (or similar)
```

**Current Action**: User switched to cluster provisioning project to fix the provisioning script.

**What Needs to Happen**:
1. Update cluster provisioning script to create GPU HardwareProfile (see YAML below)
2. Re-provision cluster OR manually create HardwareProfile
3. Return to model deployment and verify GPU option appears in dropdown
4. Complete deployment using new guides

---

## 🔑 **Critical Information for Next Session**

### **Cluster Configuration Discovered**

**GPU Infrastructure**:
- ✅ Node Feature Discovery (NFD) operator: Installed and running
- ✅ NVIDIA GPU Operator: Installed (`gpu-operator-certified.v25.3.4`)
- ✅ ClusterPolicy: Configured with tolerations for `nvidia.com/gpu`
- ✅ GPU MachineSets: Exist (`g6e.2xlarge` instances with NVIDIA L40S)
  - Currently scaled to 0 (autoscaler will provision on demand)
- ❌ **GPU HardwareProfile**: MISSING (this is the blocker)

**Namespace/Project**:
- Name: `stardew-vision`
- Type: OpenShift AI Project (has `opendatahub.io/dashboard: true` label)
- Visible in RHOAI dashboard

**Model Connection**:
- Name: `huggingface-qwen`
- Type: URI
- Target: `hf://Qwen/Qwen2.5-VL-7B-Instruct`

---

## 📋 **Missing GPU HardwareProfile YAML**

This needs to be added to the cluster provisioning script:

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
    opendatahub.io/managed: "false"
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

**Verification after applying**:
```bash
oc get hardwareprofiles -n redhat-ods-applications
# Should show: default-profile, nvidia-l40s-gpu
```

---

## 📝 **Key Decisions Made This Session**

### **1. Internal-Only Networking Architecture**
All services in `stardew-vision` namespace with internal access only:
- `stardew-vlm:8080` - vLLM inference (no external route, no auth)
- `coordinator:8000` - Agent loop (internal only)
- `ocr-tool:8000` - OpenCV + PaddleOCR (internal only)
- `tts-tool:8000` - MeloTTS (internal only)
- `webapp:8000` - FastAPI (ONLY service with external route)

**Benefits**: Security, simple DNS, no authentication overhead, lower latency

### **2. HuggingFace URI Connection (Option A)**
Chose HuggingFace direct download over ModelCar or S3:
- ✅ Simplest setup (no external storage)
- ✅ Automatic versioning from HF repo
- ✅ Works with public models
- ⏱️ Download time: ~3.5 minutes (14GB @ ~65 MB/s)
- 🔄 Can add HF token for potentially faster downloads

**Alternative**: ModelCar for production (faster startups, no download)

### **3. vLLM Runtime Arguments**
```
--max-model-len 4096 --limit-mm-per-prompt '{"image": 1}'
```

**NOT using** `--dtype=float16`:
- That was specific to AMD ROCm (Strix Halo) accelerators
- NVIDIA GPUs auto-select optimal precision
- Platform handles defaults better for NVIDIA

### **4. Deployment Naming**
- InferenceService name: `stardew-vlm`
- Internal endpoint: `http://stardew-vlm:8080/v1`
  - Full DNS: `http://stardew-vlm-predictor.stardew-vision.svc.cluster.local:8080/v1`
  - Short form works within namespace: `http://stardew-vlm:8080/v1`

---

## 🐛 **Troubleshooting Reference**

### **First Deployment Attempt - Failed**

**What Happened**:
1. Created HuggingFace connection successfully
2. Started deployment wizard
3. Step 2 (Model Deployment) - Hardware profile dropdown only showed `default-profile`
4. No GPU option available
5. Attempted to deploy anyway (for testing)
6. Pod scheduled to CPU node (`ip-10-0-7-90.us-east-2.compute.internal`)
7. vLLM failed with: `RuntimeError: Failed to infer device type`

**Pod Log Evidence**:
```
INFO 04-11 20:32:23 [importing.py:68] Triton not installed or not compatible
W0411 20:32:23.951000 1 No CUDA runtime is found, using CUDA_HOME='/usr/local/cuda'
RuntimeError: Failed to infer device type, please set the environment variable `VLLM_LOGGING_LEVEL=DEBUG`
```

**Pod Spec Analysis**:
```yaml
resources:
  limits:
    cpu: "2"
    memory: 4Gi
  requests:
    cpu: "2"
    memory: 4Gi
# ❌ MISSING: nvidia.com/gpu: "1"

tolerations:
  - effect: NoSchedule
    key: node.kubernetes.io/memory-pressure
# ❌ MISSING: nvidia.com/gpu toleration
```

**InferenceService deleted** - will redeploy after HardwareProfile is fixed.

---

## 📚 **Documentation Created This Session**

### **New Files**
1. `docs/DEPLOYING_MODELS_KSERVE.md` - Full deployment guide (500+ lines)
   - Prerequisites and verification
   - Architecture overview
   - RHOAI Project vs Namespace explained
   - Connection options comparison (HF URI, ModelCar, S3)
   - Step-by-step wizard instructions
   - Troubleshooting section (including HardwareProfile fix)

2. `docs/DEPLOYING_MODELS_QUICKSTART.md` - Quick start checklist (~200 lines)
   - Prerequisites checklist
   - 5-minute deployment sequence
   - Quick troubleshooting
   - Configuration reference table

3. `tmp/notes.md` - Session notes with questions (created by user)
   - Question about RHOAI project vs namespace
   - Connection options pros/cons
   - vLLM argument questions
   - Download timing observations
   - Internal endpoint naming

### **Updated Files**
1. `FIRST_THING.md` - Added banner pointing to new guides

---

## 🎯 **Next Steps (In Order)**

### **Immediate (Cluster Provisioning)**
1. ✅ Switch to cluster provisioning project (user doing this now)
2. Add GPU HardwareProfile to provisioning script (YAML above)
3. Decide: Re-provision cluster OR manually apply HardwareProfile
4. Verify: `oc get hardwareprofiles -n redhat-ods-applications` shows GPU profile

### **After HardwareProfile Fixed**
5. Return to `stardew-vision` project in RHOAI dashboard
6. Deploy model using `docs/DEPLOYING_MODELS_QUICKSTART.md`
7. Select `nvidia-l40s-gpu` in Hardware profile dropdown
8. Wait for deployment (~25-35 min first time: GPU node + download + load)
9. Verify internal endpoint: `curl http://stardew-vlm:8080/v1/models`
10. Deploy microservices (OCR, TTS, coordinator, webapp)
11. Create external route for webapp only
12. Test end-to-end with Pierre's shop screenshot

---

## 📊 **Timeline Expectations**

| Phase | Duration | Notes |
|-------|----------|-------|
| **Fix HardwareProfile** | 5-10 min | Update script + apply |
| **GPU Node Provision** | 15-20 min | First deployment only (autoscaler) |
| **Model Download** | ~3.5 min | 14GB from HuggingFace |
| **Model Loading** | 5-8 min | vLLM loads into GPU memory |
| **Total First Deploy** | ~25-35 min | After HardwareProfile fixed |
| **Subsequent Restarts** | 5-10 min | If model cached to PVC |

---

## 🔗 **Quick Reference Commands**

### **Check Prerequisites**
```bash
# GPU HardwareProfile (blocker check)
oc get hardwareprofiles -n redhat-ods-applications

# GPU nodes (should be 0 initially, autoscaler provisions on demand)
oc get nodes -l node-role.kubernetes.io/gpu-worker

# GPU MachineSets
oc get machineset -n openshift-machine-api | grep gpu

# Verify operators
oc get csv -n openshift-nfd | grep nfd
oc get csv -n nvidia-gpu-operator | grep gpu-operator
```

### **Monitor Deployment**
```bash
# InferenceService status
oc get inferenceservice stardew-vlm -n stardew-vision -w

# Pod status
oc get pods -n stardew-vision -l serving.kserve.io/inferenceservice=stardew-vlm

# Download logs (init container)
oc logs -n stardew-vision -l serving.kserve.io/inferenceservice=stardew-vlm -c storage-initializer -f

# vLLM startup logs
oc logs -n stardew-vision -l serving.kserve.io/inferenceservice=stardew-vlm -c kserve-container -f
```

### **Test Internal Endpoint**
```bash
# From debug pod
oc run curl-test --image=curlimages/curl -n stardew-vision --rm -it -- \
  curl http://stardew-vlm:8080/v1/models
```

---

## 💡 **Lessons Learned This Session**

1. **RHOAI Projects ≠ Regular Namespaces**: Need `opendatahub.io/dashboard: true` label to appear in RHOAI UI
2. **GPU HardwareProfile is Critical**: Without it, web UI doesn't show GPU options
3. **Hardware Profile Must Exist Before Deployment**: Can't select GPU if profile doesn't exist
4. **Internal Endpoint Naming**: `http://<deployment-name>-predictor:8080` OR `http://<deployment-name>:8080` (KServe convention)
5. **Download Time is Predictable**: ~3.5 min for 14GB model, can add HF token for optimization
6. **NVIDIA vs AMD vLLM Args**: Don't copy `--dtype` flags from AMD docs to NVIDIA deployments

---

## 📧 **Context for Future Claude Sessions**

When resuming work, tell Claude:

> "I'm working on deploying Qwen2.5-VL-7B to OpenShift AI for the stardew-vision project. Read SESSION_STATE.md for current status. We're blocked on missing GPU HardwareProfile - currently fixing cluster provisioning script. Once fixed, we'll deploy using docs/DEPLOYING_MODELS_QUICKSTART.md with internal-only networking (no external routes except webapp)."

---

**End of Session State**

Last action: User switched to cluster provisioning project to debug HardwareProfile creation.  
Next action: Fix provisioning script, apply HardwareProfile, resume model deployment.
