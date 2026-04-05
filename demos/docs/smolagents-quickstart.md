# Smolagents Quick Reference

Quick reference guide for HuggingFace Smolagents framework.

## Installation

```bash
# Basic
uv add smolagents

# With toolkit (DuckDuckGoSearch, etc.)
uv add 'smolagents[toolkit]'

# With transformers backend
uv add 'smolagents[transformers]'

# With LiteLLM backend (vLLM, OpenAI, Anthropic)
uv add 'smolagents[litellm]'

# Recommended for Stardew Vision
uv add 'smolagents[toolkit,litellm]'
```

## Core Classes

### Tool

Custom tool that agents can call.

```python
from smolagents import Tool

class MyTool(Tool):
    name = "my_tool"
    description = "What this tool does"
    inputs = {
        "arg1": {"type": "string", "description": "First argument"},
        "arg2": {"type": "integer", "description": "Second argument"}
    }
    output_type = "dict"  # or "string", "image", etc.

    def forward(self, arg1: str, arg2: int):
        """Execute the tool."""
        # Your implementation
        return {"result": f"{arg1}_{arg2}"}
```

### CodeAgent

Agent that writes Python code to call tools.

```python
from smolagents import CodeAgent, InferenceClientModel

# Initialize model
model = InferenceClientModel(model_id="Qwen/Qwen2.5-VL-7B-Instruct")

# Create agent
agent = CodeAgent(
    tools=[MyTool()],
    model=model,
    add_base_tools=False,  # Don't add default tools
    max_steps=3,           # Max reasoning iterations
    verbosity=2            # 0=silent, 1=normal, 2=verbose
)

# Run agent
result = agent.run("Use my_tool to process 'hello' and 42")
```

**How it works**:
- Agent generates Python code to call tools
- Code is executed in sandboxed environment
- More robust than JSON function calling

### ToolCallingAgent

Agent that uses JSON function calling (like OpenAI).

```python
from smolagents import ToolCallingAgent

agent = ToolCallingAgent(
    tools=[MyTool()],
    model=model,
    max_steps=3
)

result = agent.run("Same prompt as CodeAgent")
```

**Difference from CodeAgent**:
- Uses JSON instead of Python code
- Compatible with more models
- Less flexible than CodeAgent

## Model Backends

### InferenceClientModel (Transformers)

Load model from HuggingFace Hub or local path.

```python
from smolagents import InferenceClientModel

model = InferenceClientModel(
    model_id="Qwen/Qwen2.5-VL-7B-Instruct"
)
```

**Pros**:
- Simple, downloads automatically
- Works with any HF model

**Cons**:
- Slower than vLLM
- Not production-ready

### LiteLLMModel (vLLM, OpenAI, Anthropic)

Universal backend for any OpenAI-compatible API.

```python
from smolagents import LiteLLMModel

# For vLLM
model = LiteLLMModel(
    model_id="Qwen2.5-VL-7B-Instruct",
    base_url="http://localhost:8001/v1",
    api_key="EMPTY"
)

# For OpenAI API
model = LiteLLMModel(
    model_id="gpt-4o",
    api_key="sk-..."
)

# For Anthropic API
model = LiteLLMModel(
    model_id="claude-sonnet-4",
    api_key="sk-ant-..."
)
```

**Pros**:
- Production-ready (vLLM)
- Works with any OpenAI-compatible endpoint
- Faster inference

**Cons**:
- Requires running server (vLLM)
- May require API key (OpenAI, Anthropic)

## Tool Types

### Built-in Tools

```python
from smolagents import DuckDuckGoSearchTool, VisitWebpageTool

tools = [
    DuckDuckGoSearchTool(),
    VisitWebpageTool()
]
```

**Available tools** (with `[toolkit]`):
- `DuckDuckGoSearchTool`: Web search
- `VisitWebpageTool`: Fetch webpage content
- `ImageGenerationTool`: Generate images (via model)

### Custom Tools

Create your own tools by subclassing `Tool`:

