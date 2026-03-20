# Exercise 2: Agent Configuration

**Objective**: Experiment with Smolagents CodeAgent parameters to understand their effects.

**Time**: 45-60 minutes

**Prerequisites**: Completed Module 2-3, Exercise 1

---

## Part 1: Understanding `max_steps`

The `max_steps` parameter controls how many reasoning iterations the agent can perform.

### Experiment

Test the same task with different `max_steps` values:

```python
from smolagents import CodeAgent, LiteLLMModel
from stardew_vision.models.vlm_wrapper import PierresPanelTool

model = LiteLLMModel(
    model_id="Qwen2.5-VL-7B-Instruct",
    base_url="http://localhost:8001/v1",
    api_key="EMPTY"
)

tools = [PierresPanelTool()]

# Test with different max_steps
for max_steps in [1, 3, 5]:
    print(f"\n{'='*60}")
    print(f"Testing max_steps={max_steps}")
    print('='*60)

    agent = CodeAgent(
        tools=tools,
        model=model,
        max_steps=max_steps,
        verbosity=2
    )

    result = agent.run(
        "Extract information from /workspaces/stardew-vision/tests/fixtures/pierre_shop_001.png"
    )

    print(f"Result: {result}")
```

### Questions

1. **What happens with `max_steps=1`?**

   <details>
   <summary>Answer</summary>

   The agent makes a single attempt. If the task is simple (single tool call), this works. For complex tasks requiring multiple steps, it may fail or produce incomplete results.

   </details>

