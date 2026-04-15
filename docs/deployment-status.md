# Deployment Status

**Date**: 2026-04-13
**Environment**: OpenShift AI (Production)
**Status**: ✅ Operational

## Current Deployment

### Overview
Full agent loop deployed and operational on OpenShift AI. Users can upload Pierre's shop screenshots and receive natural-language audio narration of item details.

### Services Status

| Service | Version | Status | Performance |
|---------|---------|--------|-------------|
| vLLM (KServe) | Qwen2.5-VL-7B-Instruct | ✅ Running | ~1s inference |
| OCR Tool | v0.12.0 | ✅ Running | ~2s per request (cached) |
| TTS Tool | v0.4.0 | ✅ Running | ~3s synthesis |
| Coordinator | v0.6.0 | ✅ Running | ~200 MiB memory |

### Performance Metrics

**First request after pod restart:**
- Total: ~35-40s (includes OCR model loading from disk to memory)
- Breakdown: VLM 1s + OCR 30s (loading) + TTS 3s

**Subsequent requests:**
- Total: ~5-7s (models cached in memory)
- Breakdown: VLM 1s + OCR 2s + TTS 3s

### Route Information

**Public URL**: `https://stardew-vision-stardew-vision.apps.<cluster-domain>`
**Timeout**: 3 minutes (sufficient for cold start + normal operation)

### Resource Usage

**Current allocation:**
- vLLM: 1 GPU, 32Gi memory, 8 CPU
- OCR: 4Gi memory request, 8Gi limit, 1000m-2500m CPU
- TTS: 1Gi memory request, 2Gi limit, 1000m-2000m CPU
- Coordinator: 512Mi memory request, 1Gi limit, 500m-1000m CPU

**Storage:**
- `paddlex-cache`: 2Gi PVC (PaddleOCR models, ~400MB used)
- `hf-cache`: 2Gi PVC (TTS models, ~500MB used)
- `error-screenshots`: 5Gi PVC (failed extractions, <100MB used)

### Monitoring

**Health endpoints:**
- vLLM: `http://stardew-vlm-predictor:8080/health`
- OCR: `http://pierres-buying-tool:8002/health`
- TTS: `http://tts-tool:8003/health`
- Coordinator: `http://coordinator:8000/health`

**Timing logs** (grep for ⏱️ emoji):
```bash
kubectl logs -n stardew-vision deployment/coordinator -f | grep "⏱️"
```

**Example timing output:**
```
⏱️  Starting agent loop: vLLM=http://stardew-vlm-predictor:8080/v1 model=stardew-vlm
⏱️  VLM response (1.16s): finish_reason=tool_calls has_tool_calls=True num_tool_calls=1
⏱️  Tool crop_pierres_detail_panel completed in 2.14s
⏱️  Turn 1 completed in 3.45s (continuing to next turn)
⏱️  VLM response (0.98s): finish_reason=stop has_tool_calls=False
⏱️  Turn 2 completed in 1.02s (loop ending, finish_reason=stop)
⏱️  TTS synthesis succeeded in 2.87s (45123 bytes)
⏱️  TOTAL agent loop completed in 7.34s
```

## Known Issues

### 1. Cold Start Performance
**Impact**: First request after OCR pod restart takes ~35s
**Cause**: PaddleOCR models load from disk into memory (~30s)
**Workaround**: Models cached after first request; subsequent requests are fast (~5-7s)
**Future**: Consider model preloading in main container entrypoint (not just init container)

### 2. MKLDNN Disabled for Portability
**Impact**: OCR performance 2-4x slower than optimal
**Cause**: PaddlePaddle MKLDNN optimizations incompatible with some OpenShift node CPUs
**Mitigation**: Disabled via `FLAGS_use_mkldnn=0` to prevent SIGTERM crashes
**Future**: Could enable MKLDNN with node selectors targeting AVX2-capable nodes

### 3. Zero-Shot Tool Calling
**Impact**: Qwen may not always call correct tool or format narration properly
**Cause**: Using base Qwen2.5-VL-7B without fine-tuning on Stardew-specific data
**Next Step**: Phase 2 fine-tuning (see below)

## Operational Procedures

### Restart a Service

**OCR Tool:**
```bash
kubectl rollout restart deployment/pierres-buying-tool -n stardew-vision
kubectl rollout status deployment/pierres-buying-tool -n stardew-vision
```

**Coordinator:**
```bash
kubectl rollout restart deployment/coordinator -n stardew-vision
kubectl rollout status deployment/coordinator -n stardew-vision
```

**vLLM (KServe):**
```bash
# Delete predictor pod to trigger rebuild
kubectl delete pod -n stardew-vision -l serving.kserve.io/inferenceservice=stardew-vlm
kubectl get pods -n stardew-vision -l serving.kserve.io/inferenceservice=stardew-vlm -w
```

