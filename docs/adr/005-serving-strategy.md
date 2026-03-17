# ADR-005: Model Serving Strategy

**Date**: 2026-03-03
**Status**: Accepted
**Deciders**: Project team

## Context

The fine-tuned VLM must be served to the web application. Two environments need to be addressed:
1. **Local development** (devcontainer) — for development, testing, and the live conference demo
2. **Production** (OpenShift AI) — for actual deployment

The serving solution must:
- Expose an API the FastAPI web app can call
- Support FP16 inference on ROCm
- Be decoupled from the web app process (model loading is slow; web app should start independently)
- Work on both local ROCm hardware and OpenShift AI without code changes in the client

Additionally, the decision of **distributed training** framework (KubeFlow Pipelines vs. Ray Train) is decided here.

## Decision

**Local serving**: vLLM 0.7.x serving the fine-tuned model as an OpenAI-compatible API on port 8001
**Production serving**: vLLM ServingRuntime via KServe on OpenShift AI
**Web app client**: `openai` Python library pointing to `http://localhost:8001/v1` (local) or the OpenShift AI route URL (production) — same code, different URL and API key
**Distributed training**: Ray Train on OpenShift AI (via KubeRay); KubeFlow Pipelines added post-MVP as orchestration layer

## Alternatives Considered

| Option | Why not selected |
|--------|----------------|
| **Direct transformers inference in the web app process** | Model loading blocks web app startup; no request queuing; cannot scale independently |
| **Triton Inference Server** | More complex to configure for VLMs; vLLM is purpose-built for LLM/VLM serving and better supported on ROCm |
| **TGI (Text Generation Inference)** | Good alternative but vLLM has broader ROCm community support as of 2026; vLLM's OpenAI-compatible API is simpler to use |
| **KubeFlow Pipelines for training** | KFP is an orchestration layer, not a distributed training framework; use Ray Train for actual training, KFP for scheduling/pipelines post-MVP |
| **KubeFlow PyTorchJob** | Valid but requires Kubeflow Training Operator; Ray Train with KubeRay is natively supported in OpenShift AI and has better HuggingFace ecosystem integration |

## Implementation Details

### Local vLLM Serving

```bash
vllm serve models/fine-tuned/qwen25vl-stardew-v1 \
  --dtype float16 \
  --max-model-len 4096 \
  --gpu-memory-utilization 0.85 \
  --served-model-name stardew-vision-vlm \
  --port 8001
```

Configuration file: `configs/serving/vllm_local.yaml`

### OpenShift AI KServe

The fine-tuned LoRA adapter is merged into base model weights (`peft.merge_and_unload()`) before pushing to S3/ODF storage. The InferenceService pulls the merged model at startup.

Files:
- `configs/serving/openshift/serving_runtime.yaml` — defines vLLM container image and resource requests
- `configs/serving/openshift/inference_service.yaml` — points to model artifact, sets replica count

### Web App Client Pattern

The orchestrator VLM is called with a `tools` list in OpenAI function-calling format. It returns a `tool_call` response identifying the screen type; the web app then invokes the corresponding extraction agent as a local library call (no second API call).

```python
from openai import AsyncOpenAI

client = AsyncOpenAI(
    base_url=settings.vlm_endpoint,   # env var: local or OpenShift URL
    api_key=settings.vlm_api_key,     # "EMPTY" for local vLLM
)

# Orchestrator call with tool definitions
response = await client.chat.completions.create(
    model="stardew-vision-vlm",
    messages=[{"role": "user", "content": [{"type": "image_url", ...}, {"type": "text", "text": "..."}]}],
    tools=TOOL_DEFINITIONS,   # crop_pierres_detail_panel, crop_tv_dialog, etc.
    tool_choice="required",
)

# Extraction agents are local library functions, not API calls
tool_name = response.choices[0].message.tool_calls[0].function.name
result = await invoke_extraction_agent(tool_name, image_path)
```

**Note**: Only the orchestrator VLM uses the API. Extraction agents (OpenCV + EasyOCR) are called directly as Python library functions — no second vLLM call, no GPU used for extraction. See ADR-010 for extraction agent details.

### KubeFlow Pipelines (Post-MVP)

KFP will orchestrate: data validation → training trigger → evaluation → conditional model promotion. The Ray Train job is called as a KFP component. Adding KFP does not change the Ray Train code.

## Consequences

**Gets easier**: The same client code works for local and production; swapping environments is a URL change; vLLM handles request batching and GPU memory management automatically.

**Gets harder**: Two processes to start for local development (vLLM server + uvicorn web app); need to add ports 8000 and 8001 to devcontainer.json `forwardPorts`.

**We are committing to**: The OpenAI-compatible API contract; vLLM as the serving runtime; Ray Train as the distributed training framework.

## For the Conference Talk

The live demo runs locally. OpenShift AI serving is shown in the architecture diagram and explained as "how you would deploy this in production." The talk audience sees the same web app interface regardless of whether it's backed by local vLLM or OpenShift AI KServe.
