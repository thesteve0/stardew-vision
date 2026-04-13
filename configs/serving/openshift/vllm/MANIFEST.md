# vLLM Deployment Manifest

Complete set of YAML files for deploying vLLM with KServe on OpenShift AI.

---

## 📁 **Files Overview**

| File | Purpose | Namespace | Required |
|------|---------|-----------|----------|
| `00-huggingface-connection.yaml` | HuggingFace model URI connection | `stardew-vision` | ✅ Yes |
| `01-gpu-hardwareprofile.yaml` | GPU hardware profile for RHOAI | `redhat-ods-applications` | ✅ Yes |
| `02-vllm-servingruntime.yaml` | vLLM runtime configuration | `stardew-vision` | ✅ Yes |
| `03-inferenceservice.yaml` | Main vLLM deployment | `stardew-vision` | ✅ Yes |
| `04-model-cache-pvc.yaml` | Model cache storage (optional) | `stardew-vision` | ⚪ Optional |
| `deploy.sh` | Automated deployment script | - | ⚪ Helper |
| `README.md` | Complete deployment documentation | - | 📖 Docs |

---

## 🚀 **Quick Deployment**

### **Option 1: Automated Script**

```bash
cd configs/serving/openshift/vllm
./deploy.sh
```

### **Option 2: Manual Steps**

```bash
# 1. GPU HardwareProfile (if not exists)
oc apply -f 01-gpu-hardwareprofile.yaml

# 2. HuggingFace connection
oc apply -f 00-huggingface-connection.yaml

# 3. ServingRuntime
oc apply -f 02-vllm-servingruntime.yaml

# 4. InferenceService
oc apply -f 03-inferenceservice.yaml

# 5. Optional: Model cache
oc apply -f 04-model-cache-pvc.yaml
```

### **Option 3: All at Once**

```bash
cd configs/serving/openshift/vllm
oc apply -f 01-gpu-hardwareprofile.yaml
oc apply -f 00-huggingface-connection.yaml
oc apply -f 02-vllm-servingruntime.yaml
oc apply -f 03-inferenceservice.yaml
```

---

## 📊 **Resource Dependencies**

```
01-gpu-hardwareprofile.yaml (cluster-level)
         ↓
00-huggingface-connection.yaml
         ↓
02-vllm-servingruntime.yaml
         ↓
03-inferenceservice.yaml ← references runtime and connection
```

---

## ⚙️ **Configuration Summary**

### **Model**
- **HuggingFace Model**: `Qwen/Qwen2.5-VL-7B-Instruct`
- **Model ID (API)**: `stardew-vlm` (deployment name)
- **Size**: ~14GB
- **Download time**: ~3.5 minutes

### **Endpoints**
- **Internal Service**: `stardew-vlm-predictor:8080`
- **API Path**: `/v1` (OpenAI-compatible)
- **Full DNS**: `http://stardew-vlm-predictor.stardew-vision.svc.cluster.local:8080/v1`

### **GPU Resources**
- **GPU Type**: NVIDIA L40S (or compatible)
- **GPU Count**: 1
- **CPU**: 4-8 cores
- **Memory**: 24-32 GiB

### **vLLM Arguments**
```yaml
- --max-model-len=4096
- --limit-mm-per-prompt={"image":1}
```

---

## 🔄 **Version Control**

These YAML files are version-controlled and can be:
- ✅ Committed to Git
- ✅ Applied via CI/CD pipelines
- ✅ Modified for different environments (dev/staging/prod)
- ✅ Reviewed in pull requests

---

## 📝 **Customization Guide**

### **Change Model**

Edit `00-huggingface-connection.yaml`:
```yaml
stringData:
  URI: hf://Qwen/Qwen2.5-VL-14B-Instruct  # Different model
```

### **Adjust GPU Resources**

Edit `03-inferenceservice.yaml`:
```yaml
resources:
  requests:
    nvidia.com/gpu: "2"  # Use 2 GPUs
```

### **Add Model Caching**

1. Apply PVC:
   ```bash
   oc apply -f 04-model-cache-pvc.yaml
   ```

2. Edit `03-inferenceservice.yaml` to mount the volume (see README.md)

### **Change vLLM Arguments**

Edit `03-inferenceservice.yaml`:
```yaml
args:
  - --max-model-len=8192  # Increase context window
  - --limit-mm-per-prompt={"image":2}  # Allow 2 images
```

---

## 🧪 **Testing**

After deployment, verify with:

```bash
# Check InferenceService
oc get inferenceservice stardew-vlm -n stardew-vision

# Check Service
oc get svc stardew-vlm-predictor -n stardew-vision

# Test endpoint
POD=$(oc get pods -n stardew-vision -l serving.kserve.io/inferenceservice=stardew-vlm -o jsonpath='{.items[0].metadata.name}')
oc exec -n stardew-vision $POD -- curl http://localhost:8080/v1/models
```

---

## 🗑️ **Cleanup**

Delete all resources:

```bash
cd configs/serving/openshift/vllm
oc delete -f 03-inferenceservice.yaml
oc delete -f 02-vllm-servingruntime.yaml
oc delete -f 00-huggingface-connection.yaml
oc delete -f 04-model-cache-pvc.yaml  # If created
```

**Note:** GPU HardwareProfile in `redhat-ods-applications` is cluster-scoped - delete separately if needed.

---

## 📚 **Documentation**

See `README.md` for:
- Detailed deployment instructions
- Troubleshooting guide
- Configuration reference
- Best practices

---

**Last Updated**: 2026-04-12  
**Compatible with**: OpenShift AI 3.2+, KServe, vLLM 0.13+
