# Module 3: vLLM Integration

**Duration**: 2-3 hours
**Prerequisites**: Modules 1-2 completed, vLLM installed
**Example Code**: [`examples/module3_smolagents_vllm.py`](../examples/module3_smolagents_vllm.py)

---

## Learning Objectives

By the end of this module, you will:

- ✅ Understand what vLLM is and why it's used
- ✅ Start a vLLM server with tool calling enabled
- ✅ Use LiteLLMModel backend to connect Smolagents to vLLM
- ✅ Switch between InferenceClient and vLLM with minimal code changes
- ✅ Debug common vLLM connection issues
- ✅ Recognize the OpenAI-compatible API pattern

---

## Why vLLM?

In Module 2, you used `InferenceClientModel` which:
- ✅ Easy to use (just model ID)
- ✅ No setup required
- ❌ Slow (HuggingFace transformers)
- ❌ Requires internet (downloads from Hub)
- ❌ Not production-ready

**vLLM solves these problems**:

### What is vLLM?

**vLLM** = **v**ery **L**arge **L**anguage **M**odel serving

A high-performance inference server for LLMs and VLMs:
- **PagedAttention** - Efficient memory management (2-4x throughput)
- **Continuous batching** - Process multiple requests simultaneously
- **OpenAI-compatible API** - Drop-in replacement for OpenAI endpoints
- **Native tool calling** - Built-in function calling support
- **Local serving** - No internet required

**Think of it as**: NGINX for language models
- Optimized serving layer between your app and the model
- Handles batching, caching, memory management
- Exposes standard API (OpenAI format)

### Why Use vLLM for Stardew Vision?

**Production requirements**:
- ✅ **Fast inference** - Process screenshots in <2 seconds
- ✅ **GPU acceleration** - Use ROCm on AMD hardware
- ✅ **Reliable serving** - Handle multiple concurrent requests
- ✅ **Local execution** - No external API dependencies
- ✅ **OpenShift AI ready** - Same API for local and cloud deployment

**Development benefits**:
- ✅ **Same client code** - Works locally and in production
- ✅ **Standard API** - OpenAI-compatible (widely supported)
- ✅ **Tool calling** - Native function calling support
- ✅ **Debugging** - Clear error messages, logging

See diagram: [`diagrams/vllm-architecture.txt`](../diagrams/vllm-architecture.txt)

---

## Conceptual Overview: vLLM Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    LOCAL DEVELOPMENT                         │
└──────────────────────────────────────────────────────────────┘

Your Application                    vLLM Server
┌─────────────────┐                ┌─────────────────────────┐
│                 │  HTTP Request  │                         │
│  Smolagents     │───────────────>│  OpenAI-Compatible API  │
│  LiteLLMModel   │                │  (port 8001)            │
│                 │                │                         │
│  - Tools: [...]  │                │  ┌───────────────────┐  │
│  - Prompt       │                │  │ Request Handler   │  │
│                 │                │  │ - Parse prompt    │  │
│                 │  HTTP Response │  │ - Prepare inputs  │  │
│                 │<───────────────│  └─────────┬─────────┘  │
│                 │                │            │            │
└─────────────────┘                │            ▼            │
                                   │  ┌───────────────────┐  │
                                   │  │ vLLM Engine       │  │
                                   │  │ - PagedAttention  │  │
                                   │  │ - KV cache        │  │
                                   │  │ - Batching        │  │
                                   │  └─────────┬─────────┘  │
                                   │            │            │
                                   │            ▼            │
                                   │  ┌───────────────────┐  │
                                   │  │ Model             │  │
                                   │  │ Qwen2.5-VL-7B     │  │
                                   │  │ (GPU: ROCm)       │  │
                                   │  └───────────────────┘  │
                                   └─────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                    PRODUCTION (OpenShift AI)                  │
└──────────────────────────────────────────────────────────────┘

