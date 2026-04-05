# Module 1: Manual Tool Dispatch

**Duration**: 1-2 hours
**Prerequisites**: Basic Python, understanding of JSON
**Example Code**: [`examples/module1_manual_dispatch.py`](../examples/module1_manual_dispatch.py)

---

## Learning Objectives

By the end of this module, you will:

- ✅ Understand the OpenAI function-calling format
- ✅ Create tool definitions without any framework
- ✅ Build a tool registry and manual dispatcher
- ✅ Parse VLM responses and execute tools
- ✅ Understand what frameworks like Smolagents automate

---

## Why Start Manual?

**Philosophy**: *Understand the fundamentals before adding abstraction*

Starting with manual tool dispatch helps you:

1. **Debug framework issues** - When Smolagents fails, you'll know where to look
2. **Know when frameworks are overkill** - Sometimes raw code is simpler
3. **Appreciate automation** - You'll see exactly what frameworks save you
4. **Build custom solutions** - For cases frameworks don't handle

Think of it like learning manual transmission before automatic — you'll be a better driver either way.

---

## The Problem We're Solving

We have a screenshot of Pierre's shop in Stardew Valley. We want to extract item details (name, price, description). How do we bridge this gap?

```
┌─────────────────┐
│  Screenshot     │  "pierre_shop_001.png"
│  (1600×1200 px) │
└────────┬────────┘
         │
         │  ??? How do we get from pixels to structured data?
         │
         ▼
┌─────────────────┐
│  Structured     │  {"name": "Parsnip", "price": 20, ...}
│  Data (JSON)    │
└─────────────────┘
```

**Answer**: We need two things:

1. **Tools** - Functions that can extract data (we have `crop_pierres_detail_panel`)
2. **Orchestrator** - Something that decides which tool to use (eventually: a VLM)

But first, let's understand the mechanics **without** a VLM.

---

## Conceptual Overview: How Tool Calling Works

Here's the complete flow from user input to extracted data:

```
┌──────────────────────────────────────────────────────────────────┐
│                    TOOL CALLING FLOW                              │
└──────────────────────────────────────────────────────────────────┘

1. USER PROVIDES TOOLS
   ┌─────────────────────────────────┐
   │ Tool Definitions (JSON)         │  What can the VLM call?
   │ - name: "crop_pierres_detail..."│
   │ - description: "Extract from..." │
   │ - parameters: {"image_path"}    │
   └──────────────┬──────────────────┘
                  │
                  │ Sent to VLM
                  ▼
2. VLM DECIDES WHICH TOOL TO USE
   ┌─────────────────────────────────┐
   │ VLM (Qwen2.5-VL)                │  Analyzes prompt + tools
   │ Input: "Extract from this shop" │
   │ Available tools: [...]          │
   └──────────────┬──────────────────┘
                  │
                  │ Returns JSON
                  ▼
3. VLM RETURNS TOOL CALL
   ┌─────────────────────────────────┐
   │ Tool Call Response (JSON)       │
   │ {                               │
   │   "tool_call": {                │
   │     "function": {               │
   │       "name": "crop_pierres...",│
   │       "arguments": "{...}"      │
   │     }                           │
   │   }                             │
   │ }                               │
   └──────────────┬──────────────────┘
                  │
                  │ Parse JSON
                  ▼
4. DISPATCHER LOOKS UP TOOL
   ┌─────────────────────────────────┐
   │ Tool Registry (Dict)            │
   │ {                               │
   │   "crop_pierres...": function1, │
   │   "get_screen_type": function2  │
   │ }                               │
   └──────────────┬──────────────────┘
                  │
                  │ Get function from dict
                  ▼
5. EXECUTE TOOL
   ┌─────────────────────────────────┐
   │ crop_pierres_detail_panel(      │
   │   image_path="screenshot.png"   │
   │ )                               │
   └──────────────┬──────────────────┘
                  │
                  │ OpenCV + PaddleOCR
                  ▼
6. RETURN RESULT
   ┌─────────────────────────────────┐
   │ Result (Dict)                   │
   │ {                               │
   │   "name": "Parsnip",            │
   │   "description": "A spring...", │
   │   "price_per_unit": 20,         │
   │   "quantity_selected": 5,       │
   │   "total_cost": 100             │
   │ }                               │
   └─────────────────────────────────┘
```

**Key insight**: Tool calling is NOT magic. It's:

1. VLM returns JSON with tool name + arguments
2. You parse the JSON
3. You call the function from your registry

Frameworks just automate step 2-3.

---

## Code Walkthrough

Now let's walk through the actual code in `examples/module1_manual_dispatch.py`.

### Part 1: Tool Definition (Lines 22-40)

**What**: JSON schema describing the tool to the VLM

