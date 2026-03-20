# Smolagents Cheatsheet

Quick reference for common Smolagents patterns.

## Installation

```bash
uv add 'smolagents[toolkit,litellm]'
```

## Basic Tool

```python
from smolagents import Tool

class MyTool(Tool):
    name = "my_tool"
    description = "What it does"
    inputs = {"arg": {"type": "string"}}
    output_type = "string"

    def forward(self, arg: str):
        return f"Result: {arg}"
```

## CodeAgent (Recommended)

```python
from smolagents import CodeAgent, LiteLLMModel

model = LiteLLMModel(
    model_id="Qwen2.5-VL-7B-Instruct",
    base_url="http://localhost:8001/v1",
    api_key="EMPTY"
)

agent = CodeAgent(tools=[MyTool()], model=model, verbosity=2)
result = agent.run("Use my_tool on 'hello'")
```

## Vision Tool

```python
from PIL import Image

class VisionTool(Tool):
    name = "analyze_image"
    inputs = {"image_path": {"type": "string"}}
    output_type = "dict"

    def forward(self, image_path: str):
        image = Image.open(image_path)
        return {"width": image.width, "height": image.height}
```

## Error Handling

```python
def forward(self, arg: str):
    try:
        result = process(arg)
        return result
    except Exception as e:
        logger.error(f"Tool failed: {e}")
        return {"error": str(e)}
```

## Multiple Tools

```python
agent = CodeAgent(
    tools=[Tool1(), Tool2(), Tool3()],
    model=model
)
# Agent picks correct tool automatically
```

## Load from Hub

```python
from smolagents import load_tool

tool = load_tool("huggingface-tools/text-to-image")
agent = CodeAgent(tools=[tool], model=model)
```

## Debugging

```python
# Verbose output
agent = CodeAgent(tools=[...], model=model, verbosity=2)

# Inspect generated code
result = agent.run("Task")
print(agent.logs[-1]["code"])
```

## Quick Test

```python
# Minimal example
from smolagents import CodeAgent, InferenceClientModel, Tool

class EchoTool(Tool):
    name = "echo"
    description = "Echo input"
    inputs = {"text": {"type": "string"}}
    output_type = "string"
    def forward(self, text: str):
        return text

model = InferenceClientModel("Qwen/Qwen2.5-VL-7B-Instruct")
agent = CodeAgent(tools=[EchoTool()], model=model)
print(agent.run("Echo 'hello world'"))
```
