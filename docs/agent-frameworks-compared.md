# Agent Framework Comparison for Stardew Vision (March 2026)

## Executive Summary

**Decision (updated 2026-04-02)**: Use **raw OpenAI client** — no agent framework for MVP

**Rationale**:
- The agentic loop is at most 4 turns with predictable structure — no framework needed
- Full control over loop logic, error handling, and error logging
- No abstraction layer between our code and vLLM's tool-calling implementation
- Easier to debug, easier to explain in the conference talk
- Can adopt a framework (Smolagents, LangGraph) in Phase 2+ if complexity grows

**Previous recommendation**: Smolagents (still valid if multi-agent or Hub integrations become priorities — see analysis below)

---

## Quick Decision Matrix

| Your Need | Best Choice |
|-----------|-------------|
| **VLM tool calling with Qwen2.5-VL via vLLM** | **Smolagents** ✅ (VLM-optimized, model-agnostic) |
| **Maximum control, minimal abstraction** | Raw OpenAI client |
| **Production observability & hooks** | Claude Agent SDK (if using Claude) |
| **Simplicity & learning** | **Smolagents** ✅ |
| **Multi-modal (vision + code)** | **Smolagents** ✅ (first-class VLM support) |
| **Complex state machines** | LangGraph (Phase 2+ if needed) |
| **Multi-agent collaboration** | CrewAI (Phase 3+ if needed) |

---

## Detailed Framework Comparison

### Feature Matrix

| Feature | **OpenAI Agents SDK** | **Claude Agent SDK** | **Smolagents** | **Raw OpenAI Client** |
|---------|----------------------|---------------------|---------------|---------------------|
| **Philosophy** | Production-ready with built-in tools | "Give Claude a computer" | "Simplicity above all" (~1000 LOC) | Minimal abstraction |
| **Built-in tools** | WebSearch, FileSearch, ComputerTool | Read, Write, Edit, Bash, Glob, Grep, WebSearch, WebFetch | DuckDuckGoSearch, Image Generator (via Hub) | None (you implement) |
| **Tool calling paradigm** | JSON function calling | "Tool Calling 2.0" - programmatic (Claude writes code to call tools) | CodeAgent (Python code) OR ToolCallingAgent (JSON) | JSON function calling |
| **Model support** | GPT-4/5 optimized, works with OpenAI-compatible APIs | Claude-only (Opus, Sonnet, Haiku) | **Model-agnostic** (Qwen, Llama, OpenAI, Anthropic, local) | Any OpenAI-compatible API |
| **VLM support** | Limited (primarily text-focused) | Vision via messages | **First-class** (vision, video, audio) | Via message content |
| **Hooks/callbacks** | Limited | **Extensive** (PreToolUse, PostToolUse, SessionStart, Stop, etc.) | Basic (planning_interval) | Manual implementation |
| **Sessions/memory** | Built-in sessions | Built-in sessions with resume/fork | Manual state management | Manual |
| **MCP integration** | Built-in MCP server support | Built-in MCP integration | MCP server support via ToolCollection.from_mcp() | Manual |
| **Subagents** | Agents as tools | Built-in subagent system | Multi-agent via managed_agents | Manual |
| **Permission system** | Basic allowed_tools | **Granular** (acceptAll, acceptEdits, rejectAll) | tools parameter | Manual |
| **Code execution** | ComputerTool (local execution) | Bash tool | **Sandboxed** (Modal, Blaxel, E2B, Docker) | Manual |
| **Complexity** | Medium (production-focused) | Medium-High (many features) | **Lowest** (minimal abstractions) | Lowest (no abstraction) |
| **Learning curve** | Moderate | Moderate | **Easiest** | Easiest |
| **Dependencies** | openai-agents | claude-agent-sdk | smolagents[toolkit] | openai |
| **CLI tools** | No | No (but complements Claude Code CLI) | **Yes** (smolagent, webagent) | No |
| **Hub integrations** | No | No | **Yes** (share agents/tools as Spaces) | No |
| **Best for** | OpenAI-native production apps | Claude-based automation with rich tooling | Learning, prototyping, multi-modal VLM projects | Maximum control, simple use cases |