```python
TOOL_DEFINITIONS = [
    {
        "type": "function",                    # Always "function" for OpenAI format
        "function": {
            "name": "crop_pierres_detail_panel",  # Unique identifier
            "description": "Extract item details from Pierre's General Store detail panel in a Stardew Valley screenshot",
            "parameters": {                    # JSON Schema for arguments
                "type": "object",
                "properties": {
                    "image_path": {
                        "type": "string",
                        "description": "Path to the screenshot file"
                    }
                },
                "required": ["image_path"]     # Which params are mandatory
            }
        }
    }
]
```

**Why each field matters**:

- `name` - The VLM will reference this when making a tool call
- `description` - Helps the VLM decide when to use this tool vs others
- `parameters` - Tells the VLM what arguments are needed and their types
- `required` - Prevents VLM from calling the tool without mandatory arguments

**Important**: This is the **OpenAI function-calling format**. It's an industry standard used by:
- OpenAI (GPT-4, GPT-4V)
- vLLM (our serving framework)
- Qwen models (our VLM)
- Most LLM serving platforms

### Part 2: Tool Registry (Lines 46-68)

**What**: A mapping from tool names to actual Python functions

```python
def crop_pierres_detail_panel(image_path: str) -> dict:
    """
    Wrapper for actual tool implementation.
    In production, this imports from stardew_vision.tools
    """
    try:
        from stardew_vision.tools import crop_pierres_detail_panel as real_tool
        return real_tool(image_path)
    except ImportError:
        # If tool not available, return mock data for demo
        print("⚠️  Tool not available, using mock data")
        return {
            "name": "Parsnip",
            "description": "A spring vegetable",
            "price_per_unit": 20,
            "quantity_selected": 5,
            "total_cost": 100
        }


TOOL_REGISTRY = {
    "crop_pierres_detail_panel": crop_pierres_detail_panel,
}
```

**Why separation of definition and implementation?**

- **Definition** (JSON) - Sent to VLM, tells it what's available
- **Registry** (Dict) - Used by dispatcher, maps names to functions
- **Implementation** (Function) - Does the actual work

This separation allows you to:
- Send definitions to VLM without importing heavy libraries
- Swap implementations without changing definitions
- Test dispatcher with mock functions

### Part 3: Manual Dispatcher (Lines 74-107)

**What**: The code that executes a tool based on the VLM's response

```python
def dispatch_tool(tool_name: str, arguments: dict) -> dict:
    """
    Manually invoke a tool from registry.

    This is what frameworks like Smolagents automate.
    Understanding this helps you debug framework issues later.
    """
    # Step 1: Validate tool exists
    if tool_name not in TOOL_REGISTRY:
        available = ", ".join(TOOL_REGISTRY.keys())
        raise ValueError(f"Unknown tool: {tool_name}. Available: {available}")

    # Step 2: Log what we're doing (observability!)
    print(f"📞 Dispatching tool: {tool_name}")
    print(f"📋 Arguments: {json.dumps(arguments, indent=2)}")
    print()

    # Step 3: Call the function (the actual work!)
    result = TOOL_REGISTRY[tool_name](**arguments)  # Magic of **kwargs

    # Step 4: Log the result
    print(f"✅ Result:")
    print(json.dumps(result, indent=2))
    print()

    return result
```

**Line-by-line breakdown**:

- **Line 91**: Check if tool exists in registry (error handling)
- **Line 95-97**: Logging for debugging (production needs this!)
- **Line 100**: The actual dispatch - `**arguments` unpacks the dict as keyword arguments
- **Line 102-104**: Log result for observability

**The magic**: `TOOL_REGISTRY[tool_name](**arguments)`

This line:
1. Looks up the function in the registry dict
2. Unpacks the arguments dict as keyword arguments
3. Calls the function
4. Returns the result

If `tool_name = "crop_pierres_detail_panel"` and `arguments = {"image_path": "/path/to/file.png"}`, this becomes:

```python
crop_pierres_detail_panel(image_path="/path/to/file.png")
```

### Part 4: Simulating VLM Response (Lines 113-131)

**What**: Mock data showing what a real VLM would return

```python
def simulate_vlm_response(image_path: str) -> dict:
    """
    Simulate what a VLM would return (without actually running VLM).

    This is the JSON structure that vLLM returns in the `tool_calls` field.
    Understanding this structure is critical for parsing VLM responses.
    """
    return {
        "tool_call": {
            "id": "call_abc123",               # Unique call identifier
            "type": "function",                # Always "function"
            "function": {
                "name": "crop_pierres_detail_panel",
                "arguments": json.dumps({      # Arguments as JSON string!
                    "image_path": image_path
                })
            }
        }
    }
```

**Critical detail**: `arguments` is a **JSON string**, not a dict!

