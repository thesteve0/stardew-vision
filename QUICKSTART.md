# Stardew Vision Quick Start

The current verified application is the **fine-tuned OpenShift deployment**, not
the old base-model/stub-TTS local demo. The single source of deployment details is
the [OpenShift guide](configs/serving/openshift/README.md).

## Current Verified OpenShift Deployment

The canonical deployment is **fine-tuned Qwen2.5-VL-7B-Instruct**, served by
**vLLM 0.13** through KServe. Tool schemas are baked into the classification
system prompt to match training; the coordinator parses `<tool_call>` output
rather than sending an OpenAI `tools=` schema. It dispatches OCR over HTTP, then
produces narration (a separate correction/narration model call for Pierre's shop
and TV; deterministic narration for caught fish) and calls Kokoro TTS directly.

```text
Original Route stardew-vision → coordinator-finetuned:8000 (1 replica)
  ├─ stardew-vlm-finetuned-predictor:8080/v1 (vLLM 0.13, 1 replica, GPU)
  ├─ ocr-tools:8004 (unified OCR, 1 replica, CPU)
  └─ tts-tool:8003 (Kokoro, 1 replica, CPU)
```

- Private Hugging Face LoRA adapter: `TheSteve0/stardew-vision-qwen-tool-select-v1`
  at revision **`73cb70b1718e2a09af55d823701fcd26b3c6a333`**. An operator-provided
  `huggingface-adapter` Secret with a `token` key must have access to this repo;
  never commit credentials.
- API/model ID: `stardew-vlm-finetuned` (not `qwen-base`).
- Digest-pinned application images in the manifests: coordinator **v0.8.2**,
  unified OCR **v0.3.5**, TTS **v0.4.0**. Use the committed digests, not `latest`.
- Model manifests: `configs/serving/openshift/vllm-finetuned/`; shared chat
  template: `configs/serving/openshift/02-configmap-chat-template.yaml`.
- `31-deployment-coordinator-finetuned.yaml` owns the sole primary Route
  `stardew-vision`, targeting `coordinator-finetuned`; no separate route-switch
  manifest or base-model deployment is needed.

From the repository root, after completing the prerequisites in the
[canonical OpenShift deployment guide](configs/serving/openshift/README.md):

```bash
./deploy/deploy-to-openshift.sh
```

This wrapper invokes `configs/serving/openshift/deploy.sh`. Follow that guide for
storage topology, download/hash verification, readiness checks, and migration.
Do not recursively apply the manifest directory. Hash verification establishes
artifact identity, not model quality; historical evaluation accuracy must not be
attributed to this pinned adapter without fresh evaluation.

## Verify and Use

After the deploy script's readiness checks succeed:

```bash
oc get pods -n stardew-vision
oc get route stardew-vision -n stardew-vision -o jsonpath='{.spec.host}'
```

Open `https://<route-host>` and upload a Pierre's shop, TV dialog, or caught-fish
screenshot. Classification selects a supported unified OCR tool, the coordinator
assembles narration, and Kokoro returns WAV audio. Unsupported screens receive a
fallback narration. TTS is not a model tool call.

For diagnostics, consult the [canonical guide](configs/serving/openshift/README.md),
including private adapter access, RWO storage topology, and download Job failures.
Do not replace the pinned adapter or runtime based on historical accuracy claims.

## Local Development and Design History

- [CLAUDE.md](CLAUDE.md): project context and local ROCm development constraints.
- [vLLM notes](docs/vllm-notes.md): local AMD/ROCm experiments, distinct from the
  production CUDA vLLM 0.13 runtime.
- [Architecture decisions](docs/adr/): historical rationale; superseded sections
  are not current deployment instructions.
- [Project plan](docs/plan.md): historical planning milestones.
- Training and evaluation live in
  [stardew-vision-training](https://github.com/thesteve0/stardew-vision-training).
