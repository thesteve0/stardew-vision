# OpenShift deployment

Deploy the **base tool-calling** application with the explicit steps below. Run
commands from the repository root with `oc` authenticated to the intended cluster.
Do not apply this directory wholesale: it contains obsolete and alternative
manifests, including the historical fine-tuned EFS PV.

## Prerequisites

- OpenShift AI/KServe with RawDeployment support, NVIDIA GPU Operator, and a
  ready GPU node with sufficient memory for Qwen2.5-VL-7B-Instruct.
- `gp3-csi` storage for the 50Gi RWO model cache, and a working default storage
  class for the CPU services' cache/error PVCs.
- Access to the runtime registry, GHCR images, and Hugging Face for the download
  Job. The application manifests pin image digests: coordinator **v0.8.2** in
  both modes, unified OCR **v0.3.5**, and TTS **v0.4.0** (including init images).
  Use the committed digests, not mutable `latest` tags.

## Base deployment

```bash
# Namespace, CPU caches, error storage, and service discovery
oc apply -f configs/serving/openshift/00-namespace.yaml
oc apply -f configs/serving/openshift/02-pvc-paddlex-cache-ocr-tools.yaml
oc apply -f configs/serving/openshift/03-pvc-hf-cache.yaml
oc apply -f configs/serving/openshift/04-pvc-errors.yaml
oc apply -f configs/serving/openshift/06-configmap-service-endpoints.yaml

# Creates the chat template and model PVC, downloads the pinned model on a GPU
# node, waits for the Job, then applies the template-enabled runtime and service.
configs/serving/openshift/vllm/deploy.sh

# Unified OCR replaces the old Pierre-only deployment.
oc apply -f configs/serving/openshift/40-deployment-ocr-tools.yaml
oc apply -f configs/serving/openshift/20-deployment-tts-tool.yaml
oc apply -f configs/serving/openshift/30-deployment-coordinator.yaml

oc rollout status deployment/ocr-tools -n stardew-vision --timeout=15m
oc rollout status deployment/tts-tool -n stardew-vision --timeout=15m
oc rollout status deployment/coordinator -n stardew-vision --timeout=5m
oc wait --for=condition=Ready inferenceservice/stardew-vlm \
  -n stardew-vision --timeout=20m
oc get route stardew-vision -n stardew-vision
```

Use the route's HTTPS host for the application. `service-endpoints` points to
`ocr-tools:8004`, `tts-tool:8003`, and
`http://stardew-vlm-predictor:8080/v1`; the API model ID is `stardew-vlm`.
See [vLLM deployment](vllm/README.md) for model prerequisites and diagnostics.

Do **not** deploy `10-deployment-pierres-buying-tool.yaml`, the older PaddleX
cache manifest, or `obsolete/` for this flow. ODF/S3 upload and the legacy
Hugging Face connection are not required for PVC-based serving.

## Fine-tuned mode: pinned Hugging Face adapter

Follow the [explicit fine-tuned file order](vllm-finetuned/README.md), not a
recursive apply. The private adapter is
[TheSteve0/stardew-vision-qwen-tool-select-v1 at revision
73cb70b1718e2a09af55d823701fcd26b3c6a333](https://huggingface.co/TheSteve0/stardew-vision-qwen-tool-select-v1/tree/73cb70b1718e2a09af55d823701fcd26b3c6a333).
An operator-provided `huggingface-adapter` Secret (`token` key) is required; the
linked guide shows secure stdin creation without committing credentials.

The active adapter claim is gp3-csi RWO, not EFS. A separate **50Gi**
`vllm-model-cache-finetuned` avoids sharing the base predictor's cache. Apply both
claims, run the GPU-selected fine-tuned base download Job (which mounts both
claims to bind them in one GPU zone), wait for completion, then run and await
the hash-verifying adapter Job. Only then apply the fine-tuned runtime,
InferenceService and endpoint ConfigMap. Keep one predictor replica; optional
same-node pinning and migration of existing immutable EFS PVCs need the topology
review described in the guide.

The fine-tuned API/module ID is `stardew-vlm-finetuned`, distinct from `qwen-base`.
For the application, apply `05-pvc-errors-finetuned.yaml` before
`31-deployment-coordinator-finetuned.yaml` and reuse the common OCR/TTS services.
Both coordinators need separate error PVCs. Do not apply the archived EFS PV.

This serves the local v1/Hugging Face artifact. Its byte identity with the
historical EFS artifact is unproven; historical evaluation results cannot be
assumed to describe this pinned deployment. Hash verification is not quality
validation. Run fresh evaluation with the deployed prompts, tools and runtime.

## Diagnostics

```bash
oc get pods,pvc -n stardew-vision
oc logs deployment/ocr-tools -n stardew-vision --tail=100
oc logs deployment/tts-tool -n stardew-vision --tail=100
oc logs deployment/coordinator -n stardew-vision --tail=100
```

For Pending pods, inspect `oc describe pod` and PVC events for GPU scheduling,
volume topology, and multi-attach errors. RWO CPU caches also constrain placement;
do not increase replicas across nodes without reviewing storage access modes.
Deleting PVCs or the namespace can destroy downloaded models and error records.
