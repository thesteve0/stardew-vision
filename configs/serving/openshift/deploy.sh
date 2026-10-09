#!/usr/bin/env bash
# The sole production deployment: pinned HF LoRA + unified OCR + Kokoro.
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NS=stardew-vision
IS=stardew-vlm-finetuned
for tool in oc python3 curl; do command -v "$tool" >/dev/null; done
oc whoami >/dev/null
oc get storageclass gp3-csi >/dev/null
oc get crd servingruntimes.serving.kserve.io inferenceservices.serving.kserve.io >/dev/null
# Refuse mixed/legacy installations rather than silently switching route targets.
if oc get deployment/coordinator deployment/pierres-buying-tool inferenceservice/stardew-vlm -n "$NS" -o name --ignore-not-found 2>/dev/null | grep -q .; then
  echo 'Legacy base resources exist; review migration before deploying fine-tuned mode.' >&2
  exit 1
fi
oc apply -f "$DIR/00-namespace.yaml"
if ! oc get secret huggingface-adapter -n "$NS" -o go-template='{{if index .data "token"}}present{{end}}' | grep -q present; then
  echo 'Create huggingface-adapter/token securely as documented in README.md.' >&2
  exit 1
fi
# Reuse the existing predictor node; fresh installs select an unallocated GPU.
# A caller may provide GPU_NODE, but cannot move existing RWO storage blindly.
NODE=$(python3 - <<'PY'
import json, os, subprocess

def get(*args):
    return json.loads(subprocess.check_output(['oc', 'get', *args, '-o', 'json']))

nodes = get('nodes', '-l', 'nvidia.com/gpu.present=true')['items']
pods = get('pods', '-A')['items']
existing = {p['spec'].get('nodeName') for p in pods
            if p['metadata']['namespace'] == 'stardew-vision'
            and p['metadata'].get('labels', {}).get('serving.kserve.io/inferenceservice') == 'stardew-vlm-finetuned'
            and p['status']['phase'] not in ('Succeeded', 'Failed')}
existing.discard(None)
requested = os.environ.get('GPU_NODE')
if len(existing) > 1:
    raise SystemExit('Multiple predictor nodes; review storage topology first.')
if existing and requested and requested not in existing:
    raise SystemExit('GPU_NODE conflicts with current predictor; refusing storage relocation.')
for node in nodes:
    name = node['metadata']['name']
    if requested and name != requested or existing and name not in existing:
        continue
    if node['spec'].get('unschedulable') or not any(c['type'] == 'Ready' and c['status'] == 'True' for c in node['status']['conditions']):
        continue
    used = sum(int(c.get('resources', {}).get('requests', {}).get('nvidia.com/gpu', 0))
               for p in pods if p['spec'].get('nodeName') == name
               and p['status']['phase'] not in ('Succeeded', 'Failed')
               for c in p['spec']['containers'])
    if name in existing or used < int(node['status']['allocatable'].get('nvidia.com/gpu', 0)):
        print(name)
        break
else:
    raise SystemExit('No ready free GPU node; do not stop unrelated workloads automatically.')
PY
)
export DEPLOY_GPU_NODE="$NODE"
echo "Using GPU node: $NODE (Jobs and predictor share placement)"
apply_gpu() {
  oc apply --dry-run=client -f "$1" -o json | python3 -c '
import json, os, sys
obj = json.load(sys.stdin)
spec = obj["spec"]["template"]["spec"] if obj["kind"] == "Job" else obj["spec"]["predictor"]
spec.setdefault("nodeSelector", {})["kubernetes.io/hostname"] = os.environ["DEPLOY_GPU_NODE"]
print(json.dumps(obj))' | oc apply -f -
}
for file in 02-configmap-chat-template 02-pvc-paddlex-cache-ocr-tools 03-pvc-hf-cache 05-pvc-errors-finetuned; do
  oc apply -f "$DIR/$file.yaml"
done
for file in 01-pvc-lora-adapter 05-pvc-model-cache; do
  oc apply -f "$DIR/vllm-finetuned/$file.yaml"
done
READY=$(oc get inferenceservice "$IS" -n "$NS" -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}' --ignore-not-found)
if [[ "$READY" != True ]]; then
  # Never write model volumes while an existing predictor might be reading them.
  if oc get deployment "$IS-predictor" -n "$NS" -o name --ignore-not-found | grep -q .; then
    echo 'Existing predictor is not Ready; diagnose it instead of refreshing mounted files.' >&2
    exit 1
  fi
  for entry in '06-job-download-model:download-qwen-model-finetuned' '07-job-download-adapter:download-lora-adapter'; do
    file=${entry%%:*}; job=${entry#*:}
    if ! oc get job "$job" -n "$NS" -o name --ignore-not-found | grep -q .; then
      apply_gpu "$DIR/vllm-finetuned/$file.yaml"
    fi
    if ! oc wait --for=condition=Complete "job/$job" -n "$NS" --timeout=60m; then
      oc get pods,pvc -n "$NS"
      oc logs "job/$job" -n "$NS" --tail=80 || true
      exit 1
    fi
  done
fi
oc apply -f "$DIR/vllm-finetuned/02-servingruntime.yaml"
apply_gpu "$DIR/vllm-finetuned/03-inferenceservice.yaml"
oc wait --for=condition=Ready "inferenceservice/$IS" -n "$NS" --timeout=20m
# Check mounted artifacts even when completed download Jobs have expired.
oc exec "deployment/$IS-predictor" -n "$NS" -c kserve-container -- python -c '
import hashlib
from pathlib import Path
expected = {
 "adapter_model.safetensors": "373c475669049191527b3d8e8a330f347f236855482bb2282f9604177a915a63",
 "adapter_config.json": "449c057c21c46e3bc0d32d4d7a3590112927c756ae4a7e0ec6326cdc91e2e478",
}
for name, digest in expected.items():
 with (Path("/mnt/lora-adapter/model-output") / name).open("rb") as f:
  assert hashlib.file_digest(f, "sha256").hexdigest() == digest, "Adapter hash mismatch: " + name
metadata = list(Path("/mnt/models/.cache/huggingface/download").rglob("*.metadata"))
assert metadata and all(p.read_text().splitlines()[0] == "cc594898137f460bfe9f0759e9844b3ce807cfb5" for p in metadata), "Base revision mismatch"
print("Mounted adapter hashes and base revision verified.")'
oc apply -f "$DIR/vllm-finetuned/04-configmap-service-endpoints-finetuned.yaml"
for file in 40-deployment-ocr-tools 20-deployment-tts-tool 31-deployment-coordinator-finetuned; do
  oc apply -f "$DIR/$file.yaml"
done
for service in ocr-tools tts-tool coordinator-finetuned; do
  oc rollout status "deployment/$service" -n "$NS" --timeout=15m
done
oc exec deployment/coordinator-finetuned -n "$NS" -- uv run --frozen python -c '
import json, urllib.request
url = "http://stardew-vlm-finetuned-predictor:8080/v1/models"
models = json.load(urllib.request.urlopen(url))["data"]
assert any(m["id"] == "stardew-vlm-finetuned" and m["parent"] == "qwen-base" for m in models), "LoRA model missing"
print("LoRA served model verified.")'
HOST=$(oc get route stardew-vision -n "$NS" -o jsonpath='{.spec.host}')
curl --fail --silent --show-error --retry 10 --retry-delay 2 --retry-all-errors "https://$HOST/health"
printf '\nApplication: https://%s\n' "$HOST"
