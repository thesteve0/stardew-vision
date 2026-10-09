# Fine-tuned Qwen serving: pinned Hugging Face adapter

This flow downloads the private [TheSteve0/stardew-vision-qwen-tool-select-v1
snapshot](https://huggingface.co/TheSteve0/stardew-vision-qwen-tool-select-v1/tree/73cb70b1718e2a09af55d823701fcd26b3c6a333)
at revision **`73cb70b1718e2a09af55d823701fcd26b3c6a333`**. It serves the local
v1 adapter artifact, not a claim that the historical EFS artifact was recovered.
Byte identity between local v1/Hugging Face and the old EFS adapter is **unproven**.
Historical evaluation results do not establish quality for this exact deployed
snapshot: artifact identity, evaluation dataset/split, prompts, tool schemas,
and serving settings must be matched before transferring those results. Download
hash checks establish byte identity only, not accuracy, end-to-end narration
quality, or equivalence to any historical evaluation. Run fresh evaluation.

## Requirements and storage

Use the parent guide's namespace, OpenShift AI/KServe, GPU, registry and network
prerequisites. A Hugging Face read token must have access to the private repo.
No token or Secret object is committed. `huggingface-adapter` is used only by the
adapter Job, not the inference runtime. The public pinned base download needs no
adapter token.

- `lora-adapter`: **20Gi gp3-csi RWO**, populated under `model-output/`.
- `vllm-model-cache-finetuned`: **50Gi gp3-csi RWO**, independent of the base
  predictor's `vllm-model-cache`. `storageUri` uses this fine-tuned cache.
- Both Jobs select GPU nodes and tolerate the GPU taint but do not reserve a GPU.
  With `WaitForFirstConsumer`, the base download Job mounts **both claims** to
  bind them together in a GPU node's zone. Run it first. A GPU selector alone on
  independent Jobs would not guarantee a shared availability zone.
- RWO volumes can move between nodes in their bound zone after detachment, not
  across zones. Keep the predictor at one replica. For optional same-node
  placement, add the **same** `kubernetes.io/hostname` selector to both Job pod
  specs and `03-inferenceservice.yaml`'s predictor before applying. Do this only
  for a ready GPU node with capacity and compatible existing PVC node affinity.
  Do not pin one Job alone or assume a selector repairs an already bound volume.
- For existing historical `lora-adapter` PVCs, the storage class/access mode is
  immutable. Stop all consumers, preserve any historical data needed, and have
  an administrator review a migration/recreation plan before applying. Do not
  blindly delete PVCs: that may destroy data. Check existing claim topology too.

## Explicit apply order

These are operator instructions, not a deployment performed by this change.
Run from the repo root. **Never apply this directory wholesale or recursively**;
`obsolete/` contains the old EFS PV for reference only.

First create the namespace (`configs/serving/openshift/00-namespace.yaml`). If
an approved `huggingface-adapter` Secret already exists, skip Secret creation.
Otherwise use an interactive Bash session, without tracing, to send the token
through stdin (not a command argument, literal in history, manifest, or file):

```bash
set +x
IFS= read -r -s -p 'HF read token: ' HF_ADAPTER_TOKEN
printf '\n' >&2
printf '%s' "$HF_ADAPTER_TOKEN" | oc create secret generic huggingface-adapter \
  -n stardew-vision --from-file=token=/dev/stdin
unset HF_ADAPTER_TOKEN
```

Do not echo the token, save generated Secret YAML, enable shell tracing, or
commit/upload credentials. Limit Secret RBAC; follow cluster encryption and
rotation policy. Review the following manifests before applying:

```bash
# Shared chat template; no base predictor or base cache is required.
oc apply -f configs/serving/openshift/vllm/04-configmap-chat-template.yaml
# 1. Create both dedicated claims.
oc apply -f configs/serving/openshift/vllm-finetuned/01-pvc-lora-adapter.yaml
oc apply -f configs/serving/openshift/vllm-finetuned/05-pvc-model-cache.yaml
# 2. Download base revision cc594898137f460bfe9f0759e9844b3ce807cfb5;
#    mounting both claims binds them in the same GPU zone.
oc apply -f configs/serving/openshift/vllm-finetuned/06-job-download-model.yaml
oc wait --for=condition=complete job/download-qwen-model-finetuned \
  -n stardew-vision --timeout=60m
oc logs job/download-qwen-model-finetuned -n stardew-vision
# 3. Download and verify the private adapter; wait before starting inference.
oc apply -f configs/serving/openshift/vllm-finetuned/07-job-download-adapter.yaml
oc wait --for=condition=complete job/download-lora-adapter \
  -n stardew-vision --timeout=30m
oc logs job/download-lora-adapter -n stardew-vision
# 4. Only after BOTH Jobs succeed, start the runtime/service.
oc apply -f configs/serving/openshift/vllm-finetuned/02-servingruntime.yaml
oc apply -f configs/serving/openshift/vllm-finetuned/03-inferenceservice.yaml
oc wait --for=condition=Ready inferenceservice/stardew-vlm-finetuned \
  -n stardew-vision --timeout=20m
# 5. Set discovery before starting the separate fine-tuned coordinator.
oc apply -f configs/serving/openshift/vllm-finetuned/04-configmap-service-endpoints-finetuned.yaml
```

Stop on any failure; inspect Job logs and pod/PVC events instead of bypassing a
wait. Existing completed Jobs do not rerun on apply. Jobs expire after 24 hours;
review existing downloads before intentionally recreating Jobs. Never download
or refresh files while a predictor is using them. The base Job temporarily
attaches the adapter claim too; wait for its pod to release volumes before the
adapter Job starts if CSI reports multi-attach errors.

The adapter Job installs `huggingface_hub==0.36.0` into writable
`/tmp/hf-packages` with the same pinned Python image digest as the base Job. It
requests only `adapter_config.json` and `adapter_model.safetensors` (HF may also
write local download metadata), writes them under
`/mnt/lora-adapter/model-output`, and fails unless **both** SHA256 values match:

| File | SHA256 |
| --- | --- |
| `adapter_model.safetensors` | `373c475669049191527b3d8e8a330f347f236855482bb2282f9604177a915a63` |
| `adapter_config.json` | `449c057c21c46e3bc0d32d4d7a3590112927c756ae4a7e0ec6326cdc91e2e478` |

The runtime mounts the adapter read-only at `/mnt/lora-adapter/model-output`.
`qwen-base` is the base model's served ID; **`stardew-vlm-finetuned`** is the LoRA
module/API ID (`{{.Name}}` resolves to the InferenceService name). Send fine-tuned
requests to the latter, not `qwen-base` or the HF repository name. Verify
`/v1/models` at `http://stardew-vlm-finetuned-predictor:8080/v1` and inspect runtime
logs before application use.

For the full application, use the parent guide's common OCR/TTS services and
apply `05-pvc-errors-finetuned.yaml` before
`31-deployment-coordinator-finetuned.yaml`. The fine-tuned coordinator needs its
own error PVC; do not share the base coordinator's RWO error volume. GPU capacity
for both predictors and CPU-service RWO cache topology remain operator concerns.
