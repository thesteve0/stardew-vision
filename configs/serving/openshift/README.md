# Canonical OpenShift deployment

**Always deploy the fine-tuned stack.** The verified configuration is private HF
LoRA → vLLM → fine-tuned coordinator → unified OCR → Kokoro TTS. There is no
base-mode, standalone Pierre, EFS, or ODF/S3 deployment alternative here.

## Deploy

Run from the repository root with `oc` authenticated to the intended cluster:

```bash
./deploy/deploy-to-openshift.sh
```

This delegates to `configs/serving/openshift/deploy.sh`, the sole production
entrypoint. It applies explicit files in dependency order, waits for both downloads
before inference, verifies mounted artifact identities and the LoRA served ID,
and creates the **`stardew-vision` Route targeting `coordinator-finetuned`**.
Do not apply directories recursively or bypass the download verification waits.

The current original application URL is:
https://stardew-vision-stardew-vision.apps.pytorch-conf.sandbox5282.opentlc.com/
On another cluster, use the `stardew-vision` Route's generated host.

## Prerequisites

- OpenShift AI/KServe RawDeployment CRDs and registry access to the pinned runtime.
- NVIDIA GPU Operator and a Ready GPU with capacity for Qwen2.5-VL-7B.
- `gp3-csi` EBS storage; all claims are RWO, all deployments have one replica.
- Private Hugging Face repo access via Secret `huggingface-adapter`, key `token`.
- Host tools `oc`, `python3`, and `curl`; network access for model downloads.

For a fresh namespace, create the Secret securely in an interactive Bash shell:

```bash
oc apply -f configs/serving/openshift/00-namespace.yaml
set +x
IFS= read -r -s -p 'HF read token: ' HF_ADAPTER_TOKEN
printf '\n' >&2
printf '%s' "$HF_ADAPTER_TOKEN" | oc create secret generic huggingface-adapter \
  -n stardew-vision --from-file=token=/dev/stdin
unset HF_ADAPTER_TOKEN
./deploy/deploy-to-openshift.sh
```

Never print tokens, store generated Secret YAML, or commit credentials. Restrict
Secret RBAC and follow cluster encryption/rotation policies.

## Verified version contract

| Component | Version |
| --- | --- |
| Coordinator (fine-tuned entrypoint) | `ghcr.io/thesteve0/stardew-coordinator:v0.8.2`, digest pinned in YAML |
| Unified OCR, including Pierre confidence fix | `ghcr.io/thesteve0/stardew-ocr-tools:v0.3.5`, digest pinned in YAML |
| Kokoro TTS | `ghcr.io/thesteve0/stardew-tts-tool:v0.4.0`, digest pinned in YAML |
| Runtime | Red Hat vLLM `0.13.0`, digest pinned in YAML |
| Base model | `Qwen/Qwen2.5-VL-7B-Instruct` at `cc594898137f460bfe9f0759e9844b3ce807cfb5` |
| Adapter | `TheSteve0/stardew-vision-qwen-tool-select-v1` at `73cb70b1718e2a09af55d823701fcd26b3c6a333` |
| API model ID | `stardew-vlm-finetuned` (LoRA); **not** `qwen-base` |

Use committed digests and revisions. Do not rebuild or substitute `latest` as
part of a normal deployment. See [artifact details](vllm-finetuned/README.md).

## Scheduling and repeat deployments

The script reuses the existing predictor's node. On a fresh install it selects a
Ready node with an unallocated GPU and sets the **same hostname selector on both
Jobs and the predictor**. You may explicitly choose `GPU_NODE=<hostname>`;
conflicting placement with the running predictor is rejected. Review CPU/memory
capacity, taints and existing PVC node affinity before deployment. A GPU selector
alone does not guarantee that EBS storage binds in the correct availability zone.

When the predictor is Ready, reruns skip downloads, verify mounted files, and
reapply the same pinned configuration. Completed Jobs are reused; their pod specs
are not edited. A non-Ready existing predictor causes a stop, not writes into its
mounted model volumes. Failed Jobs require diagnosis before deliberate recreation.
Never refresh model/adapter files while inference is using them. Existing PVC
storage classes and access modes are immutable; do not delete data to bypass an
error. The script does not delete namespaces/PVCs or stop unrelated GPU consumers.
It refuses an existing legacy base coordinator/predictor rather than deploying a
mixed stack. Model upgrades require a separate reviewed migration.

## Manifest inventory

- `00-namespace.yaml`: application namespace.
- `02-configmap-chat-template.yaml`: exact tested `qwen-chat-template`.
- `02-pvc-paddlex-cache-ocr-tools.yaml`, `03-pvc-hf-cache.yaml`: CPU model caches.
- `05-pvc-errors-finetuned.yaml`: coordinator error screenshot storage.
- `20-deployment-tts-tool.yaml`: TTS service, startup probe and warmup.
- `31-deployment-coordinator-finetuned.yaml`: coordinator, service and primary Route.
- `40-deployment-ocr-tools.yaml`: unified OCR service, startup probe and warmup.
- `vllm-finetuned/01-pvc-lora-adapter.yaml`, `05-pvc-model-cache.yaml`: dedicated storage.
- `vllm-finetuned/06-job-download-model.yaml`, `07-job-download-adapter.yaml`: pinned downloads.
- `vllm-finetuned/02-servingruntime.yaml`, `03-inferenceservice.yaml`: LoRA inference.
- `vllm-finetuned/04-configmap-service-endpoints-finetuned.yaml`: discovery and `AGENT_MODE=finetuned`.

## Verification and diagnostics

The manifest contract regression tests guard the sole fine-tuned predictor,
primary route target, verified image versions, digest pins, adapter identity,
entrypoint, discovery and gp3 storage:

```bash
python3 -m unittest discover -s tests -p test_deployment_contract.py -v
```

These tests require PyYAML and do not access the cluster.

```bash
oc get pods,pvc,jobs,inferenceservice,route -n stardew-vision
oc logs deployment/coordinator-finetuned -n stardew-vision --tail=100
oc logs deployment/stardew-vlm-finetuned-predictor -n stardew-vision --tail=100
oc logs deployment/ocr-tools -n stardew-vision --tail=100
oc logs deployment/tts-tool -n stardew-vision --tail=100
HOST=$(oc get route stardew-vision -n stardew-vision -o jsonpath='{.spec.host}')
curl --fail "https://$HOST/health"
curl --fail --max-time 180 -F file=@tests/fixtures/pierre_shop_001.png \
  "https://$HOST/analyze" -o /tmp/stardew-pierre.wav
```

The October 8, 2026 deployed smoke tests selected the correct Pierre/TV/fish tools
and rejected an unsupported screen; all returned HTTP 200 WAV audio. The Pierre
background digit was absent; Carp narration included 23 inches. These four samples
are **not** a full accuracy evaluation. For Pending pods, inspect events, node
resources and PVC topology; do not remove finalizers or force-delete storage.