```python
from smolagents import Tool
from PIL import Image

class ImageAnalysisTool(Tool):
    name = "analyze_image"
    description = "Analyze an image and return description"
    inputs = {
        "image_path": {"type": "string", "description": "Path to image"}
    }
    output_type = "string"

    def forward(self, image_path: str) -> str:
        image = Image.open(image_path)
        # Your analysis logic
        return f"Image size: {image.size}"
```

### Hub Tools

Share and load tools from HuggingFace Hub:

```python
from smolagents import load_tool

# Load from Hub
tool = load_tool("huggingface-tools/text-to-image")

# Push to Hub
my_tool = MyTool()
my_tool.push_to_hub("username/my-tool")
```

## Agent Execution

### Running Agents

```python
# Run with prompt
result = agent.run("Extract data from screenshot.png")

# Run with context
result = agent.run(
    "Analyze this",
    context={"file_path": "/path/to/file"}
)

# Run with image
from PIL import Image
image = Image.open("screenshot.png")
result = agent.run("What's in this image?", image=image)
```

### Multi-Step Reasoning

Agents can iterate to solve complex tasks:

```python
agent = CodeAgent(
    tools=[...],
    model=model,
    max_steps=5  # Allow up to 5 reasoning steps
)

# Agent will:
# 1. Reason about task
# 2. Generate code to call tools
# 3. Execute code
# 4. Observe result
# 5. Repeat if needed
```

### Stopping Criteria

Agents stop when:
- Task is complete
- `max_steps` reached
- Error occurs
- Agent returns final answer

## Advanced Features

### Managed Agents (Multi-Agent)

Create hierarchical agent systems:

```python
from smolagents import CodeAgent, ManagedAgent

# Create sub-agent
extractor = CodeAgent(tools=[ExtractionTool()], model=model)

# Create manager agent with sub-agent as tool
manager = CodeAgent(
    tools=[],
    model=model,
    managed_agents=[ManagedAgent(extractor, "extractor")]
)

# Manager can delegate to extractor
result = manager.run("Extract data using the extractor agent")
```

### Sandboxed Execution

Secure code execution in isolated environments:

```python
from smolagents import CodeAgent, E2BExecutor

# Use E2B sandbox
agent = CodeAgent(
    tools=[...],
    model=model,
    executor=E2BExecutor()  # or ModalExecutor, BlaxelExecutor
)
```

**Options**:
- `LocalExecutor`: Local Python (default, not sandboxed)
- `E2BExecutor`: E2B cloud sandbox
- `ModalExecutor`: Modal serverless
- `BlaxelExecutor`: Blaxel secure interpreter

### Custom System Prompt

```python
agent = CodeAgent(
    tools=[...],
    model=model,
    system_prompt="You are an accessibility assistant. Always prioritize clarity."
)
```

### Planning Interval

Control when agent generates execution plan:

```python
agent = CodeAgent(
    tools=[...],
    model=model,
    planning_interval=2  # Replan every 2 steps
)
```

## Debugging

### Verbosity Levels

```python
agent = CodeAgent(
    tools=[...],
    model=model,
    verbosity=0  # Silent
    # verbosity=1  # Normal (default)
    # verbosity=2  # Verbose (show all reasoning)
)
```

### Logging

Enable detailed logging:

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("smolagents")
logger.setLevel(logging.DEBUG)
```

### Inspecting Generated Code

```python
# CodeAgent stores generated code
result = agent.run("Task")
print("Generated code:")
print(agent.logs[-1]["code"])  # Last generated code
```

## Common Patterns

### Pattern 1: VLM with Vision Tool

```python
from smolagents import CodeAgent, LiteLLMModel, Tool
from PIL import Image

class VisionTool(Tool):
    name = "analyze_screenshot"
    description = "Analyze screenshot and extract data"
    inputs = {"image_path": {"type": "string"}}
    output_type = "dict"

    def forward(self, image_path: str):
        # Your vision logic
        return {"detected": "data"}

model = LiteLLMModel(
    model_id="Qwen2.5-VL-7B-Instruct",
    base_url="http://localhost:8001/v1",
    api_key="EMPTY"
)