You must:
1. Parse the outer JSON response
2. Parse the inner `arguments` JSON string
3. Then you have a dict to pass to the function

This is why line 210 in the main code does:

```python
arguments = json.loads(tool_call["function"]["arguments"])
```

### Part 5: Putting It All Together (Lines 138-246)

The `main()` function demonstrates the complete flow:

```python
# Step 1: Show tool definitions (lines 150-162)
print(json.dumps(TOOL_DEFINITIONS, indent=2))

# Step 2: Show tool registry (lines 169-178)
for name, func in TOOL_REGISTRY.items():
    print(f"  - {name}: {func.__doc__}")

# Step 3: Simulate VLM response (lines 187-196)
vlm_response = simulate_vlm_response(image_path)
print(json.dumps(vlm_response, indent=2))

# Step 4: Parse and dispatch (lines 203-221)
tool_call = vlm_response["tool_call"]
tool_name = tool_call["function"]["name"]
arguments = json.loads(tool_call["function"]["arguments"])  # Parse JSON string!
result = dispatch_tool(tool_name, arguments)
```

---

## Key Patterns

### Pattern 1: Tool Definition Structure

**Always include**:
- Clear, unique name
- Descriptive description (helps VLM decide)
- Complete JSON schema for parameters
- Mark required parameters

**Good description**:
```python
"description": "Extract item details from Pierre's General Store detail panel in a Stardew Valley screenshot"
```

**Bad description**:
```python
"description": "Extracts stuff"  # Too vague! VLM won't know when to use this
```

### Pattern 2: Registry Lookup

**The pattern**:
```python
REGISTRY = {
    "tool_name": actual_function,
}

# Later:
func = REGISTRY[name]
result = func(**args)
```

**Why a dict?**
- O(1) lookup (fast)
- Easy to add/remove tools
- Can dynamically build from imports

### Pattern 3: Argument Unpacking

**The `**kwargs` pattern**:

```python
def my_tool(param1: str, param2: int) -> dict:
    return {"result": f"{param1} x {param2}"}

arguments = {"param1": "hello", "param2": 5}
result = my_tool(**arguments)  # Becomes: my_tool(param1="hello", param2=5)
```

This is critical because:
- VLM returns a dict of arguments
- Your function expects keyword arguments
- `**arguments` bridges the gap

---

## Hands-On Activity

### Checkpoint 1: Run the Example

```bash
# From project root
cd /workspaces/stardew-vision
python agent-learning/examples/module1_manual_dispatch.py
```

**Expected output**:
1. Tool definitions in JSON
2. Tool registry listing
3. Simulated VLM response
4. Dispatch logging
5. Extraction result (or mock data if tool not available)

**What to observe**:
- The JSON structure is verbose but readable
- Dispatch is just dict lookup + function call
- Logging is essential for debugging

### Checkpoint 2: Trace Through the Code

Open `examples/module1_manual_dispatch.py` and:

1. **Lines 22-40**: Find the tool definition. What fields are present?
2. **Line 66**: Find the registry. How is it structured?
3. **Line 100**: Find the dispatch line. What does `**arguments` do?
4. **Line 210**: Find the argument parsing. Why `json.loads()`?

**Answer key**:
1. `type`, `function` with `name`, `description`, `parameters`
2. Simple dict: `{name: function}`
3. Unpacks dict as keyword arguments
4. VLM returns arguments as JSON string, not dict

### Checkpoint 3: Create Your Own Tool

**Exercise**: Add a second tool to the system.

**Specification**:
- **Name**: `get_screen_type`
- **Description**: "Identify which UI panel is shown in a Stardew Valley screenshot"
- **Parameters**: `image_path` (string, required)
- **Returns**: `{"screen_type": "pierre_shop" | "tv_dialog" | "inventory" | "unknown"}`

**Implementation steps**:

1. Create the tool definition:
```python
{
    "type": "function",
    "function": {
        "name": "get_screen_type",
        "description": "Identify which UI panel is shown in a Stardew Valley screenshot",
        "parameters": {
            "type": "object",
            "properties": {
                "image_path": {
                    "type": "string",
                    "description": "Path to the screenshot file"
                }
            },
            "required": ["image_path"]
        }
    }
}
```

2. Add to `TOOL_DEFINITIONS` list

3. Create the implementation:
```python
def get_screen_type(image_path: str) -> dict:
    """Mock implementation - just returns pierre_shop for now."""
    return {"screen_type": "pierre_shop"}
```

4. Add to `TOOL_REGISTRY`:
```python
TOOL_REGISTRY = {
    "crop_pierres_detail_panel": crop_pierres_detail_panel,
    "get_screen_type": get_screen_type,  # New tool!
}
```

5. Test by updating the simulated VLM response to call your new tool

**Full exercise details**: See [`exercises/exercise1_tool_creation.md`](../exercises/exercise1_tool_creation.md)

