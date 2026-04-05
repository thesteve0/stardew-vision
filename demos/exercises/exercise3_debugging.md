# Exercise 3: Debugging Agent/Tool-Calling Issues

**Objective**: Learn to diagnose and fix common agent and tool-calling problems.

**Time**: 60-90 minutes

**Prerequisites**: Completed Module 1-5, Exercise 1-2

---

## Scenario 1: VLM Not Calling Tools

### Problem

Agent returns text description instead of calling the extraction tool.

```python
from smolagents import CodeAgent, LiteLLMModel
from stardew_vision.models.vlm_wrapper import PierresPanelTool

model = LiteLLMModel(
    model_id="Qwen2.5-VL-7B-Instruct",
    base_url="http://localhost:8001/v1",
    api_key="EMPTY"
)

agent = CodeAgent(tools=[PierresPanelTool()], model=model, verbosity=2)

result = agent.run("What's in this screenshot?")
# Returns: "This appears to be a shop interface..."
# Expected: Tool call with extracted data
```

### Debug Steps

1. **Check verbosity output** - What code did agent generate?

   ```python
   # Look for generated code in verbosity=2 output
   # Does it call the tool or just print text?
   ```

2. **Check vLLM tool calling enabled**

   ```bash
   # Verify vLLM was started with --enable-tool-calling
   curl http://localhost:8001/v1/models | jq .
   ```

3. **Check prompt clarity**

   ```python
   # Try more explicit prompt
   result = agent.run(
       "Use the crop_pierres_detail_panel tool to extract "
       "information from screenshot.png"
   )
   ```

4. **Check tool description**

   ```python
   # Is the tool description clear?
   print(PierresPanelTool().description)
   # Should explain WHEN to use the tool
   ```

### Your Solution

<details>
<summary>Click for solution approach</summary>