Your Web App                       KServe Endpoint
┌─────────────────┐                ┌─────────────────────────┐
│                 │  HTTPS Request │                         │
│  Smolagents     │───────────────>│  vLLM via KServe        │
│  LiteLLMModel   │                │  (https://model.apps...) │
│                 │                │                         │
│  base_url:      │                │  Same vLLM engine       │
│  https://...    │                │  Same API format        │
│                 │  HTTPS Response│                         │
│                 │<───────────────│                         │
└─────────────────┘                └─────────────────────────┘

         SAME CODE - JUST DIFFERENT BASE_URL!
```

**Key insight**: Your client code doesn't change between local and production. Only the `base_url` changes.

---

## Setting Up vLLM

### Step 1: Verify vLLM Installation

```bash
# Check vLLM is installed
vllm --version
# Should show: vllm 0.7.x

# Check model path exists
ls -la /workspaces/stardew-vision/models/base/Qwen2.5-VL-7B-Instruct/
# Should show: config.json, model files, etc.
```

**If vLLM not installed**:
```bash
uv add vllm
```

### Step 2: Start vLLM Server

Open a **separate terminal** (or use tmux/screen):

```bash
vllm serve /workspaces/stardew-vision/models/base/Qwen2.5-VL-7B-Instruct \
  --port 8001 \
  --dtype float16 \
  --enable-tool-calling \
  --max-model-len 4096
```

**Parameters explained**:
- `serve` - Start server mode (vs `run` for one-off inference)
- Model path - Local path to downloaded model
- `--port 8001` - HTTP server port (8000 conflicts with FastAPI)
- `--dtype float16` - FP16 precision (required for ROCm 7.2)
- `--enable-tool-calling` - Enable function calling support
- `--max-model-len 4096` - Max context length (saves memory)

**First run**: Model loads into GPU, takes 30-60 seconds

**Expected output**:
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8001 (Press CTRL+C to quit)
INFO: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 0.0 tokens/s
```

**Keep this terminal running!** vLLM server must stay up for Module 3.

### Step 3: Verify Server is Running

In a **different terminal**:

```bash
# Check server health
curl http://localhost:8001/health
# Expected: {"status": "ok"}

# List available models
curl http://localhost:8001/v1/models
# Expected: {"data": [{"id": "Qwen2.5-VL-7B-Instruct", ...}]}
```

**If connection refused**:
- Check vLLM terminal for errors
- Verify port 8001 is not already in use: `lsof -i :8001`
- Check firewall settings

---

## Code Walkthrough

Now let's walk through `examples/module3_smolagents_vllm.py` and see the differences from Module 2.

### Part 1: Imports (Lines 7-9)

```python
from smolagents import CodeAgent, Tool, LiteLLMModel
import json
```

**Changed from Module 2**:
```diff
- from smolagents import CodeAgent, Tool, InferenceClientModel
+ from smolagents import CodeAgent, Tool, LiteLLMModel
```

**Why LiteLLMModel?**
- `InferenceClientModel` - HuggingFace-specific (transformers or Inference API)
- `LiteLLMModel` - Universal adapter for OpenAI-compatible endpoints

**LiteLLMModel supports**:
- vLLM (local)
- TGI (Text Generation Inference)
- OpenAI API
- Anthropic API
- Azure OpenAI
- Any OpenAI-compatible endpoint

### Part 2: Tool Class (Lines 11-32)

```python
class CropPierresPanelTool(Tool):
    """Same tool from Module 2."""
    name = "crop_pierres_detail_panel"
    description = "Extract item details from Pierre's General Store detail panel in screenshot"
    inputs = {
        "image_path": {
            "type": "string",
            "description": "Path to the screenshot file"
        }
    }
    output_type = "dict"

    def forward(self, image_path: str):
        from stardew_vision.tools import crop_pierres_detail_panel
        print(f"[Tool] Executing on {image_path}")
        result = crop_pierres_detail_panel(image_path)
        print(f"[Tool] Result: {result}")
        return result
```

**No changes from Module 2!**

This is the power of abstraction - tools don't care about the model backend.

### Part 3: Configure LiteLLMModel (Lines 39-49)

```python
print("Connecting to vLLM endpoint at http://localhost:8001...")
model = LiteLLMModel(
    model_id="Qwen2.5-VL-7B-Instruct",      # Model name (for vLLM routing)
    base_url="http://localhost:8001/v1",    # vLLM OpenAI-compatible endpoint
    api_key="EMPTY"                         # vLLM doesn't require auth locally
)
print("Connected!")
```

**Compare to Module 2**:
```python
# Module 2 (InferenceClientModel)
model = InferenceClientModel(
    model_id="Qwen/Qwen2.5-VL-7B-Instruct"
)

# Module 3 (LiteLLMModel)
model = LiteLLMModel(
    model_id="Qwen2.5-VL-7B-Instruct",
    base_url="http://localhost:8001/v1",
    api_key="EMPTY"
)
```

**Parameters explained**:

**`model_id`**:
- Module 2: HuggingFace format (`org/repo`)
- Module 3: Just model name (vLLM already has model loaded)

**`base_url`**:
- OpenAI-compatible API base URL
- Format: `http://host:port/v1` (note the `/v1` suffix!)
- Local: `http://localhost:8001/v1`
- OpenShift AI: `https://model-name-namespace.apps.cluster.com/v1`

**`api_key`**:
- Local vLLM: Use `"EMPTY"` (no authentication)
- OpenAI: Use actual API key (`sk-...`)
- OpenShift AI: Use service token

**Under the hood**: LiteLLMModel translates Smolagents calls to OpenAI API format:
```
Smolagents           LiteLLMModel               vLLM
┌─────────┐          ┌───────────┐          ┌─────────┐
│ agent.  │  calls   │ Translates│  HTTP    │ OpenAI  │
│ run()   │────────> │ to OpenAI │────────> │ API     │
│         │          │ format    │ POST     │ /v1/... │
└─────────┘          └───────────┘          └─────────┘
```

### Part 4: Create Tools and Agent (Lines 51-61)

```python
tools = [CropPierresPanelTool()]

print("Initializing CodeAgent with vLLM backend...")
agent = CodeAgent(
    tools=tools,
    model=model,              # LiteLLMModel instead of InferenceClientModel
    add_base_tools=False,
    max_steps=3,
    verbosity=2
)
print("Agent initialized!")
```

**Exactly the same as Module 2!**

Only difference: `model` is `LiteLLMModel` instead of `InferenceClientModel`.

**This is the abstraction win** - agent code doesn't change when you swap backends.

### Part 5: Run Agent (Lines 65-75)

```python
image_path = "/workspaces/stardew-vision/tests/fixtures/pierre_shop_001.png"

print(f"Running agent on: {image_path}")
print("-" * 80)

result = agent.run(
    f"Extract item information from screenshot at {image_path} using crop_pierres_detail_panel."
)

print("-" * 80)
print()
print("Agent Result:")
print(json.dumps(result, indent=2))
```

**Exactly the same as Module 2!**

Same `agent.run()` call, same result format. The only difference is **speed** - vLLM is much faster.

### Part 6: Connection Check (Lines 90-104)

```python
# Check vLLM is running
import requests
try:
    r = requests.get("http://localhost:8001/v1/models", timeout=5)
    r.raise_for_status()
    print("✅ vLLM server detected")
    print()
except Exception as e:
    print("❌ vLLM server not running!")
    print("Start it with:")
    print("  vllm serve models/base/Qwen2.5-VL-7B-Instruct --port 8001 --dtype float16 --enable-tool-calling")
    print()
    exit(1)

run_smolagents_vllm()
```

**New in Module 3**: Pre-flight check

Before running agent, verify vLLM is accessible. This prevents confusing error messages.

**Error handling pattern**:
```python
try:
    # Try to connect
    requests.get("http://localhost:8001/v1/models", timeout=5)
except:
    # Helpful error message with fix
    print("❌ vLLM not running. Start with: vllm serve ...")
    exit(1)
```

Always include helpful error messages in production code!

---

## The OpenAI-Compatible API Pattern

**Key concept**: vLLM implements the same API as OpenAI.

This means:
1. Same request format
2. Same response format
3. Same endpoint paths
4. Same authentication method (API keys)

### OpenAI API Endpoints

```
POST /v1/completions          # Text completion
POST /v1/chat/completions     # Chat (what we use)
POST /v1/embeddings           # Embeddings
GET  /v1/models               # List models
```

### Example Request (Chat Completions)

**What Smolagents sends** (via LiteLLMModel):

```http
POST http://localhost:8001/v1/chat/completions
Content-Type: application/json

{
  "model": "Qwen2.5-VL-7B-Instruct",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant..."},
    {"role": "user", "content": "Extract from screenshot"}
  ],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "crop_pierres_detail_panel",
        "description": "...",
        "parameters": {...}
      }
    }
  ],
  "tool_choice": "auto"
}
```

### Example Response

**What vLLM returns**:

```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "created": 1677652288,
  "model": "Qwen2.5-VL-7B-Instruct",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": null,
        "tool_calls": [
          {
            "id": "call_xyz",
            "type": "function",
            "function": {
              "name": "crop_pierres_detail_panel",
              "arguments": "{\"image_path\": \"/path/to/screenshot.png\"}"
            }
          }
        ]
      },
      "finish_reason": "tool_calls"
    }
  ]
}
```

**LiteLLMModel parses this** and returns it to Smolagents in the expected format.

**Why this matters**:
- Same API for local vLLM and OpenAI GPT-4
- Same API for local vLLM and OpenShift AI deployment
- Can switch providers with just `base_url` change

---

## Hands-On Activity

### Checkpoint 1: Start vLLM and Run Example

**Terminal 1**: Start vLLM server
```bash
vllm serve /workspaces/stardew-vision/models/base/Qwen2.5-VL-7B-Instruct \
  --port 8001 \
  --dtype float16 \
  --enable-tool-calling \
  --max-model-len 4096
```

**Wait for**: `Application startup complete`

**Terminal 2**: Test vLLM is running
```bash
curl http://localhost:8001/v1/models | jq
```

**Expected**:
```json
{
  "object": "list",
  "data": [
    {
      "id": "Qwen2.5-VL-7B-Instruct",
      "object": "model",
      "created": 1234567890,
      "owned_by": "vllm"
    }
  ]
}
```

**Terminal 2**: Run Module 3 example
```bash
cd /workspaces/stardew-vision
python agent-learning/examples/module3_smolagents_vllm.py
```

**Expected output**:
```
✅ vLLM server detected

================================================================================
MODULE 3: SMOLAGENTS + vLLM
================================================================================

Connecting to vLLM endpoint at http://localhost:8001...
Connected!

Initializing CodeAgent with vLLM backend...
Agent initialized!

Running agent on: /workspaces/stardew-vision/tests/fixtures/pierre_shop_001.png
--------------------------------------------------------------------------------
[Agent] Step 1/3
[VLM] Generating code...
[Tool] Executing on /workspaces/stardew-vision/tests/fixtures/pierre_shop_001.png
[Tool] Result: {"name": "Parsnip", ...}
--------------------------------------------------------------------------------

Agent Result:
{
  "name": "Parsnip",
  "description": "A spring vegetable. Still loved by many.",
  "price_per_unit": 20,
  "quantity_selected": 5,
  "total_cost": 100
}

✅ Module 3 Complete!
```

**Compare speed to Module 2**:
- Module 2 (InferenceClientModel): ~5-10 seconds
- Module 3 (vLLM): ~1-2 seconds

### Checkpoint 2: Switch to Different Base URL

**Simulate production**: Change base_url as if you deployed to OpenShift AI.

**Edit the example** or create a test script:
```python
# Local vLLM
model = LiteLLMModel(
    model_id="Qwen2.5-VL-7B-Instruct",
    base_url="http://localhost:8001/v1",
    api_key="EMPTY"
)

# "Production" (still local, but shows pattern)
# model = LiteLLMModel(
#     model_id="Qwen2.5-VL-7B-Instruct",
#     base_url="https://model-stardew-vision.apps.cluster.com/v1",
#     api_key=os.getenv("OPENSHIFT_TOKEN")
# )

agent = CodeAgent(tools=[...], model=model)
```

**Key observation**: Only 2 parameters change (base_url, api_key), everything else identical.

### Checkpoint 3: Debug Connection Issues

**Intentionally break the connection** to practice debugging:

**Test 1: Wrong port**
```python
model = LiteLLMModel(
    model_id="Qwen2.5-VL-7B-Instruct",
    base_url="http://localhost:9999/v1",  # Wrong port!
    api_key="EMPTY"
)
```

**Expected error**:
```
requests.exceptions.ConnectionError: ('Connection aborted.', ConnectionRefusedError(111, 'Connection refused'))
```

**Fix**: Use correct port (8001)

**Test 2: Missing /v1 suffix**
```python
base_url="http://localhost:8001"  # Missing /v1!
```

**Expected error**:
```
404 Not Found
```

**Fix**: Add `/v1` suffix

**Test 3: vLLM not running**
```python
# Stop vLLM server in Terminal 1 (CTRL+C)
# Try to run agent
```

**Expected error**:
```
❌ vLLM server not running!
Start it with:
  vllm serve models/base/Qwen2.5-VL-7B-Instruct --port 8001 --dtype float16 --enable-tool-calling
```

**Fix**: Start vLLM server

**Full debugging exercise**: [`exercises/exercise3_debugging.md`](../exercises/exercise3_debugging.md)

---

## Common vLLM Issues

### Issue 1: Connection Refused

**Symptom**:
```
requests.exceptions.ConnectionError: Connection refused
```

**Causes**:
1. vLLM server not running
2. Wrong port
3. vLLM still starting up

**Fix**:
```bash
# Check vLLM is running
curl http://localhost:8001/health

# Check port is correct
lsof -i :8001  # Should show vllm process

# Wait for "Application startup complete" in vLLM terminal
```

### Issue 2: 404 Not Found

**Symptom**:
```
404 Client Error: Not Found
```

**Cause**: Missing `/v1` in base_url

**Fix**:
```python
# WRONG
base_url="http://localhost:8001"

# RIGHT
base_url="http://localhost:8001/v1"
```

### Issue 3: Tool Calling Not Enabled

**Symptom**:
```
VLM returns text instead of tool call
```

**Cause**: vLLM started without `--enable-tool-calling`

**Fix**:
```bash
# Restart vLLM with flag
vllm serve ... --enable-tool-calling
```

### Issue 4: Out of Memory

**Symptom**:
```
RuntimeError: CUDA out of memory
```

**Causes**:
1. Context length too large
2. Multiple models loaded
3. Insufficient GPU memory

**Fix**:
```bash
# Reduce context length
vllm serve ... --max-model-len 2048  # Instead of 4096

# Check GPU memory
rocm-smi  # For ROCm
nvidia-smi  # For CUDA

# Kill other GPU processes
```

### Issue 5: Model Not Found

**Symptom**:
```
ValueError: Model path does not exist
```

**Fix**:
```bash
# Check model path
ls -la /workspaces/stardew-vision/models/base/Qwen2.5-VL-7B-Instruct/

# If missing, download from HuggingFace
# (this was done in project setup)
```

---

## Key Patterns

### Pattern 1: Environment-Specific Configuration

**Use environment variables** for base_url and api_key:

```python
import os

# Development (local vLLM)
if os.getenv("ENV") == "development":
    base_url = "http://localhost:8001/v1"
    api_key = "EMPTY"

# Production (OpenShift AI)
elif os.getenv("ENV") == "production":
    base_url = os.getenv("VLLM_ENDPOINT")
    api_key = os.getenv("VLLM_API_KEY")

model = LiteLLMModel(
    model_id="Qwen2.5-VL-7B-Instruct",
    base_url=base_url,
    api_key=api_key
)
```

### Pattern 2: Connection Health Check

**Always verify connectivity** before running agent:

```python
import requests

def check_vllm_health(base_url: str, timeout: int = 5) -> bool:
    """Check if vLLM server is healthy."""
    try:
        # Remove /v1 suffix for health endpoint
        health_url = base_url.replace("/v1", "") + "/health"
        r = requests.get(health_url, timeout=timeout)
        r.raise_for_status()
        return True
    except:
        return False

# Before creating model
if not check_vllm_health("http://localhost:8001/v1"):
    raise ConnectionError("vLLM server not available")

model = LiteLLMModel(...)
```

### Pattern 3: Graceful Degradation

**Fall back to InferenceClientModel** if vLLM unavailable:

```python
try:
    # Try vLLM first (faster)
    model = LiteLLMModel(
        model_id="Qwen2.5-VL-7B-Instruct",
        base_url="http://localhost:8001/v1",
        api_key="EMPTY"
    )
    # Quick health check
    requests.get("http://localhost:8001/health", timeout=2)
    print("Using vLLM backend (fast)")
except:
    # Fall back to InferenceClientModel (slower, but works)
    model = InferenceClientModel(
        model_id="Qwen/Qwen2.5-VL-7B-Instruct"
    )
    print("Using InferenceClient backend (slow)")

# Agent code doesn't change!
agent = CodeAgent(tools=[...], model=model)
```

---

## Key Takeaways

### 1. vLLM is Production Serving

Module 2 (InferenceClient): Good for testing
Module 3 (vLLM): Good for production

**Performance gains**:
- 2-4x faster inference
- Better memory efficiency
- Concurrent request handling

### 2. LiteLLMModel is Universal Adapter

Works with any OpenAI-compatible endpoint:
- ✅ Local vLLM
- ✅ OpenShift AI vLLM
- ✅ TGI (Text Generation Inference)
- ✅ OpenAI API
- ✅ Anthropic API

**Same interface, different backends**.

### 3. Only base_url Changes

**Development**:
```python
base_url="http://localhost:8001/v1"
```

**Production**:
```python
base_url="https://model-stardew-vision.apps.cluster.com/v1"
```

**Everything else stays the same!**

### 4. OpenAI API is the Standard

Understanding OpenAI API format helps with:
- vLLM debugging
- Reading vLLM logs
- Building custom clients
- Switching providers

### 5. Tool Code Never Changes

```python
class MyTool(Tool):
    # Same code works with:
    # - InferenceClientModel (Module 2)
    # - LiteLLMModel + vLLM (Module 3)
    # - LiteLLMModel + OpenAI (future)
```

**This abstraction is powerful** - write tools once, use anywhere.

---

## Comparison: Module 2 vs Module 3

| Aspect              | Module 2                    | Module 3                  |
|---------------------|----------------------------|---------------------------|
| Model Backend       | InferenceClientModel       | LiteLLMModel              |
| Server              | HuggingFace transformers   | vLLM                      |
| Speed               | Slow (~5-10s)              | Fast (~1-2s)              |
| Setup               | None (auto-download)       | Start vLLM server         |
| Internet Required   | Yes (HF Hub)               | No (local model)          |
| Production Ready    | No                         | Yes                       |
| API Format          | HuggingFace-specific       | OpenAI-compatible         |
| Lines Changed       | N/A                        | ~5 (just model init)      |

**Bottom line**: Same agent code, much faster inference.

---

## Summary

You now understand:

1. ✅ **What vLLM is** - Production inference server for LLMs/VLMs
2. ✅ **Why use vLLM** - 2-4x faster, production-ready, local serving
3. ✅ **LiteLLMModel** - Universal adapter for OpenAI-compatible endpoints
4. ✅ **Code changes** - Only model initialization (5 lines)
5. ✅ **OpenAI API** - Standard format used by vLLM
6. ✅ **Deployment pattern** - Same code, different base_url

**The progression**:
- Module 1: Manual dispatch (understand mechanics)
- Module 2: Smolagents + InferenceClient (easy setup, slow)
- Module 3: Smolagents + vLLM (production speed, local)
- Module 4: Add error handling, logging, tests

---

## Next Steps

**Current state**:
- ✅ Smolagents CodeAgent (automated dispatch)
- ✅ vLLM backend (production speed)
- ✅ Local serving (no external dependencies)

**Still missing**:
- ❌ Error handling (what if tool fails?)
- ❌ Observability (how do we track calls?)
- ❌ Testing (how to test without VLM?)
- ❌ Validation (how to ensure correct output?)

**Module 4** builds the production wrapper:
- `VLMOrchestrator` class
- Error handling and retries
- MLFlow integration
- Unit tests with mocks

---

## Additional Resources

**Code**:
- Full example: [`examples/module3_smolagents_vllm.py`](../examples/module3_smolagents_vllm.py)
- Exercise: [`exercises/exercise3_debugging.md`](../exercises/exercise3_debugging.md)

**Diagrams**:
- [`diagrams/vllm-architecture.txt`](../diagrams/vllm-architecture.txt) - vLLM internals
- [`diagrams/tool-calling-flow.txt`](../diagrams/tool-calling-flow.txt) - General flow

**Official Docs**:
- [vLLM Documentation](https://docs.vllm.ai/)
- [vLLM OpenAI Compatibility](https://docs.vllm.ai/en/latest/serving/openai_compatible_server.html)
- [LiteLLM Documentation](https://docs.litellm.ai/)

**Related**:
- ADR-005: Serving strategy (why vLLM)
- `docs/plan.md`: Deployment architecture

---

**Ready for Module 4?** → [`module4-production-wrapper.md`](module4-production-wrapper.md)

Learn how to build a production-ready VLMOrchestrator with error handling, logging, and tests!