2. **When would you use `max_steps=1`?**

   <details>
   <summary>Answer</summary>

   - Single-shot classification tasks
   - When you know exactly which tool to call
   - To prevent agent from "overthinking"
   - For faster response times
   - MVP (like Stardew Vision Pierre's shop - one screen, one tool)

   </details>

3. **When would you need `max_steps > 3`?**

   <details>
   <summary>Answer</summary>

   - Multi-step workflows (e.g., extract → validate → summarize)
   - Complex reasoning tasks
   - When agent needs to explore multiple approaches
   - Tasks requiring tool chaining

   </details>

---

## Part 2: Verbosity Levels

The `verbosity` parameter controls how much the agent logs.

### Experiment

Test with different verbosity levels:

```python
for verbosity in [0, 1, 2]:
    print(f"\n{'='*60}")
    print(f"Testing verbosity={verbosity}")
    print('='*60)

    agent = CodeAgent(
        tools=tools,
        model=model,
        max_steps=3,
        verbosity=verbosity
    )

    result = agent.run("Extract from screenshot.png")
```

### Questions

1. **What does `verbosity=0` show?**

   <details>
   <summary>Answer</summary>

   Silent mode - only errors. No intermediate reasoning or code generation shown. Fastest, minimal output.

   </details>

2. **What does `verbosity=1` show?**

   <details>
   <summary>Answer</summary>

   Normal mode - shows high-level steps (tool calls, results). Good for production.

   </details>

3. **What does `verbosity=2` show?**

   <details>
   <summary>Answer</summary>

   Verbose mode - shows everything (reasoning, generated code, execution). Good for debugging and learning.

   </details>

4. **Which verbosity should you use in production?**

   <details>
   <summary>Answer</summary>

   `verbosity=0` or `1`:
   - `0` for production API (log to file instead)
   - `1` for debugging production issues
   - `2` only for development/debugging

   </details>

---

## Part 3: Adding/Removing Base Tools

The `add_base_tools` parameter controls whether default tools (DuckDuckGo search, etc.) are included.

### Experiment

```python
# With base tools
agent_with_base = CodeAgent(
    tools=[PierresPanelTool()],
    model=model,
    add_base_tools=True,  # Add default tools
    verbosity=1
)

# Without base tools
agent_without_base = CodeAgent(
    tools=[PierresPanelTool()],
    model=model,
    add_base_tools=False,  # No default tools
    verbosity=1
)

# Compare available tools
print("With base tools:")
print([tool.name for tool in agent_with_base.tools])

print("\nWithout base tools:")
print([tool.name for tool in agent_without_base.tools])
```

### Questions

1. **What base tools are available?**

   <details>
   <summary>Answer</summary>

   With `smolagents[toolkit]`:
   - `DuckDuckGoSearchTool` - Web search
   - `VisitWebpageTool` - Fetch webpage content
   - Other tools depending on installation

   </details>

2. **When should you use `add_base_tools=True`?**

   <details>
   <summary>Answer</summary>

   - When task might require web search
   - Exploratory tasks where agent needs to find information
   - Building general-purpose assistants

   </details>

3. **When should you use `add_base_tools=False`?**

   <details>
   <summary>Answer</summary>

   - Controlled environments (like Stardew Vision)
   - When you have exact tools needed
   - To prevent unwanted tool calls (e.g., don't want agent searching web)
   - For deterministic behavior

   </details>

---

## Part 4: Model Backend Comparison

Compare InferenceClientModel vs LiteLLMModel performance.

### Experiment

**Note**: This requires model downloaded locally. Skip if you only have vLLM.

```python
import time
from smolagents import InferenceClientModel, LiteLLMModel

# Transformers backend (local)
print("Testing InferenceClientModel (transformers)...")
model_transformers = InferenceClientModel("Qwen/Qwen2.5-VL-7B-Instruct")
agent_transformers = CodeAgent(tools=[PierresPanelTool()], model=model_transformers, verbosity=0)

start = time.time()
result1 = agent_transformers.run("Extract from screenshot.png")
latency_transformers = time.time() - start

# vLLM backend (served)
print("\nTesting LiteLLMModel (vLLM)...")
model_vllm = LiteLLMModel(
    model_id="Qwen2.5-VL-7B-Instruct",
    base_url="http://localhost:8001/v1",
    api_key="EMPTY"
)
agent_vllm = CodeAgent(tools=[PierresPanelTool()], model=model_vllm, verbosity=0)

start = time.time()
result2 = agent_vllm.run("Extract from screenshot.png")
latency_vllm = time.time() - start

# Compare
print(f"\nLatency comparison:")
print(f"  InferenceClientModel: {latency_transformers:.2f}s")
print(f"  LiteLLMModel (vLLM):  {latency_vllm:.2f}s")
print(f"  Speedup: {latency_transformers / latency_vllm:.2f}x")
```

### Questions

1. **Which is faster?**

   <details>
   <summary>Answer</summary>

   LiteLLMModel with vLLM is typically 2-5x faster due to:
   - Continuous batching
   - Optimized GPU kernels
   - KV cache management

   </details>

2. **When to use InferenceClientModel?**

   <details>
   <summary>Answer</summary>

   - Local development without vLLM server
   - One-off scripts
   - Prototyping new models

   </details>

3. **When to use LiteLLMModel?**

   <details>
   <summary>Answer</summary>

   - Production deployments
   - When latency matters
   - Serving multiple requests
   - OpenShift AI / cloud deployments

   </details>

---

## Part 5: System Prompt Customization

Customize the agent's system prompt for better results.

### Experiment

```python
# Default system prompt
agent_default = CodeAgent(
    tools=[PierresPanelTool()],
    model=model,
    verbosity=1
)

# Custom system prompt
agent_custom = CodeAgent(
    tools=[PierresPanelTool()],
    model=model,
    system_prompt=(
        "You are an accessibility assistant for visually impaired Stardew Valley players. "
        "Your job is to extract information from game screenshots and return it in a structured format. "
        "Always prioritize clarity and completeness. "
        "If you're unsure about a field, indicate that in the result."
    ),
    verbosity=1
)

# Compare results
print("Default prompt:")
result1 = agent_default.run("Extract from screenshot.png")

print("\nCustom prompt:")
result2 = agent_custom.run("Extract from screenshot.png")
```

### Questions

1. **When should you customize the system prompt?**

   <details>
   <summary>Answer</summary>

   - Domain-specific tasks (like accessibility for games)
   - When default behavior isn't optimal
   - To enforce specific output formats
   - To add safety constraints

   </details>

2. **What should a good system prompt include?**

   <details>
   <summary>Answer</summary>

   - Role ("You are an accessibility assistant")
   - Context ("for visually impaired players")
   - Task ("extract information from screenshots")
   - Constraints ("always prioritize clarity")
   - Error handling ("if unsure, indicate in result")

   </details>

---

## Part 6: Planning Interval

The `planning_interval` parameter controls when the agent regenerates its execution plan.

### Experiment

```python
# Replan every step
agent_frequent = CodeAgent(
    tools=[PierresPanelTool()],
    model=model,
    planning_interval=1,  # Replan every step
    verbosity=2
)

# Replan less frequently
agent_infrequent = CodeAgent(
    tools=[PierresPanelTool()],
    model=model,
    planning_interval=5,  # Replan every 5 steps
    verbosity=2
)

# For single-shot tasks, both should behave the same
result1 = agent_frequent.run("Extract from screenshot.png")
result2 = agent_infrequent.run("Extract from screenshot.png")
```

### Questions

1. **What does `planning_interval=1` do?**

   <details>
   <summary>Answer</summary>

   Agent regenerates its plan after every step. More adaptive but slower.

   </details>

2. **When to use low planning_interval?**

   <details>
   <summary>Answer</summary>

   - Dynamic tasks where plan might change
   - Exploration tasks
   - When environment is unpredictable

   </details>

3. **For Stardew Vision (single-shot), does planning_interval matter?**

   <details>
   <summary>Answer</summary>

   No - with `max_steps=1` or simple tasks, planning_interval has minimal effect.

   </details>

---

## Bonus Challenge

Create the "optimal" CodeAgent configuration for Stardew Vision.

### Requirements

- Fast response time
- Reliable (doesn't hallucinate tools)
- Good error messages
- Production-ready

### Your Configuration

```python
agent = CodeAgent(
    tools=[PierresPanelTool()],
    model=LiteLLMModel(...),  # Fill in parameters
    max_steps=?,
    verbosity=?,
    add_base_tools=?,
    system_prompt=?,
    planning_interval=?
)
```

### Recommended Solution

<details>
<summary>Click to reveal</summary>

```python
agent = CodeAgent(
    tools=[PierresPanelTool()],
    model=LiteLLMModel(
        model_id="Qwen2.5-VL-7B-Instruct",
        base_url="http://localhost:8001/v1",
        api_key="EMPTY"
    ),
    max_steps=1,  # Single-shot (one screen, one tool)
    verbosity=0,  # Silent in production (log to file)
    add_base_tools=False,  # No external tools needed
    system_prompt=(
        "You are an accessibility assistant for Stardew Valley. "
        "Extract information from screenshots using the provided tools. "
        "Return complete, accurate data."
    ),
    planning_interval=1  # Doesn't matter for single-shot
)
```

**Rationale**:
- `max_steps=1`: Single tool call per screenshot
- `verbosity=0`: Production silence (use logging instead)
- `add_base_tools=False`: Controlled environment
- `system_prompt`: Clear role and expectations
- vLLM backend: Production performance

</details>

---

## Verification

Test your optimized agent:

```bash
python -c "
from smolagents import CodeAgent, LiteLLMModel
from stardew_vision.models.vlm_wrapper import PierresPanelTool
import time

model = LiteLLMModel(
    model_id='Qwen2.5-VL-7B-Instruct',
    base_url='http://localhost:8001/v1',
    api_key='EMPTY'
)

agent = CodeAgent(
    tools=[PierresPanelTool()],
    model=model,
    max_steps=1,
    verbosity=0,
    add_base_tools=False
)

start = time.time()
result = agent.run('Extract from /workspaces/stardew-vision/tests/fixtures/pierre_shop_001.png')
latency = time.time() - start

print(f'Latency: {latency:.2f}s')
print(f'Result: {result}')
"
```

Expected:
- Latency < 3s
- Valid extraction result
- No errors

---

## Next Steps

- Complete Exercise 3 (Debugging)
- Apply optimal configuration to production VLMOrchestrator
- Benchmark different configurations with MLFlow