**Root causes**:
1. vLLM not started with `--enable-tool-calling`
2. Prompt too vague (doesn't mention tool)
3. Tool description unclear (VLM doesn't know when to use it)

**Fix**:
```python
# Restart vLLM with tool calling
# vllm serve ... --enable-tool-calling

# Use explicit prompt
result = agent.run(
    "Extract all fields from the Pierre's shop screenshot at screenshot.png "
    "using the crop_pierres_detail_panel tool."
)

# Improve tool description
class PierresPanelTool(Tool):
    name = "crop_pierres_detail_panel"
    description = (
        "Extract item details (name, description, price, quantity, total) "
        "from Pierre's General Store detail panel in Stardew Valley screenshots. "
        "Use this ONLY for Pierre's shop UI."
    )
    # ...
```

</details>

---

## Scenario 2: Tool Execution Fails

### Problem

Agent calls tool but execution fails.

```python
agent = CodeAgent(tools=[PierresPanelTool()], model=model, verbosity=2)

result = agent.run("Extract from /path/to/screenshot.png")
# Error: FileNotFoundError: Image not found
```

### Debug Steps

1. **Check file path**

   ```python
   from pathlib import Path
   image_path = "/path/to/screenshot.png"
   print(f"File exists: {Path(image_path).exists()}")
   ```

2. **Check tool implementation**

   ```python
   # Test tool manually (bypass agent)
   tool = PierresPanelTool()
   result = tool.forward("/workspaces/stardew-vision/tests/fixtures/pierre_shop_001.png")
   print(result)
   ```

3. **Check error handling**

   ```python
   # Does tool have try/except?
   def forward(self, image_path: str):
       try:
           # Implementation
           return result
       except Exception as e:
           logger.error(f"Tool failed: {e}")
           return {"error": str(e)}  # Return error dict instead of raising
   ```

4. **Check dependencies**

   ```python
   # Are required packages installed?
   try:
       from stardew_vision.tools import crop_pierres_detail_panel
       print("✅ Tool imported successfully")
   except ImportError as e:
       print(f"❌ Import failed: {e}")
   ```

### Your Solution

Debug this failing tool call and fix it.

<details>
<summary>Click for solution approach</summary>

**Root causes**:
1. File path incorrect (relative vs absolute)
2. Missing dependencies (OpenCV, PaddleOCR)
3. Tool doesn't validate inputs
4. No error handling in tool

**Fix**:
```python
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class PierresPanelTool(Tool):
    # ...

    def forward(self, image_path: str):
        """Execute with robust error handling."""
        try:
            # Validate input
            path = Path(image_path)
            if not path.exists():
                logger.error(f"File not found: {image_path}")
                return {"error": f"Image not found: {image_path}"}

            # Execute extraction
            from stardew_vision.tools import crop_pierres_detail_panel
            result = crop_pierres_detail_panel(str(path.absolute()))

            logger.info(f"Extraction successful: {result}")
            return result

        except ImportError as e:
            logger.error(f"Dependency missing: {e}")
            return {"error": f"Tool dependencies not installed: {e}"}

        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            return {"error": f"Extraction failed: {e}"}
```

</details>

---

## Scenario 3: Agent Hallucinates Tools

### Problem

Agent tries to call tools that don't exist.

```python
agent = CodeAgent(tools=[PierresPanelTool()], model=model, verbosity=2)

result = agent.run("Extract everything from this screenshot")
# Error: Tool 'extract_everything' not found
# Agent invented a tool name!
```

### Debug Steps

1. **Check available tools**

   ```python
   print("Available tools:")
   for tool in agent.tools:
       print(f"  - {tool.name}: {tool.description}")
   ```

2. **Check system prompt**

   ```python
   # Add explicit constraint
   agent = CodeAgent(
       tools=[PierresPanelTool()],
       model=model,
       system_prompt=(
           "You must ONLY use the tools provided. "
           "Available tools: crop_pierres_detail_panel. "
           "Do not invent new tools."
       )
   )
   ```

3. **Check prompt specificity**

   ```python
   # Be explicit about tool name
   result = agent.run(
       "Use crop_pierres_detail_panel to extract from screenshot.png"
   )
   ```

### Your Solution

Prevent the agent from hallucinating tools.

<details>
<summary>Click for solution approach</summary>

**Root causes**:
1. Vague prompt ("extract everything")
2. No system prompt constraining tool use
3. Model not fine-tuned on tool calling

**Fix**:
```python
# 1. Explicit system prompt
system_prompt = (
    "You are a screenshot analyzer. "
    "ONLY use these exact tools (do not invent new ones): "
    "- crop_pierres_detail_panel: Extract from Pierre's shop panel"
)

# 2. Specific user prompt
user_prompt = (
    "Analyze the screenshot at {image_path}. "
    "If it shows Pierre's shop, use crop_pierres_detail_panel. "
    "If it's a different screen, return {{'error': 'Unknown screen type'}}."
)

# 3. Validate tool name before execution
def validate_tool_call(tool_name: str, available_tools: list) -> bool:
    """Validate tool exists before calling."""
    tool_names = [t.name for t in available_tools]
    if tool_name not in tool_names:
        raise ValueError(
            f"Invalid tool: {tool_name}. "
            f"Available: {tool_names}"
        )
    return True

# 4. [Phase 1 fine-tuning] Fine-tune VLM on correct tool calls
```

</details>

---

## Scenario 4: vLLM Connection Timeout

### Problem

Agent hangs or times out when trying to connect to vLLM.

```python
model = LiteLLMModel(
    model_id="Qwen2.5-VL-7B-Instruct",
    base_url="http://localhost:8001/v1",
    api_key="EMPTY"
)

agent = CodeAgent(tools=[PierresPanelTool()], model=model)

# Hangs for 60 seconds then times out
result = agent.run("Extract from screenshot.png")
```

### Debug Steps

1. **Check vLLM server status**

   ```bash
   # Is vLLM running?
   curl http://localhost:8001/v1/models

   # Check process
   ps aux | grep vllm
   ```

2. **Check endpoint URL**

   ```python
   # Verify correct endpoint
   import requests
   response = requests.get("http://localhost:8001/v1/models", timeout=5)
   print(response.json())
   ```

3. **Check vLLM logs**

   ```bash
   # Look for errors in vLLM output
   # Common issues:
   # - Out of memory
   # - Model not loaded
   # - Port already in use
   ```

4. **Test with curl**

   ```bash
   # Direct API test
   curl http://localhost:8001/v1/chat/completions \
     -H "Content-Type: application/json" \
     -d '{
       "model": "Qwen2.5-VL-7B-Instruct",
       "messages": [{"role": "user", "content": "Hello"}]
     }'
   ```

### Your Solution

Diagnose and fix the connection issue.

<details>
<summary>Click for solution approach</summary>

**Root causes**:
1. vLLM not running
2. Wrong port (8000 vs 8001)
3. vLLM crashed (OOM, etc.)
4. Firewall blocking connection

**Fix**:
```bash
# 1. Check vLLM is running
lsof -i :8001

# 2. Restart vLLM if needed
vllm serve /workspaces/stardew-vision/models/base/Qwen2.5-VL-7B-Instruct \
  --port 8001 \
  --dtype float16 \
  --enable-tool-calling \
  --max-model-len 4096

# 3. Verify endpoint
curl http://localhost:8001/v1/models

# 4. Test in Python
import requests
response = requests.get("http://localhost:8001/v1/models", timeout=5)
print(response.json())

# 5. If still failing, check vLLM logs for errors
```

</details>

---

## Scenario 5: Invalid Extraction Results

### Problem

Tool runs successfully but returns invalid data.

```python
result = agent.run("Extract from screenshot.png")
# Result: {"name": "", "price_per_unit": -1, "total_cost": 0}
# Empty name, negative price - clearly wrong!
```

### Debug Steps

1. **Check extraction tool directly**

   ```python
   from stardew_vision.tools import crop_pierres_detail_panel

   # Test tool without agent
   result = crop_pierres_detail_panel(
       "/workspaces/stardew-vision/tests/fixtures/pierre_shop_001.png"
   )
   print(result)
   ```

2. **Validate against schema**

   ```python
   from pydantic import BaseModel, ValidationError, Field

   class PierreShopResult(BaseModel):
       name: str = Field(..., min_length=1)
       price_per_unit: int = Field(..., gt=0)
       quantity_selected: int = Field(..., gt=0)
       total_cost: int = Field(..., gt=0)

   # Validate result
   try:
       validated = PierreShopResult(**result)
       print("✅ Validation passed")
   except ValidationError as e:
       print(f"❌ Validation failed: {e}")
   ```

3. **Add verification checks**

   ```python
   def verify_extraction(result: dict) -> bool:
       """Verify extraction quality."""
       checks = [
           ("has_name", bool(result.get("name", "").strip())),
           ("price_positive", result.get("price_per_unit", 0) > 0),
           ("quantity_positive", result.get("quantity_selected", 0) > 0),
           ("total_matches",
            result.get("total_cost") ==
            result.get("price_per_unit", 0) * result.get("quantity_selected", 0)
           )
       ]

       failed = [name for name, passed in checks if not passed]

       if failed:
           print(f"❌ Failed checks: {failed}")
           return False

       print("✅ All checks passed")
       return True

   # Test
   verify_extraction(result)
   ```

4. **Check screenshot quality**

   ```python
   from PIL import Image

   image = Image.open("screenshot.png")
   print(f"Size: {image.size}")
   print(f"Mode: {image.mode}")

   # Is it too small/blurry for OCR?
   if image.width < 800:
       print("⚠️  Image might be too small for accurate OCR")
   ```

### Your Solution

Add validation and verification to catch invalid results.

<details>
<summary>Click for solution approach</summary>

**Root causes**:
1. OCR failed (blurry image, wrong region)
2. Template matching failed (different resolution)
3. Parsing logic has bugs
4. No validation before returning

**Fix**:
```python
from pydantic import BaseModel, ValidationError, Field
import logging

logger = logging.getLogger(__name__)

class PierreShopResult(BaseModel):
    """Validated extraction result."""
    name: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    price_per_unit: int = Field(..., gt=0)
    quantity_selected: int = Field(..., gt=0)
    total_cost: int = Field(..., gt=0)

def validate_and_verify(result: dict) -> PierreShopResult:
    """Validate schema and verify quality."""
    # Schema validation
    try:
        validated = PierreShopResult(**result)
    except ValidationError as e:
        logger.error(f"Schema validation failed: {e}")
        raise ValueError(f"Invalid extraction: {e}")

    # Business logic verification
    expected_total = validated.price_per_unit * validated.quantity_selected
    if validated.total_cost != expected_total:
        logger.warning(
            f"Total cost mismatch: {validated.total_cost} != "
            f"{expected_total} ({validated.price_per_unit} * {validated.quantity_selected})"
        )
        # Could raise error or fix automatically:
        # validated.total_cost = expected_total

    return validated

# Usage in VLMOrchestrator
def analyze_screenshot(self, image_path: str) -> dict:
    result = self.agent.run(...)
    validated = validate_and_verify(result)  # Raises if invalid
    return validated.dict()
```

</details>

---

## Scenario 6: Slow Response Times

### Problem

Agent takes >10 seconds to return results.

```python
import time

start = time.time()
result = agent.run("Extract from screenshot.png")
latency = time.time() - start

print(f"Latency: {latency:.2f}s")
# Latency: 12.45s - Too slow!
```

### Debug Steps

1. **Profile with MLFlow**

   ```python
   import mlflow
   import time

   with mlflow.start_run():
       # Time VLM call
       start = time.time()
       result = agent.run("Extract from screenshot.png")
       vlm_latency = time.time() - start

       mlflow.log_metric("vlm_latency_ms", vlm_latency * 1000)

       # Time tool execution separately
       start = time.time()
       tool_result = tool.forward(image_path)
       tool_latency = time.time() - start

       mlflow.log_metric("tool_latency_ms", tool_latency * 1000)

   print(f"VLM: {vlm_latency:.2f}s")
   print(f"Tool: {tool_latency:.2f}s")
   ```

2. **Check vLLM performance**

   ```python
   # Test vLLM directly (no agent)
   from openai import OpenAI

   client = OpenAI(base_url="http://localhost:8001/v1", api_key="EMPTY")

   start = time.time()
   response = client.chat.completions.create(
       model="Qwen2.5-VL-7B-Instruct",
       messages=[{"role": "user", "content": "Hello"}],
       max_tokens=50
   )
   vllm_latency = time.time() - start

   print(f"Raw vLLM latency: {vllm_latency:.2f}s")
   ```

3. **Check model parameters**

   ```bash
   # Is vLLM using GPU?
   # Check --dtype float16 (faster than float32)
   # Check --max-model-len (smaller = faster)
   ```

4. **Optimize agent config**

   ```python
   # Use max_steps=1 for single-shot
   agent = CodeAgent(
       tools=[PierresPanelTool()],
       model=model,
       max_steps=1,  # Don't iterate
       verbosity=0   # Less logging overhead
   )
   ```

### Your Solution

Optimize for <3s latency.

<details>
<summary>Click for solution approach</summary>

**Bottlenecks**:
1. VLM inference (2-5s)
2. Tool execution (OCR) (1-2s)
3. Agent overhead (0.5-1s)

**Optimizations**:
```python
# 1. Use vLLM (not transformers)
model = LiteLLMModel(
    model_id="Qwen2.5-VL-7B-Instruct",
    base_url="http://localhost:8001/v1",
    api_key="EMPTY"
)

# 2. Single-shot agent
agent = CodeAgent(
    tools=[PierresPanelTool()],
    model=model,
    max_steps=1,  # No iteration
    verbosity=0   # Silent
)

# 3. Optimize vLLM startup
# vllm serve ... \
#   --dtype float16 \             # FP16 faster than FP32
#   --max-model-len 2048 \        # Smaller context = faster
#   --gpu-memory-utilization 0.9  # Use more GPU memory

# 4. Cache compiled model (PyTorch)
# torch.compile(model, mode="reduce-overhead")

# 5. Batch multiple requests (if applicable)
# Use async patterns in FastAPI
```

**Target latency breakdown**:
- VLM inference: 1-2s (vLLM optimized)
- Tool execution: 0.5-1s (OpenCV + OCR)
- Overhead: <0.5s
- **Total: <3s** ✅

</details>

---

## Bonus Challenge

Create a comprehensive debugging checklist for production.

### Your Checklist

```markdown
## Pre-Deployment Checklist

- [ ] vLLM server running with --enable-tool-calling
- [ ] All tools imported successfully
- [ ] Tool descriptions clear and accurate
- [ ] System prompt constrains tool usage
- [ ] Schema validation implemented
- [ ] Error handling in all tools
- [ ] MLFlow logging configured
- [ ] Health check endpoint working
- [ ] Unit tests passing (mocked VLM)
- [ ] Integration tests passing (real vLLM)
- [ ] Latency < 3s on sample screenshots
- [ ] Memory leaks checked (long-running tests)

## Troubleshooting Guide

1. VLM not calling tools → Check --enable-tool-calling
2. Tool execution fails → Check file paths and dependencies
3. Invalid results → Add schema validation
4. Slow performance → Profile with MLFlow, optimize vLLM
5. Connection timeout → Check vLLM server status
6. Agent hallucinating → Improve system prompt, specify tool names
```

---

## Verification

Test your debugging skills:

```bash
# Break something intentionally, then fix it
python agent-learning/examples/module4_production_wrapper.py

# Common breaks to practice:
# 1. Stop vLLM server → diagnose connection error
# 2. Corrupt image file → handle gracefully
# 3. Remove tool from registry → catch KeyError
# 4. Return invalid data → validation catches it
```

---

## Next Steps

- Apply debugging techniques to production VLMOrchestrator
- Create monitoring dashboard (MLFlow + Grafana)
- Set up alerting for production failures
- Document common issues and solutions