---

## Code Comparison: Same Task, Four Approaches

**Task**: Analyze a screenshot and call an extraction tool.

### 1. Raw OpenAI Client

**Lines of code**: ~20
**Pros**: Full control, debuggable, no magic
**Cons**: Manual error handling, manual logging

```python
from openai import AsyncOpenAI
import json
import base64

client = AsyncOpenAI(base_url="http://localhost:8001/v1", api_key="EMPTY")

# Encode image
with open(image_path, "rb") as f:
    image_b64 = base64.b64encode(f.read()).decode("utf-8")

response = await client.chat.completions.create(
    model="Qwen2.5-VL-7B-Instruct",
    messages=[
        {"role": "system", "content": "Classify UI and call extraction tool."},
        {
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}},
                {"type": "text", "text": "Extract information from this screenshot."}
            ]
        }
    ],
    tools=TOOL_DEFINITIONS,
    tool_choice="required"
)

# Manual dispatch
tool_call = response.choices[0].message.tool_calls[0]
result = TOOL_REGISTRY[tool_call.function.name](image_path=image_path)
```

### 2. Smolagents

**Lines of code**: ~20
**Pros**: Model-agnostic (works with Qwen!), first-class VLM support, Hub integrations
**Cons**: Less mature than OpenAI/Claude SDKs

```python
from smolagents import CodeAgent, Tool, InferenceClientModel

class CropPierresPanelTool(Tool):
    name = "crop_pierres_detail_panel"
    description = "Extract item details from Pierre's General Store panel"
    inputs = {"image_path": {"type": "string", "description": "Path to screenshot"}}
    output_type = "dict"

    def forward(self, image_path: str):
        # Your extraction logic here
        pass

model = InferenceClientModel(model_id="Qwen/Qwen2.5-VL-7B-Instruct")
agent = CodeAgent(tools=[CropPierresPanelTool()], model=model)

result = agent.run(f"Extract information from {image_path}")
```

### 3. OpenAI Agents SDK

**Lines of code**: ~15
**Pros**: Built-in tool loop, session management
**Cons**: GPT-optimized (may not work well with Qwen via vLLM)

```python
from agents import Agent, Runner, function_tool

@function_tool
def crop_pierres_detail_panel(image_path: str) -> dict:
    """Extract item details from Pierre's General Store."""
    # Your extraction logic here
    pass

agent = Agent(
    name="ScreenAnalyzer",
    instructions="Analyze screenshot and call extraction tool.",
    tools=[crop_pierres_detail_panel]
)

result = Runner.run_sync(agent, f"Analyze {image_path}")
```

### 4. Claude Agent SDK

