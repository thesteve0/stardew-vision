# Module 2: Smolagents Basics

**Duration**: 2-3 hours
**Prerequisites**: Module 1 completed, basic Python OOP
**Example Code**: [`examples/module2_smolagents_basic.py`](../examples/module2_smolagents_basic.py)

---

## Learning Objectives

By the end of this module, you will:

- ✅ Install and configure Smolagents
- ✅ Create custom `Tool` classes
- ✅ Understand `CodeAgent` vs `ToolCallingAgent`
- ✅ Run your first agent with a transformers backend
- ✅ See how Smolagents automates what you did manually in Module 1

---

## Why Smolagents?

After doing manual dispatch in Module 1, you might wonder: *"Why not just keep doing it manually?"*

**Here's why frameworks matter**:

### What You Wrote Manually (Module 1)

```python
# Parse VLM response
tool_call = vlm_response["tool_call"]
tool_name = tool_call["function"]["name"]
arguments = json.loads(tool_call["function"]["arguments"])

# Validate tool exists
if tool_name not in TOOL_REGISTRY:
    raise ValueError(f"Unknown tool: {tool_name}")

# Dispatch
result = TOOL_REGISTRY[tool_name](**arguments)
```

That's **~10 lines** every time you want to call a tool.

### What Smolagents Does

```python
agent = CodeAgent(tools=[MyTool()], model=model)
result = agent.run("Extract from screenshot")
```

That's **2 lines**. Smolagents handles:
- ✅ Tool definition generation (from Tool class)
- ✅ Prompt construction (system prompt + user message)
- ✅ VLM invocation (with retries, error handling)
- ✅ Response parsing (JSON or Python code)
- ✅ Tool dispatch (lookup and execution)
- ✅ Multi-step reasoning (if task needs multiple tools)
- ✅ Error recovery (retry on failures)

**The win**: You focus on **what** to do, not **how** to dispatch.

---

## Smolagents Design Philosophy

Smolagents was designed specifically for **VLM (Vision-Language Model)** use cases:

### 1. VLM-First Design

**Unlike LangChain** (retrofitted for vision):
- ✅ First-class support for images, video, audio
- ✅ Optimized for multi-modal prompts
- ✅ Vision model-specific optimizations

**Example**:
```python
# Smolagents handles images natively
agent.run("Analyze this screenshot", image="/path/to/file.png")

# LangChain requires manual image encoding
# image_data = encode_image(image_path)
# agent.run(f"Analyze this: data:image/png;base64,{image_data}")
```

### 2. Model-Agnostic

Works with:
- ✅ Local models (Qwen, Llama, SmolVLM)
- ✅ OpenAI (GPT-4V, GPT-4o)
- ✅ Anthropic (Claude Sonnet)
- ✅ HuggingFace Inference API
- ✅ Any OpenAI-compatible endpoint (vLLM, TGI)

**Same code, different backend**:
```python
# Local vLLM
model = LiteLLMModel(model_id="Qwen2.5-VL", base_url="http://localhost:8001/v1")

# OpenAI
model = LiteLLMModel(model_id="gpt-4o", api_key=os.getenv("OPENAI_API_KEY"))

# Same agent code works with both!
agent = CodeAgent(tools=[...], model=model)
```

### 3. CodeAgent Paradigm

**ToolCallingAgent** (JSON-based, like most frameworks):
```json
{
  "tool": "my_tool",
  "arguments": {"x": 1, "y": 2}
}
```

**CodeAgent** (Python-based, unique to Smolagents):
```python
x = 1
y = 2
result = my_tool(x=x, y=y)
print(result)
```

**Why Python > JSON?**
- ✅ Type-checked by Python runtime (catches errors early)
- ✅ Composable (can chain tools: `y = tool1(x); z = tool2(y)`)
- ✅ Debuggable (Python stack traces vs JSON parse errors)
- ✅ Self-correcting (VLM can fix syntax errors)

See diagram: [`diagrams/codeagent-execution.txt`](../diagrams/codeagent-execution.txt)

### 4. Minimal Complexity

