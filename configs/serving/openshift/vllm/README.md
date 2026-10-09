# Base Qwen serving on OpenShift AI

This flow serves `Qwen/Qwen2.5-VL-7B-Instruct` with KServe RawDeployment,
using a pre-populated PVC and the tool-calling chat template. It does not use
S3 or a Hugging Face connection secret.

## Prerequisites

Authenticate `oc` to the intended cluster. OpenShift AI/KServe, NVIDIA GPU
resources, registry access, Hugging Face download access, and the `gp3-csi`
storage class must be available. The predictor requests one GPU, 4 CPUs and
24Gi RAM (limits: 8 CPUs, 32Gi RAM). A GPU HardwareProfile can be configured
by an administrator for dashboard use; it does not replace the explicit GPU
resource requests and scheduling constraints in the InferenceService.

## Deploy

From the repository root:

```bash
configs/serving/openshift/vllm/deploy.sh
```

The script is noninteractive and applies prerequisites in this order:

1. Create `stardew-vision` using `../00-namespace.yaml`.
2. Apply `04-configmap-chat-template.yaml` (`qwen-chat-template`).
3. Apply `05-pvc-model-cache.yaml`: `vllm-model-cache`, **50Gi gp3-csi RWO**.
4. Apply `06-job-download-model.yaml`. The Job runs on a GPU node so that
   delayed volume binding places the cache where the predictor can run. It
   downloads revision **`cc594898137f460bfe9f0759e9844b3ce807cfb5`** into
   `/mnt/models`.
5. Wait for `download-qwen-model` to complete successfully.
6. Apply **`02-servingruntime-with-template.yaml`**, then
   `03-inferenceservice.yaml` (`stardew-vlm`). The compatibility runtime
   `02-vllm-servingruntime.yaml` now also mounts the template, but defines the
   same resource; apply only the canonical template-enabled variant.

Do not apply the whole directory or start the predictor before the download
finishes. A completed Job does not rerun merely because it is applied again;
for an intentional refresh, stop consumers and review/delete the old Job before
rerunning it. Do not overwrite a cache actively used by a predictor.

## Verify

```bash
oc logs job/download-qwen-model -n stardew-vision
oc wait --for=condition=Ready inferenceservice/stardew-vlm \
  -n stardew-vision --timeout=20m
oc get inferenceservice,pvc -n stardew-vision
oc logs -n stardew-vision \
  -l serving.kserve.io/inferenceservice=stardew-vlm \
  -c kserve-container --tail=100
oc port-forward -n stardew-vision svc/stardew-vlm-predictor 8080:8080
# In another terminal:
curl --fail http://localhost:8080/v1/models
```

The internal API is `http://stardew-vlm-predictor:8080/v1`, with model ID
`stardew-vlm` (not the Hugging Face repository name). The InferenceService uses
`pvc://vllm-model-cache`, an 8192-token context, one image per prompt, Hermes
tool-call parsing, and `/mnt/chat-template/chat_template.jinja`.

## Storage and fine-tuned limitations

The cache is required, not optional. With gp3-csi RWO, the bound volume's topology
and single-node attachment constrain scheduling. Keep the base predictor at one
replica; the same cache cannot serve base and fine-tuned predictors on different
GPU nodes concurrently. Use separate model caches or provision suitable RWX
storage before attempting that layout.

Fine-tuned serving now has a [dedicated download flow](../vllm-finetuned/README.md)
for the private [TheSteve0/stardew-vision-qwen-tool-select-v1 snapshot at revision
73cb70b1718e2a09af55d823701fcd26b3c6a333](https://huggingface.co/TheSteve0/stardew-vision-qwen-tool-select-v1/tree/73cb70b1718e2a09af55d823701fcd26b3c6a333).
It uses a separate 50Gi gp3-csi RWO base cache and a gp3-csi RWO adapter claim,
not the historical EFS binding. Follow its explicit apply order, secure stdin
Secret setup, GPU-zone/same-node guidance and waits for **both** download Jobs.
The adapter Job verifies pinned hashes before completion; inference mounts
`/mnt/lora-adapter/model-output`. Request the `stardew-vlm-finetuned` LoRA module,
not the distinct `qwen-base` model ID. Both coordinators need separate error PVCs.

The local v1/Hugging Face artifact has not been proven byte-identical to the
historical EFS artifact. Historical evaluation results are not proof of quality
for this pinned serving configuration; fresh evaluation is required. See the
[parent deployment guide](../README.md) for the application integration.

## Troubleshooting

- **Pending Job/predictor:** inspect pod and PVC events, GPU node readiness,
  tolerations, storage-class binding mode, and volume node affinity. A cache
  already bound on a CPU node is not repaired by changing the Job selector.
- **Download failure:** inspect Job logs and network/registry access. Job success
  is required before serving; do not bypass its wait after a failure.
- **Template or startup failure:** verify `qwen-chat-template` exists and the
  template-enabled ServingRuntime is applied, then inspect `kserve-container`
  logs. The model download is performed by the Job, not a serving init container.
- **Multi-attach error:** stop competing consumers or supply separate/RWX storage;
  do not try to solve it by increasing replicas.

To stop base serving, delete the `stardew-vlm` InferenceService. Retain the cache
for restarts; deleting the PVC can destroy the model download.