agent = CodeAgent(tools=[VisionTool()], model=model)
result = agent.run("Analyze /path/to/screenshot.png")
```

### Pattern 2: Tool with External API

```python
class WeatherTool(Tool):
    name = "get_weather"
    description = "Get current weather for a location"
    inputs = {"location": {"type": "string"}}
    output_type = "dict"

    def forward(self, location: str):
        import requests
        response = requests.get(
            f"https://api.weather.com/v1/current?location={location}"
        )
        return response.json()
```

### Pattern 3: Tool Chaining

```python
class ExtractTool(Tool):
    name = "extract_text"
    inputs = {"image_path": {"type": "string"}}
    output_type = "string"

    def forward(self, image_path: str):
        # OCR logic
        return "extracted text"

class SummarizeTool(Tool):
    name = "summarize_text"
    inputs = {"text": {"type": "string"}}
    output_type = "string"

    def forward(self, text: str):
        # Summarization logic
        return "summary"

# Agent can chain tools
agent = CodeAgent(tools=[ExtractTool(), SummarizeTool()], model=model)
result = agent.run("Extract text from image.png and summarize it")

# Agent generates:
# text = extract_text(image_path="image.png")
# summary = summarize_text(text=text)
# print(summary)
```

## Error Handling

### Tool Errors

```python
class SafeTool(Tool):
    def forward(self, arg: str):
        try:
            # Your logic
            return {"result": arg}
        except Exception as e:
            # Log error
            logger.error(f"Tool failed: {e}")
            # Re-raise or return error dict
            return {"error": str(e)}
```

### Agent Errors

```python
try:
    result = agent.run("Task")
except Exception as e:
    print(f"Agent failed: {e}")
    # Handle error (retry, fallback, etc.)
```

## CLI Tools

### smolagent

Interactive agent REPL:

```bash
# Start interactive session
smolagent

# Specify model
smolagent --model "Qwen/Qwen2.5-VL-7B-Instruct"

# Add tools
smolagent --tools search,web
```

### webagent

Web-based agent interface:

```bash
# Start Gradio UI
webagent

# Specify model
webagent --model "gpt-4o"
```

## Configuration

### Environment Variables

```bash
# HuggingFace token (for private models)
export HF_TOKEN="hf_..."

# Model cache directory
export HF_HOME="/path/to/cache"

# LiteLLM settings
export LITELLM_LOG="DEBUG"
```

## Resources

**Official Documentation**:
- [Main Docs](https://huggingface.co/docs/smolagents/index)
- [Guided Tour](https://huggingface.co/docs/smolagents/guided_tour)
- [Building Good Agents](https://huggingface.co/docs/smolagents/tutorials/building_good_agents)
- [Tools Guide](https://huggingface.co/docs/smolagents/main/en/conceptual_guides/tools)

**API Reference**:
- [CodeAgent](https://huggingface.co/docs/smolagents/reference/agents#smolagents.CodeAgent)
- [ToolCallingAgent](https://huggingface.co/docs/smolagents/reference/agents#smolagents.ToolCallingAgent)
- [Tool](https://huggingface.co/docs/smolagents/reference/tools#smolagents.Tool)

**Examples**:
- [HuggingFace Hub](https://huggingface.co/spaces?search=smolagents)
- [GitHub Examples](https://github.com/huggingface/smolagents/tree/main/examples)

---

**Quick Start Template**:

```python
from smolagents import CodeAgent, LiteLLMModel, Tool

# 1. Define tool
class MyTool(Tool):
    name = "my_tool"
    description = "What it does"
    inputs = {"arg": {"type": "string"}}
    output_type = "string"

    def forward(self, arg: str):
        return f"Processed: {arg}"

# 2. Initialize model
model = LiteLLMModel(
    model_id="Qwen2.5-VL-7B-Instruct",
    base_url="http://localhost:8001/v1",
    api_key="EMPTY"
)

# 3. Create agent
agent = CodeAgent(tools=[MyTool()], model=model)

# 4. Run
result = agent.run("Use my_tool on 'hello'")
print(result)
```