**Smolagents**: ~1,000 lines of core code
**LangChain**: ~50,000+ lines
**CrewAI**: ~10,000 lines

**Implication**: You can read and understand the entire Smolagents codebase in an afternoon.

When something breaks, you can debug it. When you need custom behavior, you can fork/extend it.

---

## Installation

```bash
# Install with all backends
uv add 'smolagents[toolkit,litellm]'

# Verify installation
python -c "import smolagents; print(smolagents.__version__)"
```

**Extras explained**:
- `toolkit`: Includes default tools (web search, Python REPL, etc.)
- `litellm`: LiteLLM backend for OpenAI-compatible endpoints (vLLM, TGI)

**If you get import errors**:
```bash
# Reinstall with correct extras
uv remove smolagents
uv add 'smolagents[toolkit,litellm]'
```

---

## Core Concepts

### Concept 1: Tool Classes

In Module 1, you had two separate things:
- Tool definition (JSON)
- Tool implementation (function)

In Smolagents, they're **unified** in a `Tool` class:

```python
from smolagents import Tool

class MyTool(Tool):
    # METADATA (replaces JSON definition)
    name = "my_tool"
    description = "What this tool does"
    inputs = {
        "param1": {"type": "string", "description": "..."},
        "param2": {"type": "integer", "description": "..."}
    }
    output_type = "dict"  # str, dict, Image, etc.

    # IMPLEMENTATION (replaces function in registry)
    def forward(self, param1: str, param2: int):
        """This is called when tool is invoked."""
        result = do_something(param1, param2)
        return result
```

**Benefits**:
- ✅ Single source of truth (metadata + implementation together)
- ✅ Auto-generated tool definitions (Smolagents converts to JSON)
- ✅ Type hints in `forward()` method (IDE autocomplete!)
- ✅ Reusable (import and share across projects)

**Comparison to Module 1**:

| Module 1 (Manual)                     | Module 2 (Smolagents)           |
|---------------------------------------|---------------------------------|
| JSON definition + function in registry| Single Tool class               |
| Manually keep in sync                 | Auto-sync (name from class attr)|
| No IDE support                        | Type hints in forward()         |

### Concept 2: Models

Smolagents supports multiple model backends via a unified interface:

```python
# InferenceClientModel: HuggingFace transformers or Inference API
from smolagents import InferenceClientModel
model = InferenceClientModel(model_id="Qwen/Qwen2.5-VL-7B-Instruct")

# LiteLLMModel: OpenAI-compatible endpoints (vLLM, TGI, OpenAI, etc.)
from smolagents import LiteLLMModel
model = LiteLLMModel(
    model_id="Qwen2.5-VL-7B-Instruct",
    base_url="http://localhost:8001/v1",
    api_key="EMPTY"
)

# OpenAIServerModel: OpenAI SDK directly
from smolagents import OpenAIServerModel
model = OpenAIServerModel(model_id="gpt-4o", api_key="sk-...")
```

**When to use which**:
- `InferenceClientModel`: Quick testing, no vLLM setup needed (slower)
- `LiteLLMModel`: Production, local vLLM or OpenShift AI (fast, recommended)
- `OpenAIServerModel`: Using actual OpenAI API

**For this tutorial**: We start with `InferenceClientModel` (Module 2), then switch to `LiteLLMModel` with vLLM (Module 3).

### Concept 3: CodeAgent vs ToolCallingAgent

**Two agent types** in Smolagents:

#### ToolCallingAgent (JSON-based)

```python
from smolagents import ToolCallingAgent

agent = ToolCallingAgent(tools=[...], model=model)
result = agent.run("Do something")
```

**How it works**:
1. VLM returns JSON: `{"tool": "my_tool", "arguments": {...}}`
2. Agent parses JSON
3. Agent calls tool

**Pros**: Simple, widely compatible
**Cons**: Less composable, weaker type safety

#### CodeAgent (Python-based) ⭐ Recommended

```python
from smolagents import CodeAgent

agent = CodeAgent(tools=[...], model=model)
result = agent.run("Do something")
```

