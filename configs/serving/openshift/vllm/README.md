# vLLM Deployment for Qwen2.5-VL-7B on OpenShift AI

Complete YAML-based deployment for vLLM with KServe on Red Hat OpenShift AI, serving Qwen2.5-VL-7B-Instruct vision-language model.

---

## 📋 **Prerequisites**

### **1. GPU HardwareProfile Must Exist**

The GPU HardwareProfile must be created in the `redhat-ods-applications` namespace **before deploying**:

```bash
# Check if it exists
oc get hardwareprofiles -n redhat-ods-applications

# If missing, create it (usually done by cluster provisioning)
oc apply -f 01-gpu-hardwareprofile.yaml
```

**Why:** Without this, the InferenceService won't get GPU resources.

### **2. GPU Nodes Available**

```bash
# Check GPU MachineSets
oc get machineset -n openshift-machine-api | grep gpu

# If scaled to 0, the autoscaler will provision on-demand (~15-20 min)
# Or manually scale up:
oc scale machineset <gpu-machineset-name> --replicas=1 -n openshift-machine-api
```

### **3. Verify Operators Installed**

```bash
# Node Feature Discovery
oc get csv -n openshift-nfd | grep nfd

# NVIDIA GPU Operator
oc get csv -n nvidia-gpu-operator | grep gpu-operator
```

---

## 🚀 **Deployment Steps**

### **Step 1: Create HuggingFace Connection**

```bash
oc apply -f 00-huggingface-connection.yaml
```

**What it does:** Creates a secret with the HuggingFace model URI for direct download.

**Verify:**
```bash
oc get secret huggingface-qwen -n stardew-vision
```

---

### **Step 2: Create ServingRuntime**

```bash
oc apply -f 02-vllm-servingruntime.yaml
```

**What it does:** Defines the vLLM runtime configuration (container image, ports, etc.)

**Verify:**
```bash
oc get servingruntime stardew-vlm -n stardew-vision
```

---

### **Step 3: Deploy InferenceService**

```bash
oc apply -f 03-inferenceservice.yaml
```

**What it does:** 
- Creates the vLLM deployment
- Downloads Qwen2.5-VL-7B-Instruct from HuggingFace (~14GB, ~3.5 min)
- Loads model into GPU memory (~5-8 min)
- Creates internal service `stardew-vlm-predictor:8080`

**Monitor deployment:**
```bash
# Watch InferenceService status
oc get inferenceservice stardew-vlm -n stardew-vision -w

# Watch pods
oc get pods -n stardew-vision -l serving.kserve.io/inferenceservice=stardew-vlm -w
```

**Expected timeline:**
- GPU node provision: 15-20 min (first deployment only, if needed)
- Model download: ~3.5 min
- Model loading: ~5-8 min
- **Total:** 25-35 min (first deployment)

---

### **Step 4: Verify Deployment**

#### **Check InferenceService Status**

```bash
oc get inferenceservice stardew-vlm -n stardew-vision
```

**Expected output:**
```
NAME          URL                                              READY   PREV   LATEST
stardew-vlm   http://stardew-vlm-predictor.stardew-vision...   True    100
```

#### **Check Pod Logs**

```bash
# Download progress (init container)
oc logs -n stardew-vision \
  -l serving.kserve.io/inferenceservice=stardew-vlm \
  -c storage-initializer -f

# vLLM startup
oc logs -n stardew-vision \
  -l serving.kserve.io/inferenceservice=stardew-vlm \
  -c kserve-container -f
```

**Success indicators in logs:**
- `Model downloaded in X seconds`
- `Multimodal image limit per prompt: {'image': 1}`
- `# GPU blocks: XXXX`
- `Application startup complete`

#### **Test Internal Endpoint**

```bash
# Get pod name
POD=$(oc get pods -n stardew-vision -l serving.kserve.io/inferenceservice=stardew-vlm -o jsonpath='{.items[0].metadata.name}')

# Test models endpoint
oc exec -n stardew-vision $POD -- \
  curl -s http://localhost:8080/v1/models

# Expected: {"object":"list","data":[{"id":"stardew-vlm",...}]}

# Test chat completion
oc exec -n stardew-vision $POD -- \
  curl -s http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"stardew-vlm","messages":[{"role":"user","content":"What is 2+2?"}],"max_tokens":50}'

# Expected: {"choices":[{"message":{"content":"2 + 2 equals 4."}}]}
```

#### **Test from Another Pod (Service Discovery)**

```bash
oc run curl-test --image=curlimages/curl -n stardew-vision --rm -it -- \
  curl http://stardew-vlm-predictor:8080/v1/models
```

---

## 🔧 **Configuration Reference**

### **Internal Endpoint**

**Service name:** `stardew-vlm-predictor` (deployment name + `-predictor` suffix)

**Endpoints:**
- Full DNS: `http://stardew-vlm-predictor.stardew-vision.svc.cluster.local:8080/v1`
- Short form (same namespace): `http://stardew-vlm-predictor:8080/v1`

**Use in coordinator:**
```yaml
env:
  - name: VLLM_BASE_URL
    value: "http://stardew-vlm-predictor:8080/v1"
  - name: VLLM_MODEL
    value: "stardew-vlm"  # NOT "Qwen/Qwen2.5-VL-7B-Instruct"
```

### **Model ID**

