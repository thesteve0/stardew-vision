# Exercise 1: Tool Creation

**Objective**: Create custom tools in both OpenAI format and Smolagents format.

**Time**: 30-45 minutes

**Prerequisites**: Completed Module 1-2

---

## Part 1: OpenAI Format Tool Definition

Create a tool definition in OpenAI function-calling format for a new extraction function.

### Task

Create a tool definition for `get_screen_type` that identifies which UI panel is shown in a screenshot.

**Function signature**:
```python
def get_screen_type(image_path: str) -> dict:
    """
    Identify which UI panel is shown in screenshot.

    Args:
        image_path: Path to screenshot

    Returns:
        {"screen_type": "pierre_shop" | "tv_dialog" | "inventory" | "unknown"}
    """
    pass
```

### Your Implementation

1. Create the OpenAI tool definition (JSON):

```python
SCREEN_TYPE_TOOL = {
    "type": "function",
    "function": {
        "name": "get_screen_type",
        "description": "TODO: Write description",
        "parameters": {
            # TODO: Define parameters
        }
    }
}
```

2. Add to `TOOL_REGISTRY`:

```python
TOOL_REGISTRY = {
    "crop_pierres_detail_panel": crop_pierres_detail_panel,
    "get_screen_type": get_screen_type,  # Add this
}
```

3. Test with manual dispatch:

```python
from examples.module1_manual_dispatch import dispatch_tool

result = dispatch_tool("get_screen_type", {"image_path": "screenshot.png"})
print(result)
```

### Hints

- `description` should explain what the tool does and when to use it
- `parameters` must include `image_path` as a required field
- `type` for image_path should be `"string"`

### Solution

<details>
<summary>Click to reveal solution</summary>

```python
SCREEN_TYPE_TOOL = {
    "type": "function",
    "function": {
        "name": "get_screen_type",
        "description": "Identify which UI panel is shown in a Stardew Valley screenshot (pierre_shop, tv_dialog, inventory, or unknown)",
        "parameters": {
            "type": "object",
            "properties": {
                "image_path": {
                    "type": "string",
                    "description": "Path to the screenshot file to analyze"
                }
            },
            "required": ["image_path"]
        }
    }
}

def get_screen_type(image_path: str) -> dict:
    """Mock implementation - replace with real logic."""
    # In reality, you'd use template matching or VLM classification
    return {"screen_type": "pierre_shop"}
```

</details>

---

## Part 2: Smolagents Tool Class

Convert the same function to a Smolagents `Tool` class.

### Task

Create a Smolagents `Tool` class for `get_screen_type`.

### Your Implementation

```python
from smolagents import Tool

class ScreenTypeTool(Tool):
    """Identify which UI panel is shown in screenshot."""

    name = "get_screen_type"
    description = "TODO: Write description"

    inputs = {
        # TODO: Define inputs
    }

    output_type = "TODO: What type does it return?"

    def forward(self, image_path: str):
        """Execute the tool."""
        # TODO: Implement
        pass
```

### Test Your Tool

```python
from smolagents import CodeAgent, InferenceClientModel

tool = ScreenTypeTool()

# Test manually
result = tool.forward("screenshot.png")
print(result)

# Test with agent (requires model)
model = InferenceClientModel("Qwen/Qwen2.5-VL-7B-Instruct")
agent = CodeAgent(tools=[tool], model=model)
result = agent.run("What type of screen is shown in screenshot.png?")
print(result)
```

### Hints

- `output_type` should be `"dict"` (returns a dictionary)
- `inputs` uses different format than OpenAI (see Module 2)
- `forward()` is where you put your actual implementation

### Solution

<details>
<summary>Click to reveal solution</summary>

```python
from smolagents import Tool

class ScreenTypeTool(Tool):
    """Identify which UI panel is shown in screenshot."""

    name = "get_screen_type"
    description = "Identify which UI panel is shown in a Stardew Valley screenshot (pierre_shop, tv_dialog, inventory, or unknown)"

    inputs = {
        "image_path": {
            "type": "string",
            "description": "Path to the screenshot file to analyze"
        }
    }

    output_type = "dict"

    def forward(self, image_path: str):
        """Execute the screen type classification."""
        # Mock implementation - in reality use template matching or VLM
        from pathlib import Path

        if not Path(image_path).exists():
            return {"screen_type": "unknown", "error": "File not found"}

        # Simple heuristic (replace with real logic)
        if "pierre" in image_path.lower():
            return {"screen_type": "pierre_shop"}
        elif "tv" in image_path.lower():
            return {"screen_type": "tv_dialog"}
        elif "inventory" in image_path.lower():
            return {"screen_type": "inventory"}
        else:
            return {"screen_type": "unknown"}
```

</details>

---

## Part 3: Comparison

### Questions

1. **What's the difference between OpenAI format and Smolagents Tool class?**

   <details>
   <summary>Answer</summary>

   - **OpenAI format**: Pure JSON schema, no implementation. Used for vLLM/OpenAI API to know what tools are available.
   - **Smolagents Tool**: Python class with implementation (`forward()` method). Schema + code in one place.

   </details>

2. **Which format does vLLM use?**

   <details>
   <summary>Answer</summary>

   vLLM uses OpenAI format in the `tools` parameter of API calls. Smolagents converts Tool classes to OpenAI format internally.

   </details>

3. **Can you use both formats together?**

   <details>
   <summary>Answer</summary>

   Yes! Smolagents Tool classes can be used with vLLM because Smolagents converts them to OpenAI format when calling the model.

   </details>

---

## Bonus Challenge

Create a third tool: `crop_tv_dialog` that extracts text from the TV dialog panel.

**Requirements**:
- OpenAI format definition
- Smolagents Tool class
- Mock implementation that returns: `{"character": "Mayor Lewis", "dialog": "Hello farmer!"}`

**Hints**:
- Follow same pattern as Pierre's panel tool
- `output_type` should be `"dict"`
- Return fields: `character` (string) and `dialog` (string)

---

## Verification

Run your tools:

```bash
# Test OpenAI format
python -c "from your_module import SCREEN_TYPE_TOOL; import json; print(json.dumps(SCREEN_TYPE_TOOL, indent=2))"

# Test Smolagents class
python -c "from your_module import ScreenTypeTool; tool = ScreenTypeTool(); print(tool.forward('test.png'))"
```

Expected output:
- Valid JSON schema (OpenAI format)
- Dictionary with `screen_type` field (Smolagents)

---

## Next Steps

- Complete Exercise 2 (Agent Configuration)
- Apply these patterns to create TV dialog and inventory tools (Phase 2)
- Share your custom tools on HuggingFace Hub
