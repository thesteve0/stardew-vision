# 🚀 First Thing Tomorrow: OpenShift AI Deployment

**Status**: Ready to deploy to OpenShift AI with NVIDIA L40s GPU nodes

---

## ☕ Quick Start (30 minutes to first deployment)

### Pre-flight Checklist

Before starting, verify:

```bash
# 1. Cluster access (from devcontainer or host)
oc whoami
oc cluster-info

# 2. GPU nodes available
oc get nodes -l nvidia.com/gpu.present=true

# Expected: At least 1 node with STATUS=Ready

# 3. ODF installed
oc get storageclasses | grep noobaa

# Expected: openshift-storage.noobaa.io storage class exists
```

✅ If all three checks pass, you're ready to deploy.

---

## 🏗️ Deployment Workflow

### Step 1: Build Container Images (15 minutes)

⚠️ **Run on HOST machine** (exit devcontainer first)

```bash
# Exit devcontainer in VS Code:
# Command Palette (Ctrl+Shift+P) → "Dev Containers: Reopen Folder Locally"

# Navigate to repo
cd /path/to/stardew-vision

# Build all images
./deploy/build-images.sh v0.1.0
```

**Expected output**: 3 images built (coordinator, ocr-tool, tts-tool)

### Step 2: Push to GitHub Container Registry (5 minutes)

```bash
# Login to GHCR
docker login ghcr.io
# Username: thesteve0
# Password: <GitHub Personal Access Token with write:packages scope>

# Push all images
docker push ghcr.io/thesteve0/stardew-coordinator:v0.1.0
docker push ghcr.io/thesteve0/stardew-ocr-tool:v0.1.0
docker push ghcr.io/thesteve0/stardew-tts-tool:v0.1.0
docker push ghcr.io/thesteve0/stardew-coordinator:latest
docker push ghcr.io/thesteve0/stardew-ocr-tool:latest
docker push ghcr.io/thesteve0/stardew-tts-tool:latest
```

### Step 3: Make Packages Public (2 minutes)

🔗 **Go to**: https://github.com/thesteve0?tab=packages

For each package (stardew-coordinator, stardew-ocr-tool, stardew-tts-tool):
1. Click package name
2. Click "Package settings" (right sidebar)
3. Scroll to "Danger Zone"
4. Click "Change visibility" → "Public" → Confirm

### Step 4: Run Automated Deployment (60-90 minutes)

```bash
# Can run from devcontainer or host (needs oc/kubectl CLI)
./deploy/deploy-to-openshift.sh
```

**The script will**:
1. Create namespace, ConfigMaps, PVCs, ObjectBucketClaim (~2 min)
2. Extract ODF S3 credentials and display them
3. **PAUSE** for you to upload model to ODF (~15-20 min)
4. Deploy vLLM serving via KServe (~5-10 min wait)
5. Deploy microservices (coordinator, OCR, TTS) (~3 min)
6. Display external HTTPS URL

---

## 📦 Model Upload (During Step 4 Pause)

When the script pauses, open a new terminal and run:

```bash
# Install s3cmd if needed
pip install s3cmd

# Configure s3cmd (credentials displayed by deployment script)
cat > ~/.s3cfg << EOF
[default]
access_key = <AWS_ACCESS_KEY_ID from script>
secret_key = <AWS_SECRET_ACCESS_KEY from script>
host_base = <BUCKET_HOST from script>
host_bucket = <BUCKET_HOST from script>
use_https = True
EOF

# Download Qwen2.5-VL-7B-Instruct
python -c "
from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
model = Qwen2VLForConditionalGeneration.from_pretrained('Qwen/Qwen2.5-VL-7B-Instruct', torch_dtype='float16')
processor = AutoProcessor.from_pretrained('Qwen/Qwen2.5-VL-7B-Instruct')
model.save_pretrained('./qwen-upload')
processor.save_pretrained('./qwen-upload')
"

# Upload to ODF (use BUCKET_NAME from script output)
s3cmd put -r qwen-upload/ s3://<BUCKET_NAME>/models/qwen2.5-vl-7b/

# Verify
s3cmd ls s3://<BUCKET_NAME>/models/qwen2.5-vl-7b/
```

Expected: ~15GB of files (config.json, model*.safetensors, etc.)

Once verified, return to deployment script terminal and press ENTER.

---