**In API requests:** Use deployment name `stardew-vlm`  
**NOT:** HuggingFace model name `Qwen/Qwen2.5-VL-7B-Instruct`

### **vLLM Arguments**

```yaml
args:
  - --max-model-len=4096
  - --limit-mm-per-prompt={"image":1}
```

**Critical formatting rules:**
- ✅ Use `=` between flag and value
- ✅ No spaces in JSON: `{"image":1}` not `{"image": 1}`
- ✅ No quotes around arguments
- ❌ Wrong: `--limit-mm-per-prompt '{"image": 1}'`

### **GPU Resources**

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

---

## 🔄 **Updates and Modifications**

### **Update vLLM Arguments**

Edit the InferenceService:
```bash
oc edit inferenceservice stardew-vlm -n stardew-vision
```

Modify the `args:` section under `spec.predictor.model`, then save. The deployment will automatically restart.

### **Scale Replicas**

```bash
# Edit InferenceService
oc edit inferenceservice stardew-vlm -n stardew-vision

# Modify spec.predictor.minReplicas and maxReplicas
```

### **Update Model Version**

Edit `00-huggingface-connection.yaml` to point to a different model:
```yaml
stringData:
  URI: hf://Qwen/Qwen2.5-VL-14B-Instruct  # Example
```

Then:
```bash
oc apply -f 00-huggingface-connection.yaml
oc delete inferenceservice stardew-vlm -n stardew-vision
oc apply -f 03-inferenceservice.yaml
```

---

## ⚡ **Optional: Model Caching PVC**

To avoid re-downloading the model on every restart:

```bash
oc apply -f 04-model-cache-pvc.yaml
```

Then edit `03-inferenceservice.yaml` to add:

```yaml
spec:
  predictor:
    volumes:
      - name: model-cache
        persistentVolumeClaim:
          claimName: vllm-model-cache
    model:
      volumeMounts:
        - name: model-cache
          mountPath: /mnt/models
```

**Benefit:** Restarts go from ~3.5 min to ~30 seconds.

---

## 🐛 **Troubleshooting**

### **Pod Stuck in Pending**

```bash
oc describe pod -n stardew-vision -l serving.kserve.io/inferenceservice=stardew-vlm
```

**Common causes:**
- GPU node not ready (wait for autoscaler, or manually scale MachineSet)
- Missing GPU resources in InferenceService spec
- Missing GPU tolerations

### **Pod on CPU Node (vLLM Fails with "Failed to infer device type")**

Check if GPU resources are requested:
```bash
oc get pod -n stardew-vision -l serving.kserve.io/inferenceservice=stardew-vlm \
  -o jsonpath='{.items[0].spec.containers[*].resources}'
```

**Expected:** `nvidia.com/gpu: "1"` in both requests and limits.

**Fix:** Delete and redeploy InferenceService with correct GPU configuration.

### **Download Stuck or Slow**

Check init container logs:
```bash
oc logs -n stardew-vision \
  -l serving.kserve.io/inferenceservice=stardew-vlm \
  -c storage-initializer -f
```

**Speed up with HuggingFace token:**
```bash
# Create secret with HF token
oc create secret generic huggingface-token \
  --from-literal=token=hf_your_token_here \
  -n stardew-vision

# Add to InferenceService env (edit 03-inferenceservice.yaml):
env:
  - name: HF_TOKEN
    valueFrom:
      secretKeyRef:
        name: huggingface-token
        key: token
```

### **vLLM Argument Parsing Error**

If logs show:
```
api_server.py: error: unrecognized arguments: --limit-mm-per-prompt '{"image": 1}'
```

**Fix:** Use correct format in `args:` (no quotes, no spaces in JSON):
```yaml
args:
  - --max-model-len=4096
  - --limit-mm-per-prompt={"image":1}
```

---

## 🗑️ **Cleanup**

Delete all vLLM resources:

```bash
# Delete InferenceService (stops serving)
oc delete inferenceservice stardew-vlm -n stardew-vision

# Delete ServingRuntime
oc delete servingruntime stardew-vlm -n stardew-vision

# Delete connection
oc delete secret huggingface-qwen -n stardew-vision

# Delete cache PVC (optional - frees storage)
oc delete pvc vllm-model-cache -n stardew-vision
```

---

## 📚 **References**

- [Red Hat OpenShift AI 3.2 Documentation](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.2)
- [How to deploy language models with Red Hat OpenShift AI](https://developers.redhat.com/articles/2025/09/10/how-deploy-language-models-red-hat-openshift-ai)
- [vLLM Documentation](https://docs.vllm.ai/)
- [Qwen2.5-VL-7B-Instruct Model Card](https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct)

---

## ✅ **Success Criteria**

Deployment is successful when:

1. ✅ `oc get inferenceservice stardew-vlm` shows `READY=True`
2. ✅ Pod status: `1/1 Running`
3. ✅ Service exists: `stardew-vlm-predictor` with endpoint `8080/TCP`
4. ✅ `/v1/models` endpoint returns model list
5. ✅ Chat completion request returns valid response
6. ✅ Other pods in namespace can reach `http://stardew-vlm-predictor:8080/v1`

---

**Total deployment time (first run):** ~25-35 minutes  
**Subsequent restarts (no cache):** ~8-10 minutes  
**Subsequent restarts (with PVC cache):** ~30 seconds

**Ready to deploy!** 🚀