**How it works**:
1. VLM returns Python code: `result = my_tool(x=1, y=2)`
2. Agent executes code in sandbox
3. Agent returns result

**Pros**: Composable, type-safe, self-correcting
**Cons**: Requires code execution sandbox

**We use CodeAgent** for this project. See full comparison: [`diagrams/codeagent-execution.txt`](../diagrams/codeagent-execution.txt)

---

## Code Walkthrough

Now let's walk through `examples/module2_smolagents_basic.py` line-by-line.

### Part 1: Import Smolagents (Lines 7-10)

```python
from smolagents import CodeAgent, Tool, InferenceClientModel
from PIL import Image
import json
```

**New imports**:
- `Tool`: Base class for creating tools
- `CodeAgent`: Agent that generates Python code
- `InferenceClientModel`: HuggingFace transformers backend

### Part 2: Create Tool Class (Lines 12-35)

```python
class CropPierresPanelTool(Tool):
    """
    Smolagents Tool wrapper for crop_pierres_detail_panel.

    Tool classes define:
    - name: Tool identifier (matches function name)
    - description: What the tool does (shown to VLM)
    - inputs: Parameter schema (type, description)
    - output_type: Return type (str, dict, Image, etc.)
    - forward(): Actual implementation
    """
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
        """Execute the extraction tool."""
        from stardew_vision.tools import crop_pierres_detail_panel

        print(f"[CropPierresPanelTool] Executing on {image_path}")
        result = crop_pierres_detail_panel(image_path)
        print(f"[CropPierresPanelTool] Extraction successful: {result}")

        return result
```

**Line-by-line**:
- **Line 12**: Class inherits from `Tool` (required)
- **Line 22**: `name` - Must match what VLM will call
- **Line 23**: `description` - Shown to VLM, helps it decide when to use tool
- **Lines 25-30**: `inputs` - JSON schema for parameters (same format as Module 1!)
- **Line 32**: `output_type` - What this tool returns (`str`, `dict`, `Image`, etc.)
- **Line 34**: `forward()` - The actual implementation (replaces function from Module 1)
- **Line 37**: Import real tool (lazy import, only when called)
- **Lines 39-41**: Logging (same as Module 1, but in class method)

**Comparison to Module 1**:

Module 1 (Manual):
```python
# Definition (JSON)
TOOL_DEFINITIONS = [{"type": "function", "function": {"name": "...", ...}}]

# Implementation (function)
def crop_pierres_detail_panel(image_path: str) -> dict:
    ...

# Registry (dict)
TOOL_REGISTRY = {"crop_pierres_detail_panel": crop_pierres_detail_panel}
```

Module 2 (Smolagents):
```python
# Everything in one class!
class CropPierresPanelTool(Tool):
    name = "crop_pierres_detail_panel"
    description = "..."
    inputs = {...}
    output_type = "dict"

    def forward(self, image_path: str):
        ...
```

**The win**: Definition and implementation are in sync automatically.

### Part 3: Initialize Model (Lines 45-51)

```python
print("Loading model (InferenceClientModel)...")
model = InferenceClientModel(
    model_id="Qwen/Qwen2.5-VL-7B-Instruct"
)
print("Model loaded!")
```

**What happens**:
- Smolagents connects to HuggingFace Inference API (or downloads model)
- First run may download model weights (~15 GB for Qwen2.5-VL-7B)
- Subsequent runs use cached model

**Model ID format**: `{org}/{repo}` from HuggingFace Hub

**Note**: This is **not** using vLLM yet. That's Module 3. This is for quick testing.

### Part 4: Create Tools List (Line 53)

```python
tools = [CropPierresPanelTool()]
```

**Why a list?**
- Agent can have multiple tools
- VLM sees all tools, picks the right one
- Example: `[CropPierresPanelTool(), GetScreenTypeTool(), ExtractTVDialogTool()]`

**Instance vs class**:
```python
# WRONG
tools = [CropPierresPanelTool]  # Class, not instance

# RIGHT
tools = [CropPierresPanelTool()]  # Instance (note the parentheses)
```