## ✅ Verification

After deployment completes:

```bash
# 1. Check all pods running
oc get pods -n stardew-vision

# Expected:
# coordinator-xxx     1/1  Running
# coordinator-xxx     1/1  Running  
# coordinator-xxx     1/1  Running
# ocr-tool-xxx        1/1  Running
# ocr-tool-xxx        1/1  Running
# tts-tool-xxx        1/1  Running
# tts-tool-xxx        1/1  Running
# vllm-qwen-xxx       2/2  Running

# 2. Get external URL
EXTERNAL_URL=$(oc get route stardew-vision -n stardew-vision -o jsonpath='{.spec.host}')
echo "Application: https://${EXTERNAL_URL}"

# 3. Test in browser
open https://${EXTERNAL_URL}
# Upload tests/fixtures/pierre_shop_001.png
# Verify audio playback works
```

---

## 🐛 Quick Troubleshooting

### vLLM pod stuck in Pending
```bash
oc describe pod -n stardew-vision -l serving.kserve.io/inferenceservice=vllm-qwen
# Check: GPU node availability, resource requests
```

### OCR templates missing error
```bash
oc exec -n stardew-vision deployment/ocr-tool -- ls -la /app/datasets/assets/templates
# Should show: pierres_detail_panel_corner.png, etc.
```

### Coordinator can't reach vLLM
```bash
oc get svc -n stardew-vision | grep vllm
oc logs -n stardew-vision -l component=coordinator --tail=50
```

### View logs in real-time
```bash
# All components
oc logs -n stardew-vision -l app=stardew-vision --all-containers -f

# Specific component
oc logs -n stardew-vision -l component=coordinator -f
oc logs -n stardew-vision -l serving.kserve.io/inferenceservice=vllm-qwen -c kserve-container -f
```

---

## 📚 Reference Documentation

- **DEPLOYMENT.md** - Complete deployment guide with architecture
- **configs/serving/openshift/README.md** - Detailed manual deployment steps
- **configs/serving/openshift/00-BUILD-INSTRUCTIONS.md** - Container build guide
- **Plan**: `/home/stpousty-devcontainer/.claude/plans/tranquil-forging-barto.md`

---

## ⏱️ Time Estimates

| Phase | Time | Notes |
|-------|------|-------|
| Pre-flight checks | 5 min | Verify cluster access |
| Build images | 15 min | On host machine |
| Push images | 5 min | Requires GHCR login |
| Make packages public | 2 min | Via GitHub web UI |
| Deploy foundation | 5 min | Namespace, storage, ConfigMaps |
| Upload model to ODF | 15-20 min | Download + upload ~15GB |
| Deploy vLLM | 5-10 min | Model loading, GPU allocation |
| Deploy microservices | 3 min | OCR, TTS, coordinator |
| Verification | 5 min | Test upload + playback |
| **Total** | **60-75 min** | Assuming no issues |

---

## 🎯 Success Criteria

✅ Deployment is successful when:

1. All 8 pods show `Running` status
2. InferenceService shows `READY=True`
3. External URL is accessible via HTTPS
4. Pierre's shop screenshot upload returns audio
5. Audio narration is accurate and plays correctly

---

## 🆘 If Stuck

1. Check pod logs: `oc logs -n stardew-vision <pod-name>`
2. Check events: `oc get events -n stardew-vision --sort-by='.lastTimestamp'`
3. Review detailed docs: `cat configs/serving/openshift/README.md`
4. Start over: `oc delete namespace stardew-vision` (then re-run deployment)

---

## 📝 Notes

- **Local MVP is working**: Full agent loop tested with vLLM + FastAPI locally
- **GPU difference**: Local uses AMD ROCm, OpenShift uses NVIDIA L40s (different vLLM images)
- **All images reference**: `ghcr.io/thesteve0/...` (lowercase username)
- **Storage**: Uses OpenShift Data Foundation (ODF) for model weights

---

**Good luck! 🚀**

When deployment completes, you'll have a production-ready, GPU-accelerated Stardew Vision deployment on OpenShift AI with:
- Auto-scaling vLLM serving (1-2 replicas)
- Highly available coordinator (3 replicas)
- HTTPS external access
- Persistent error logging
- Full agent loop with tool calling

The local demo will still work for conference talks, and you'll have a production OpenShift deployment for real-world testing.