**Lines of code**: ~12
**Pros**: Rich hooks, built-in observability, permission system
**Cons**: Claude-only (can't use with Qwen2.5-VL)

```python
from claude_agent_sdk import query, ClaudeAgentOptions

async for message in query(
    prompt=f"Analyze screenshot at {image_path} using crop_pierres_detail_panel tool",
    options=ClaudeAgentOptions(
        allowed_tools=["crop_pierres_detail_panel"],
        hooks={"PostToolUse": [log_to_mlflow]}  # Built-in observability
    )
):
    if hasattr(message, "result"):
        print(message.result)
```

---

## Why Smolagents for Stardew Vision?

### 1. VLM-First Design

Smolagents was built specifically for multi-modal AI applications. Unlike OpenAI/Claude SDKs which were retrofitted for vision, Smolagents has first-class support for:
- **Vision** (images) - used in MVP
- **Video** (for future live gameplay narration)
- **Audio** (for TTS integration)

### 2. Model Agnostic

Works with any model:
- Local transformers: `InferenceClientModel(model_id="Qwen/Qwen2.5-VL-7B-Instruct")`
- vLLM endpoints: `LiteLLMModel(base_url="http://localhost:8001/v1")`
- OpenAI API: `LiteLLMModel(model_id="gpt-4o")`
- Anthropic API: `LiteLLMModel(model_id="claude-sonnet-4")`

This means the same code works for:
- MVP: Local Qwen2.5-VL via vLLM
- Phase 2: Upgraded Qwen3-VL
- Production: OpenShift AI KServe endpoint
- Demos: Switch to GPT-5 or Claude if needed

### 3. CodeAgent Paradigm

CodeAgent writes **Python code** to call tools, not JSON:

```python
# VLM generates this Python code:
image = PIL.Image.open("screenshot.png")
result = crop_pierres_detail_panel(image_path="screenshot.png")
print(result)
```

This is more robust than JSON function calling because:
- Type safety (Python runtime checks)
- Composable (can chain multiple tool calls)
- Debuggable (see exact Python code generated)
- Matches "manual first" philosophy (same code you'd write manually)

### 4. Hub Integrations

Perfect for conference demos:
- Share tools as HuggingFace Spaces
- Attendees can try tools in browser
- Version control for tool definitions
- Community contributions possible

### 5. Sandboxed Execution

Production security out of the box:
- Modal: Serverless Python functions
- E2B: Isolated sandbox environments
- Docker: Containerized execution
- Blaxel: Secure code interpreter

This matters when running untrusted extraction tools or allowing user-submitted tools.

### 6. Minimal Complexity

~1000 lines of core code vs:
- LangGraph: Complex state machine API
- CrewAI: Heavy multi-agent abstractions
- OpenAI SDK: GPT-specific optimizations

Can read the entire Smolagents source in an afternoon.

### 7. Open Path to Complexity

Starts simple (CodeAgent + 1 tool) but scales to:
- Multi-agent systems (`managed_agents`)
- Complex tool chains
- Web agents (`webagent` CLI)
- Gradio UI integration

No need to rewrite when requirements grow.

---

## Why NOT Claude/OpenAI SDKs?

### Claude Agent SDK

**Blockers**:
- ❌ Requires Claude API (project uses Qwen2.5-VL locally)
- ❌ Can't call vLLM-served Qwen models
- ❌ Costs API credits

**When to use**:
- ✅ IF you switch to Claude API
- ✅ IF you need extensive hooks (PreToolUse, PostToolUse, etc.)
- ✅ IF you need granular permission system

### OpenAI Agents SDK

**Concerns**:
- ⚠️ Designed for GPT-4/5, may not optimize for Qwen via vLLM
- ⚠️ Less explicit VLM support compared to Smolagents
- ⚠️ More abstraction than needed for single-shot task

**When to use**:
- ✅ IF you switch to GPT-5 API
- ✅ IF you need built-in sessions/handoffs
- ✅ IF you need MCP integration

---

## When to Use Other Frameworks

### LangGraph

**Use when**:
- Complex conditional routing (e.g., IF TV dialog THEN extract_tv ELSE IF inventory THEN extract_inventory)
- Multi-step state machines
- Phase 2+ with multiple screen types

**Don't use for**:
- Single-shot classification (overkill)
- Simple linear workflows

### CrewAI

**Use when**:
- Multi-agent collaboration (e.g., Extractor agent + Validator agent)
- Role-based workflows
- Phase 3+ if validation agent added

**Don't use for**:
- Single-agent systems
- Deterministic tools (not LLM-based)

### Raw OpenAI Client

**Use when**:
- Maximum control required
- No framework lock-in desired
- Simplest possible code
- Single-shot tool calling

**Trade-off**:
- No built-in error handling
- No observability hooks
- No sandboxing
- Manual everything

---

## Framework Landscape 2026

Based on March 2026 research:

### Leading Frameworks

1. **OpenAI Agents SDK** (NEW in 2025)
   - Official framework from OpenAI
   - Built-in tool calling, handoffs, guardrails
   - Best for: Production workflows with OpenAI-compatible endpoints

2. **LangGraph**
   - Graph-first state machines
   - Most token-efficient in benchmarks
   - Best for: Complex stateful workflows with conditional branching

3. **CrewAI**
   - Role-based multi-agent collaboration
   - Intuitive for team-oriented workflows
   - Best for: Multi-agent collaboration scenarios

4. **Smolagents**
   - HuggingFace's agent framework
   - VLM-optimized, model-agnostic
   - Best for: Multi-modal AI applications, VLM projects

5. **LlamaIndex**
   - Specializes in RAG and document retrieval
   - Best for: Document-centric applications, knowledge work

### Key 2026 Best Practices

1. **Observability first**: Log every tool call (name, args, result, latency)
2. **Structured outputs**: Enforce JSON schemas with `response_format`
3. **Verification-aware planning**: Add pass-fail checks for each subtask
4. **Parallel function calling**: Batch multiple tool calls when possible
5. **Guardrails**: Validate inputs/outputs at boundaries
6. **Testing strategy**: Mock VLM responses for unit tests
7. **Error handling**: Distinguish VLM errors (retry) from tool errors (fail fast)
8. **Framework minimalism**: Use raw code until complexity demands abstraction

---

## Decision for Stardew Vision

### MVP (Phase 1): Raw OpenAI Client

**Architecture**:
```
User upload → FastAPI /analyze  (FastAPI = agent runtime)
  ↓
Multi-turn loop (raw openai.AsyncOpenAI → vLLM port 8001)
  Turn 1: Qwen calls crop_pierres_detail_panel
  Turn 2: Qwen checks result, corrects typos, may retry with debug=True
  Turn 3: Qwen calls text_to_speech
  ↓
FastAPI streams WAV → browser
```

**Why raw OpenAI client**:
- Loop is simple (≤4 turns, predictable structure) — no framework pays off
- Full control over error logging, image saving, tool injection
- No abstraction layer that might conflict with vLLM's tool-calling implementation
- Maximally transparent for conference talk — audience can read the code

**When to revisit (Phase 2+)**:
- If routing grows complex (multiple screen types with conditional branching) → consider LangGraph
- If multi-agent validation is added → consider Smolagents managed_agents or CrewAI
- If Hub tool sharing becomes a priority → Smolagents

### Phase 2: Multi-Screen Support

If conditional routing grows complex:
- **Consider**: LangGraph for state machines
- **Stick with Smolagents**: If CodeAgent's Python code generation handles routing well

### Phase 3: Validation Agent

If multi-agent validation needed:
- **Consider**: CrewAI for agent collaboration
- **Or**: Smolagents multi-agent (`managed_agents`)

---

## Installation

### Smolagents

```bash
# Basic installation
uv add smolagents

# With default toolkit (DuckDuckGoSearch, etc.)
uv add 'smolagents[toolkit]'

# For transformers backend (local Qwen model)
uv add 'smolagents[transformers]'

# For LiteLLM backend (vLLM, OpenAI, Anthropic)
uv add 'smolagents[litellm]'

# Recommended for Stardew Vision:
uv add 'smolagents[toolkit,litellm]'
```

### Optional (for comparison)

```bash
# OpenAI Agents SDK
uv add openai-agents

# LangGraph
uv add langgraph

# CrewAI
uv add crewai
```

**IMPORTANT**: Use `uv` exclusively, NOT pip. Pip may break ROCm PyTorch installation.

---

## Sources

**Agent Frameworks**:
- [Best AI Agent Frameworks 2025: LangGraph, CrewAI, OpenAI, LlamaIndex, AutoGen](https://www.getmaxim.ai/articles/top-5-ai-agent-frameworks-in-2025-a-practical-guide-for-ai-builders/)
- [Top 7 Agentic AI Frameworks in 2026](https://www.alphamatch.ai/blog/top-agentic-ai-frameworks-2026)
- [A Detailed Comparison of Top 6 AI Agent Frameworks in 2026](https://www.turing.com/resources/ai-agent-frameworks)
- [The AI Agent Framework Landscape in 2025](https://medium.com/@hieutrantrung.it/the-ai-agent-framework-landscape-in-2025-what-changed-and-what-matters-3cd9b07ef2c3)
- [Comparing the Top Agent Frameworks](https://www.techaheadcorp.com/blog/top-agent-frameworks/)

**HuggingFace Smolagents**:
- [Smolagents Main Documentation](https://huggingface.co/docs/smolagents/index)
- [Smolagents Guided Tour](https://huggingface.co/docs/smolagents/guided_tour)
- [Building Good Agents Tutorial](https://huggingface.co/docs/smolagents/tutorials/building_good_agents)
- [Tools Conceptual Guide](https://huggingface.co/docs/smolagents/main/en/conceptual_guides/tools)
- [CodeAgent Reference](https://huggingface.co/docs/smolagents/reference/agents#smolagents.CodeAgent)
- [ToolCallingAgent Reference](https://huggingface.co/docs/smolagents/reference/agents#smolagents.ToolCallingAgent)

**Claude Agent SDK**:
- [Building Agents with the Claude Agent SDK](https://claude.com/blog/building-agents-with-the-claude-agent-sdk)
- [Agent SDK Overview](https://platform.claude.com/docs/en/agent-sdk/overview)
- [Anthropic Tool Calling 2.0](https://medium.com/@lmpo/anthropic-tool-calling-2-0-the-game-changer-that-finally-fixes-ai-agent-fccd2f034568)
- [GitHub - claude-agent-sdk-python](https://github.com/anthropics/claude-agent-sdk-python)

**OpenAI Agents SDK**:
- [OpenAI Agents SDK](https://openai.github.io/openai-agents-python/)
- [Agents SDK | OpenAI API](https://developers.openai.com/api/docs/guides/agents-sdk)
- [OpenAI for Developers in 2025](https://developers.openai.com/blog/openai-for-developers-2025/)
- [Building Production-Ready AI Agents in 2026](https://medium.com/@sausi/in-2026-building-ai-agents-isnt-about-prompts-it-s-about-architecture-15f5cfc93950)

**VLM & Tool Calling**:
- [Multimodal AI: Best Open-Source Vision Language Models in 2026](https://www.bentoml.com/blog/multimodal-ai-a-guide-to-open-source-vision-language-models)
- [Qwen2.5-VL Usage Guide - vLLM Recipes](https://docs.vllm.ai/projects/recipes/en/latest/Qwen/Qwen2.5-VL.html)
- [Top 10 Vision Language Models in 2026](https://dextralabs.com/blog/top-10-vision-language-models/)
- [Benchmarking Best Open-Source Vision Language Models](https://www.clarifai.com/blog/benchmarking-best-open-source-vision-language-models)

**Agentic Workflows & Best Practices**:
- [Best AI Models for Agentic Workflows in 2026](https://www.mindstudio.ai/blog/best-ai-models-agentic-workflows-2026)
- [How Tools Are Called in AI Agents: Complete 2025 Guide](https://medium.com/@sayalisureshkumbhar/how-tools-are-called-in-ai-agents-complete-2025-guide-with-examples-42dcdfe6ba38)
- [Agents At Work: 2026 Playbook](https://promptengineering.org/agents-at-work-the-2026-playbook-for-building-reliable-agentic-workflows/)
- [Introducing AgentKit | OpenAI](https://openai.com/index/introducing-agentkit/)
- [Tool Calling in AI Agents 2026](https://www.techjunkgigs.com/tool-calling-in-ai-agents-how-llms-execute-real-world-actions-in-2026/)

---

## Next Steps

1. **Complete curriculum**: See `agent-learning/curriculum.md`
2. **Install Smolagents**: `uv add 'smolagents[toolkit,litellm]'`
3. **Start Module 1**: Manual tool dispatch (no framework)
4. **Build progressively**: Module by module through learning path
5. **Deliver production code**: VLMOrchestrator using Smolagents

**Timeline**: 8-12 hours over 3-4 sessions
