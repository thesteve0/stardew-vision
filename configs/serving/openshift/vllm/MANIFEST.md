# Base vLLM manifest inventory

Apply explicit files in dependency order, preferably through `deploy.sh`.
Do not apply this directory wholesale: alternative runtimes share resource names.

| File | Role in the base flow |
| --- | --- |
| `../00-namespace.yaml` | Creates `stardew-vision` |
| `04-configmap-chat-template.yaml` | Required `qwen-chat-template` ConfigMap |
| `05-pvc-model-cache.yaml` | Required `vllm-model-cache`: 50Gi, gp3-csi, ReadWriteOnce |
| `06-job-download-model.yaml` | GPU-node download Job; wait for completion before serving |
| `02-servingruntime-with-template.yaml` | Required `stardew-vlm` runtime with chat-template mount and digest-pinned vLLM image |
| `03-inferenceservice.yaml` | Single-replica GPU predictor, consuming `pvc://vllm-model-cache` |
| `deploy.sh` | Noninteractive prerequisite/download/runtime/service sequence |
| `00-huggingface-connection.yaml` | Legacy direct-download connection; not required |
| `01-gpu-hardwareprofile.yaml` | Administrator-managed dashboard profile in `redhat-ods-applications`; not a substitute for GPU resources |
| `02-vllm-servingruntime.yaml` | Compatibility runtime now includes the template mount; defines the same resource, so do not apply both |

## Deployment contract

The download Job populates Qwen2.5-VL-7B-Instruct revision
`cc594898137f460bfe9f0759e9844b3ce807cfb5` at `/mnt/models`. Scheduling the
Job on a GPU node ensures delayed PVC binding uses GPU-compatible topology.
Only after Job success should the template-enabled runtime and InferenceService
be applied.

- API: `http://stardew-vlm-predictor:8080/v1`; model ID: `stardew-vlm`.
- Predictor: one NVIDIA GPU, 4–8 CPUs, 24–32Gi RAM, one replica.
- Context: 8192 tokens; one image per prompt; Hermes tool-call parser.
- The parent application uses digest-pinned coordinator v0.8.2 in both modes,
  unified OCR v0.3.5, and TTS v0.4.0.

## Blocked alternatives

The base cache is RWO, not EFS/RWX. Predictors on different GPU nodes cannot
share it concurrently; use separate model caches or suitable RWX storage.
Fine-tuned serving remains blocked until the intended adapter's provenance and
its missing EFS storage are resolved. Both coordinators require separate error
PVCs. Do not apply fine-tuned resources as part of the base deployment.

See [README.md](README.md) for deployment and verification, and the
[parent guide](../README.md) for CPU services and routes.