### Update a Service

**OCR Tool:**
```bash
# Build and push new image
docker build -t ghcr.io/thesteve0/stardew-pierres-buying-tool:v0.XX.0 -f services/pierres-buying-tool/Dockerfile .
docker push ghcr.io/thesteve0/stardew-pierres-buying-tool:v0.XX.0

# Update deployment
kubectl set image deployment/pierres-buying-tool -n stardew-vision \
  ocr=ghcr.io/thesteve0/stardew-pierres-buying-tool:v0.XX.0 \
  download-paddlex-models=ghcr.io/thesteve0/stardew-pierres-buying-tool:v0.XX.0

# Monitor rollout
kubectl rollout status deployment/pierres-buying-tool -n stardew-vision
```

**Coordinator:**
```bash
# Build and push
docker build -t ghcr.io/thesteve0/stardew-coordinator:v0.X.0 -f services/coordinator/Dockerfile .
docker push ghcr.io/thesteve0/stardew-coordinator:v0.X.0

# Update deployment YAML and apply
# Edit configs/serving/openshift/30-deployment-coordinator.yaml
kubectl apply -f configs/serving/openshift/30-deployment-coordinator.yaml
```

### Check Error Screenshots

**List errors:**
```bash
kubectl exec -n stardew-vision deployment/coordinator -- ls -lh /app/datasets/errors/
```

**Download error for analysis:**
```bash
kubectl cp stardew-vision/<coordinator-pod-name>:/app/datasets/errors/<error-file>.png ./error.png
```

### View Comprehensive Logs

**All services:**
```bash
# Coordinator (agent loop timing)
kubectl logs -n stardew-vision deployment/coordinator -f

# OCR tool (model loading, extraction)
kubectl logs -n stardew-vision deployment/pierres-buying-tool -f

# TTS tool (synthesis)
kubectl logs -n stardew-vision deployment/tts-tool -f

# vLLM predictor (inference)
kubectl logs -n stardew-vision -l serving.kserve.io/inferenceservice=stardew-vlm -f
```

## Next Steps: Phase 2 Fine-Tuning

### Objectives
1. Improve screen classification accuracy (recognize Pierre's shop vs. unrecognized screens)
2. Improve tool calling reliability (always call correct extraction tool)
3. Improve narration quality (natural language, appropriate detail level)
4. Add support for additional screen types (TV dialog, inventory tooltip)

### Data Collection Plan

**Target**: 500-1000 annotated screenshots across multiple screen types

**Annotation format** (full conversation):
```json
{
  "image_id": "uuid",
  "screen_type": "pierres_shop_detail",
  "conversation": [
    {"role": "system", "content": "<system prompt>"},
    {"role": "user", "content": [{"type": "image_url", ...}, {"type": "text", ...}]},
    {"role": "assistant", "content": null, "tool_calls": [{"function": {"name": "crop_pierres_detail_panel", "arguments": "{}"}}]},
    {"role": "tool", "content": "{\"name\": \"Parsnip Seeds\", ...}"},
    {"role": "assistant", "content": "{\"narration\": \"The item is Parsnip Seeds...\", \"has_errors\": false}"}
  ]
}
```

**Screen types for Phase 2:**
- Pierre's shop detail panel (current): 300 examples
- Unrecognized screens (fallback behavior): 100 examples
- TV dialog (Phase 2 target): 100 examples
- Inventory tooltip (Phase 3): 100 examples

### Fine-Tuning Approach

**Model**: Qwen2.5-VL-7B-Instruct with LoRA (PEFT)
**Method**: SFTTrainer (TRL) or custom training loop
**Precision**: FP16 (ROCm 7.2 constraint)
**Hardware**: Local AMD Strix Halo for training, then deploy adapter to OpenShift

**Evaluation metrics:**
- Screen classification accuracy: % of screenshots where correct tool is called on turn 1
- Tool calling accuracy: % of turns where tool call format is valid
- Narration quality: Human eval on naturalness and accuracy
- JSON validity rate: % of final responses that parse as valid JSON

### Deployment of Fine-Tuned Model

**Option 1: LoRA adapter** (preferred for MVP)
- Upload LoRA adapter weights to HuggingFace
- Update vLLM `storageUri` to point to adapter
- vLLM loads base model + adapter at startup

**Option 2: Merged model**
- Merge LoRA adapter into base model weights
- Upload merged model to HuggingFace
- Update vLLM `storageUri` to point to merged model

## References

- [ADR-012: OpenShift Deployment Architecture](adr/012-openshift-deployment-architecture.md)
- [LESSONS_LEARNED.md](../LESSONS_LEARNED.md): Troubleshooting guide
- [CLAUDE.md](../CLAUDE.md): Development environment and architecture overview
- [plan.md](plan.md): Overall project plan and phases