---

## Common Pitfalls

### Pitfall 1: Forgetting to Parse Arguments

**Wrong**:
```python
tool_call = vlm_response["tool_call"]
arguments = tool_call["function"]["arguments"]  # This is a JSON string!
result = my_tool(**arguments)  # ERROR: can't unpack a string
```

**Right**:
```python
tool_call = vlm_response["tool_call"]
arguments = json.loads(tool_call["function"]["arguments"])  # Parse first!
result = my_tool(**arguments)  # Now it's a dict
```

### Pitfall 2: Vague Tool Descriptions

The VLM uses descriptions to decide which tool to call. Be specific!

**Bad**:
```python
"description": "Processes images"  # What kind of processing?
```

**Good**:
```python
"description": "Extract item details from Pierre's General Store detail panel in a Stardew Valley screenshot"
```

### Pitfall 3: Missing Required Parameters

Always mark parameters as required if they're mandatory:

```python
"parameters": {
    "type": "object",
    "properties": { ... },
    "required": ["image_path"]  # Don't forget this!
}
```

Without this, the VLM might call your tool without required arguments.

---

## Key Takeaways

### 1. Tool Calling is Just JSON + Dict Lookup

There's no magic:
- Tool definitions describe functions in JSON
- Registry maps names to functions
- Dispatch = `registry[name](**args)`

### 2. OpenAI Format is a Standard

This JSON schema is used by:
- OpenAI API (GPT-4, GPT-4V)
- vLLM (our serving platform)
- Most LLM frameworks

Learning it once helps everywhere.

### 3. Separation of Concerns

- **Definition** (JSON) - Metadata for VLM
- **Registry** (Dict) - Name → function mapping
- **Implementation** (Function) - Actual logic

This separation enables:
- Sending definitions without heavy imports
- Swapping implementations easily
- Testing with mocks

### 4. Logging is Essential

Notice all the `print()` statements in the example:
- When tools are dispatched
- What arguments are passed
- What results are returned

In production, replace with proper logging (`logging.info()`, MLFlow, etc.).

---

## What Frameworks Automate

After doing this manually, you'll appreciate what Smolagents (Module 2) does for you:

**You wrote**:
```python
tool_call = vlm_response["tool_call"]
tool_name = tool_call["function"]["name"]
arguments = json.loads(tool_call["function"]["arguments"])

if tool_name not in TOOL_REGISTRY:
    raise ValueError(...)

result = TOOL_REGISTRY[tool_name](**arguments)
```

**Smolagents does**:
```python
agent = CodeAgent(tools=[MyTool()], model=model)
result = agent.run("Extract from screenshot")
# All parsing, validation, dispatch happens automatically
```

But now you **understand** what's happening under the hood!

---

## Summary

You now understand:

1. ✅ **OpenAI function-calling format** - JSON schema for tool definitions
2. ✅ **Tool registry pattern** - Dict mapping names to functions
3. ✅ **Manual dispatch logic** - Parse JSON, look up function, call with args
4. ✅ **VLM response structure** - `tool_calls` field with nested JSON
5. ✅ **Why frameworks exist** - They automate the tedious parts

**The fundamental pattern**:
```
VLM returns JSON → Parse it → Look up function → Call it → Return result
```

Everything else in this curriculum builds on this foundation.

---

## Next Steps

**Immediate**:
1. Complete Exercise 1 (create your own tool)
2. Experiment with different tool definitions
3. Try adding error handling to the dispatcher

**Next Module**: Module 2 - Smolagents Basics

In Module 2, you'll see how Smolagents automates everything you just did manually. You'll learn:
- How to create `Tool` classes (instead of manual definitions)
- How `CodeAgent` dispatches automatically (instead of manual dispatch)
- How Smolagents writes Python code (not just JSON)

**The transition**:
- Module 1 (manual): You control everything, but write more code
- Module 2 (Smolagents): Framework controls dispatch, you write less code
- Module 3 (vLLM): Add real VLM intelligence, not just simulated responses

---

## Additional Resources

**Reference**:
- See full code: [`examples/module1_manual_dispatch.py`](../examples/module1_manual_dispatch.py)
- Exercise: [`exercises/exercise1_tool_creation.md`](../exercises/exercise1_tool_creation.md)
- OpenAI function calling spec: [OpenAI API Reference](https://platform.openai.com/docs/guides/function-calling)

**Diagrams**:
- [`diagrams/tool-calling-flow.txt`](../diagrams/tool-calling-flow.txt) - Complete flow diagram

**Related**:
- Our project's tool implementation: `src/stardew_vision/tools/`
- ADR-009: Agent/tool-calling architecture decision

---

**Ready for Module 2?** → [`module2-smolagents-basics.md`](module2-smolagents-basics.md)
