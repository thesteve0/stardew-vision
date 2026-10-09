# Pinned fine-tuned model artifacts

This is the **only production model** for Stardew Vision. Deploy the complete
stack using `./deploy/deploy-to-openshift.sh`; follow the
[parent deployment guide](../README.md) for authentication, ordering, storage,
route and diagnostics. Do not deploy this directory independently or recursively.

## Identity and provenance

Private adapter repository:
[TheSteve0/stardew-vision-qwen-tool-select-v1](https://huggingface.co/TheSteve0/stardew-vision-qwen-tool-select-v1/tree/73cb70b1718e2a09af55d823701fcd26b3c6a333)

- Adapter revision: `73cb70b1718e2a09af55d823701fcd26b3c6a333`.
- Base: `Qwen/Qwen2.5-VL-7B-Instruct`, serving revision
  `cc594898137f460bfe9f0759e9844b3ce807cfb5`.
- Rank 16 LoRA, served as **`stardew-vlm-finetuned`**; base ID `qwen-base`.
- Adapter Job downloads only config/weights and fails unless both hashes match.
- Secret `huggingface-adapter/token` is used only by the download Job.
- Adapter is mounted read-only by inference; no HF token is passed to the runtime.

| File | SHA256 |
| --- | --- |
| `adapter_model.safetensors` | `373c475669049191527b3d8e8a330f347f236855482bb2282f9604177a915a63` |
| `adapter_config.json` | `449c057c21c46e3bc0d32d4d7a3590112927c756ae4a7e0ec6326cdc91e2e478` |

The published adapter is recovered **local v1**, matching local checkpoint 200.
Its identity with the historical EFS adapter remains unproven. The observed
training checkout is not established as the training-run commit, and the original
training base revision was not pinned. Historical evaluation accuracy does not
transfer automatically to this exact deployment. Hash checks establish identity,
not quality. Current deployed Pierre/TV/fish/rejection smoke tests pass; run a
fresh full evaluation before claiming accuracy.

## Runtime contract

The runtime uses pinned Red Hat vLLM 0.13.0, context 8192, max sequences 1,
one image per prompt, prefix caching, GPU utilization 0.95, one GPU replica,
Hermes parser and the shared `qwen-chat-template` ConfigMap. The fine-tuned
coordinator uses baked-in tool schemas without OpenAI `tools` injection, dispatches
TV/Pierre/fish to unified OCR, and uses deterministic fish narration.

## Storage contract

- `lora-adapter`: 20Gi gp3-csi RWO; files under `model-output/`.
- `vllm-model-cache-finetuned`: 50Gi gp3-csi RWO; model at volume root.
- Base download Job mounts both claims to bind them together before adapter
  download and serving. Both Jobs and predictor must use the same GPU node
  selector selected by the deployment script.
- Downloads use pinned Python image and `huggingface_hub==0.36.0` installed under
  writable `/tmp`. No root or GPU reservation is needed by the download Jobs.
- Never redownload into volumes mounted by a predictor. The script skips downloads
  for a Ready predictor and verifies the on-disk identities instead.
- Existing incompatible storage requires reviewed migration; never delete PVCs to
  bypass immutable-field or availability-zone errors.