### Part 5: Initialize CodeAgent (Lines 55-61)

```python
print("Initializing CodeAgent...")
agent = CodeAgent(
    tools=tools,
    model=model,
    add_base_tools=False,  # Don't add default DuckDuckGo, etc.
    max_steps=3,           # Limit iterations
    verbosity=2            # Show reasoning
)
print("Agent initialized!")
```

**Parameters explained**:
- `tools`: List of Tool instances
- `model`: Model backend (InferenceClientModel, LiteLLMModel, etc.)
- `add_base_tools`: If `True`, adds web search, Python REPL, etc. (we don't need these)
- `max_steps`: Max reasoning iterations (prevents infinite loops)
- `verbosity`: 0=silent, 1=minimal, 2=detailed (shows VLM reasoning)

**What CodeAgent does during init**:
1. Converts Tool classes to JSON tool definitions
2. Prepares system prompt with available tools
3. Sets up code execution sandbox
4. Connects to model backend

### Part 6: Run Agent (Lines 65-71)

```python
image_path = "/workspaces/stardew-vision/tests/fixtures/pierre_shop_001.png"

print(f"Running agent on: {image_path}")
print("-" * 80)

result = agent.run(
    f"Extract all item information from the Pierre's General Store screenshot at {image_path}. "
    f"Use the crop_pierres_detail_panel tool."
)
```

**The `agent.run()` method**:
- Takes a natural language prompt
- Returns extracted data

**What happens inside** (see [`diagrams/codeagent-execution.txt`](../diagrams/codeagent-execution.txt)):
1. Agent sends prompt + tool definitions to VLM
2. VLM generates Python code: `result = crop_pierres_detail_panel(image_path="/path/...")`
3. Agent executes code in sandbox
4. Code calls `CropPierresPanelTool.forward()`
5. Tool extracts data, returns dict
6. Agent returns final result

**With `verbosity=2`, you'll see**:
```
[Agent] Step 1/3
[VLM] Generating code...
[Agent] Executing:
  image_path = "/workspaces/stardew-vision/tests/fixtures/pierre_shop_001.png"
  result = crop_pierres_detail_panel(image_path=image_path)
  print(result)
[CropPierresPanelTool] Executing on /workspaces/stardew-vision/tests/fixtures/pierre_shop_001.png
[CropPierresPanelTool] Extraction successful: {"name": "Parsnip", ...}
[Agent] Step 1 complete
```

### Part 7: Display Result (Lines 73-82)

```python
print("-" * 80)
print()
print("Agent Result:")
print(json.dumps(result, indent=2))
print()

print("✅ Module 2 Complete!")
print("You now understand:")
print("  - How to create Smolagents Tool classes")
print("  - How CodeAgent writes Python code to call tools")
print("  - How InferenceClientModel works with HF models")
```

---

## Hands-On Activity

### Checkpoint 1: Run the Example

```bash
# From project root
cd /workspaces/stardew-vision

# Run Module 2 example
python agent-learning/examples/module2_smolagents_basic.py
```

**First run**: May download Qwen2.5-VL-7B (~15 GB), takes 5-10 minutes

**Expected output**:
```
================================================================================
MODULE 2: SMOLAGENTS BASICS
================================================================================

Loading model (InferenceClientModel)...
Model loaded!

Initializing CodeAgent...
Agent initialized!

Running agent on: /workspaces/stardew-vision/tests/fixtures/pierre_shop_001.png
--------------------------------------------------------------------------------
[Agent] Step 1/3
[VLM] Generating code...
[Agent] Executing:
  image_path = "/workspaces/stardew-vision/tests/fixtures/pierre_shop_001.png"
  result = crop_pierres_detail_panel(image_path=image_path)
  print(result)
[CropPierresPanelTool] Executing on /workspaces/stardew-vision/tests/fixtures/pierre_shop_001.png
[CropPierresPanelTool] Extraction successful: {...}
--------------------------------------------------------------------------------

Agent Result:
{
  "name": "Parsnip",
  "description": "A spring vegetable. Still loved by many.",
  "price_per_unit": 20,
  "quantity_selected": 5,
  "total_cost": 100
}

✅ Module 2 Complete!
```

**If it fails**:
- Check internet connection (needs HF Hub access)
- Verify Smolagents installed: `python -c "import smolagents"`
- Check PYTHONPATH includes `/workspaces/stardew-vision/src`

### Checkpoint 2: Experiment with Parameters

Modify the example and see what changes:

**Test 1: Silent mode**
```python
agent = CodeAgent(..., verbosity=0)  # No reasoning output
```

**Test 2: Single-step**
```python
agent = CodeAgent(..., max_steps=1)  # Only one reasoning iteration
```

**Test 3: Add base tools**
```python
agent = CodeAgent(..., add_base_tools=True)  # Web search, Python REPL, etc.
```

What tools are available now?
```python
print([tool.name for tool in agent.tools])
```

**Test 4: Different prompt**
```python
result = agent.run("What's in this screenshot? Extract details.")
# Vaguer prompt - does VLM still pick the right tool?
```

### Checkpoint 3: Create a Second Tool

Add a tool that identifies screen type:

```python
class GetScreenTypeTool(Tool):
    name = "get_screen_type"
    description = "Identify which UI panel is shown in a Stardew Valley screenshot"

    inputs = {
        "image_path": {
            "type": "string",
            "description": "Path to the screenshot file"
        }
    }

    output_type = "dict"

    def forward(self, image_path: str):
        """Mock implementation - always returns pierre_shop for now."""
        # In production, this would use a classifier
        return {"screen_type": "pierre_shop"}

# Add to tools list
tools = [CropPierresPanelTool(), GetScreenTypeTool()]

# Run agent with both tools
agent = CodeAgent(tools=tools, model=model, verbosity=2)
result = agent.run("First identify the screen type, then extract details from the screenshot")
```

**What to observe**:
- Does VLM call both tools?
- In what order?
- How does it use the screen_type result?

**Full exercise**: [`exercises/exercise2_agent_config.md`](../exercises/exercise2_agent_config.md)

---

## Key Patterns

### Pattern 1: Tool Class Structure

**Always include**:
```python
class MyTool(Tool):
    name = "unique_name"          # Required
    description = "Clear desc"    # Required (helps VLM)
    inputs = {...}                # Required (JSON schema)
    output_type = "dict"          # Required

    def forward(self, **kwargs):  # Required
        # Implementation here
        return result
```

### Pattern 2: Lazy Imports in forward()

**Don't import at top of file**:
```python
# WRONG
from heavy_library import expensive_function

class MyTool(Tool):
    def forward(self):
        return expensive_function()
```

**Do import inside forward()**:
```python
# RIGHT
class MyTool(Tool):
    def forward(self):
        from heavy_library import expensive_function
        return expensive_function()
```

**Why?**
- Tool definitions are sent to VLM (metadata only)
- Heavy imports slow down tool registration
- Import only when tool is actually called

### Pattern 3: Tool Instantiation

```python
# Create instances, not classes
tools = [Tool1(), Tool2(), Tool3()]  # ✅

# NOT
tools = [Tool1, Tool2, Tool3]  # ❌ Missing parentheses
```

---

## Common Pitfalls

### Pitfall 1: Forgetting to Instantiate Tools

**Error**:
```python
tools = [CropPierresPanelTool]  # Class, not instance
agent = CodeAgent(tools=tools, model=model)
# TypeError: 'type' object is not iterable
```

**Fix**:
```python
tools = [CropPierresPanelTool()]  # Add parentheses!
```

### Pitfall 2: Missing Model Backend

**Error**:
```python
from smolagents import CodeAgent, Tool
agent = CodeAgent(tools=[MyTool()])  # No model!
# TypeError: missing required argument: 'model'
```

**Fix**:
```python
from smolagents import CodeAgent, Tool, InferenceClientModel
model = InferenceClientModel(model_id="Qwen/Qwen2.5-VL-7B-Instruct")
agent = CodeAgent(tools=[MyTool()], model=model)
```

### Pitfall 3: Vague Tool Descriptions

VLM uses descriptions to decide which tool to call:

**Bad**:
```python
description = "Does stuff with images"  # Too vague!
```

**Good**:
```python
description = "Extract item details from Pierre's General Store detail panel in a Stardew Valley screenshot"
```

### Pitfall 4: Incorrect Input Schema

**Wrong types**:
```python
inputs = {
    "image_path": {"type": "file"}  # Not a valid JSON schema type!
}
```

**Valid JSON schema types**: `string`, `integer`, `number`, `boolean`, `object`, `array`, `null`

**Fix**:
```python
inputs = {
    "image_path": {"type": "string", "description": "Path to image file"}
}
```

---

## Key Takeaways

### 1. Tool Classes Unify Definition + Implementation

Module 1: Definition (JSON) + Implementation (function) + Registry (dict)
Module 2: One Tool class contains everything

### 2. CodeAgent Automates Dispatch

Module 1: You parse JSON, validate, look up, call
Module 2: Agent does all of this automatically

### 3. VLM Writes Python Code (Not JSON)

This enables:
- Type checking (Python runtime)
- Composability (chain tools in code)
- Self-correction (VLM can fix syntax errors)

### 4. Same Pattern, Higher Abstraction

The underlying mechanism hasn't changed:
1. VLM gets tool definitions
2. VLM decides which tool to use
3. Tool is called with arguments
4. Result is returned

Smolagents just automates steps 2-4.

---

## What's Next?

**Current state**:
- ✅ Tool classes (cleaner than manual definitions)
- ✅ CodeAgent (automated dispatch)
- ✅ InferenceClientModel (HuggingFace backend)

**Limitations**:
- ❌ No local vLLM (slower, requires internet)
- ❌ No production-grade error handling
- ❌ No observability (logging, metrics)

**Module 3** fixes these:
- Use vLLM for faster local inference
- Use LiteLLMModel for OpenAI-compatible endpoints
- Same agent code, just swap model backend

**Module 4** adds production features:
- VLMOrchestrator wrapper class
- Error handling and validation
- MLFlow logging
- Unit tests with mocking

---

## Summary

You now understand:

1. ✅ **Why Smolagents** - Automates tedious dispatch logic
2. ✅ **Tool classes** - Single source of truth for definition + implementation
3. ✅ **CodeAgent** - Generates Python code (not JSON)
4. ✅ **Model backends** - InferenceClientModel for quick testing
5. ✅ **Agent.run()** - Natural language → tool execution → result

**The abstraction ladder**:
- Module 1: Raw JSON + manual dispatch
- Module 2: Tool classes + CodeAgent
- Module 3: Add vLLM for production speed
- Module 4: Add error handling + observability

---

## Additional Resources

**Code**:
- Full example: [`examples/module2_smolagents_basic.py`](../examples/module2_smolagents_basic.py)
- Exercise: [`exercises/exercise2_agent_config.md`](../exercises/exercise2_agent_config.md)

**Diagrams**:
- [`diagrams/codeagent-execution.txt`](../diagrams/codeagent-execution.txt) - How CodeAgent works
- [`diagrams/tool-calling-flow.txt`](../diagrams/tool-calling-flow.txt) - General flow

**Official Docs**:
- [Smolagents Guided Tour](https://huggingface.co/docs/smolagents/guided_tour)
- [Tool Conceptual Guide](https://huggingface.co/docs/smolagents/main/en/conceptual_guides/tools)
- [Building Good Agents](https://huggingface.co/docs/smolagents/tutorials/building_good_agents)

**Related**:
- [`docs/smolagents-quickstart.md`](../docs/smolagents-quickstart.md) - Quick reference
- [`docs/framework-decision.md`](../docs/framework-decision.md) - Why Smolagents over alternatives

---

**Ready for Module 3?** → [`module3-vllm-integration.md`](module3-vllm-integration.md)

Learn how to connect Smolagents to vLLM for production-grade serving!
