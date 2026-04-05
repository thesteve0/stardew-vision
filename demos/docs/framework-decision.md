# Framework Decision Summary

**Decision**: Use **Smolagents** for Stardew Vision VLM orchestrator

**Date**: March 2026

**Decision Maker**: Based on comprehensive framework comparison and Stardew Vision requirements

---

## TL;DR

**Smolagents wins because**:
1. ✅ Built for VLMs (vision, video, audio)
2. ✅ Works with Qwen2.5-VL (local or vLLM)
3. ✅ CodeAgent writes Python (robust, composable)
4. ✅ Minimal complexity (~1000 LOC)
5. ✅ Hub integrations (conference demo friendly)
6. ✅ Scales from simple to complex

---

## The Options

We evaluated 4 approaches:

1. **Raw OpenAI Client** - Manual tool dispatch
2. **Smolagents** - HuggingFace agent framework
3. **OpenAI Agents SDK** - Official OpenAI framework
4. **Claude Agent SDK** - Anthropic framework

Plus alternatives for Phase 2+:
- **LangGraph** - State machines for complex routing
- **CrewAI** - Multi-agent collaboration

---

## Why Smolagents?

### 1. VLM-First Design

Unlike OpenAI/Claude SDKs that added vision later, Smolagents was **built for multi-modal from day one**:

```python
from smolagents import CodeAgent, Tool
from PIL import Image

class VisionTool(Tool):
    inputs = {"image": {"type": "image"}}  # Native image support
    output_type = "dict"

    def forward(self, image: Image.Image):
        # Direct PIL Image handling
        return analyze(image)
```

This matters because:
- No base64 encoding gymnastics
- Native image/video/audio types
- VLM-optimized prompt templates

### 2. Model Agnostic

**Same code works with**:
- Local Qwen2.5-VL via transformers
- vLLM-served Qwen2.5-VL (MVP)
- OpenShift AI KServe endpoint (production)
- GPT-5 or Claude (if we switch)

```python
# Local transformers
model = InferenceClientModel("Qwen/Qwen2.5-VL-7B-Instruct")

# vLLM endpoint
model = LiteLLMModel(base_url="http://localhost:8001/v1", ...)

# Same agent code
agent = CodeAgent(tools=[...], model=model)
```

**Contrast with**:
- OpenAI SDK: Designed for GPT-4/5
- Claude SDK: Claude API only

### 3. CodeAgent > JSON Function Calling

**CodeAgent writes Python code**:
```python
# VLM generates this:
image_path = "/path/to/screenshot.png"
result = crop_pierres_detail_panel(image_path=image_path)
print(result)
```

**Why this is better than JSON**:
- Type-checked at runtime
- Composable (can chain tools in natural Python)
- Debuggable (see exact Python code)
- Matches "manual first" philosophy

**ToolCallingAgent uses JSON** (like OpenAI):
```json
{
  "tool": "crop_pierres_detail_panel",
  "arguments": {"image_path": "/path/to/screenshot.png"}
}
```

Less flexible, more error-prone.

### 4. Minimal Complexity

**Smolagents**: ~1000 lines of core code

Can read entire source in an afternoon. Simple abstractions:
- `Tool`: Wraps function
- `Agent`: Calls tools
- `Model`: Backend for LLM

**LangGraph**: Complex state machine API with nodes, edges, conditional routing

**CrewAI**: Heavy multi-agent abstractions with roles, delegation, collaboration

**For single-shot classification**, Smolagents is right-sized.

### 5. Hub Integrations

**Perfect for conference demos**:

```python
# Share tool on HuggingFace Hub
tool = PierresPanelTool()
tool.push_to_hub("username/pierre-panel-tool")

# Attendees can try it
from smolagents import load_tool
tool = load_tool("username/pierre-panel-tool")
```

- Interactive Spaces
- Version control for tools
- Community contributions

### 6. Open Path to Complexity

**Starts simple** (MVP):
```python
agent = CodeAgent(tools=[OneTool()], model=model)
result = agent.run("Extract from screenshot")
```

**Scales to complex** (Phase 2+):
- Multi-agent systems (`managed_agents`)
- Multi-step reasoning (`max_steps`)
- Web agents (`webagent` CLI)
- Gradio UI integration

**No rewrite needed** as requirements grow.

---

## Why NOT Alternatives?

### OpenAI Agents SDK

**Blockers**:
- ⚠️ Designed for GPT-4/5 (may not optimize for Qwen)
- ⚠️ Less explicit VLM support than Smolagents
- ⚠️ More abstraction than needed for single-shot task

**When to use**:
- IF you switch to GPT-5 API
- IF you need built-in sessions/handoffs
- IF you need MCP integration

### Claude Agent SDK

**Blockers**:
- ❌ Requires Claude API (we use Qwen2.5-VL locally)
- ❌ Can't call vLLM-served models
- ❌ Costs API credits

**When to use**:
- IF you switch to Claude API
- IF you need extensive hooks (PreToolUse, PostToolUse)
- IF you need granular permission system

### Raw OpenAI Client

**Not blocked, just less optimal**:
- ⚠️ No built-in error handling
- ⚠️ No observability hooks
- ⚠️ No sandboxing
- ⚠️ Manual everything

**When to use**:
- IF maximum control required
- IF no framework lock-in desired
- IF simplest possible code

**For MVP**: Smolagents provides just enough abstraction without overhead.

---

## When to Reconsider

### Phase 2: Multi-Screen Support

**If routing grows complex**:
- TV dialog tool
- Inventory tooltip tool
- Shop vs dialog vs inventory classification

**Options**:
1. **Stick with Smolagents** - CodeAgent can handle routing in Python code
2. **Add LangGraph** - IF conditional state machine needed

**Decision criteria**: Test Smolagents first. Only add LangGraph if routing logic becomes unmaintainable.

### Phase 3: Validation Agent

**If multi-agent validation needed**:
- Extractor agent
- Validator agent (checks extraction quality)

**Options**:
1. **Smolagents multi-agent** - `managed_agents` feature
2. **CrewAI** - Role-based collaboration

**Decision criteria**: Start with Smolagents multi-agent. Only add CrewAI if collaboration patterns need CrewAI's abstractions.

### Production: Observability Critical

**If observability becomes priority**:
- Claude SDK has best hooks (PreToolUse, PostToolUse, etc.)
- But requires Claude API

**Options**:
1. **Add MLFlow logging** to Smolagents (our approach)
2. **Switch to Claude SDK** IF we adopt Claude API

---

## Implementation Plan

### Module 1-2: Manual → Smolagents

1. Start with manual tool dispatch (understand fundamentals)
2. Introduce Smolagents (automate dispatch)
3. Compare CodeAgent vs ToolCallingAgent
4. Choose CodeAgent (Python code generation)

### Module 3-4: vLLM → Production

1. Connect Smolagents to vLLM via LiteLLMModel
2. Build production VLMOrchestrator class
3. Add error handling, logging, validation
4. Write unit tests with mocking

### Module 5-6: Integration → Demos

1. FastAPI integration
2. End-to-end testing
3. Conference demo scripts
4. Hub tool sharing

---

## Success Metrics

**We'll know Smolagents is working when**:

1. ✅ VLM successfully calls `crop_pierres_detail_panel` tool
2. ✅ Extraction returns valid JSON matching schema
3. ✅ All unit tests pass (mocked VLM)
4. ✅ Integration tests pass (real vLLM)
5. ✅ FastAPI endpoint accepts uploads, returns results
6. ✅ MLFlow logs all tool calls
7. ✅ Conference demos run smoothly

**Red flags** (reconsider framework):
- ❌ Smolagents can't handle vLLM endpoint
- ❌ CodeAgent too slow vs raw client
- ❌ Tool calling unreliable (hallucinations)
- ❌ Documentation too sparse to debug issues

**Mitigation**: Always have raw OpenAI client as fallback.

---

## Decision Log

**2026-03-20**: Chose Smolagents based on:
- VLM-first design
- Model agnostic (Qwen2.5-VL support)
- CodeAgent paradigm (matches philosophy)
- Minimal complexity for MVP
- Conference demo friendly (Hub integrations)

**Alternative considered**: Raw OpenAI client (very close second)

**Deferred decisions**:
- LangGraph: Revisit if Phase 2 routing gets complex
- CrewAI: Revisit if Phase 3 needs multi-agent

**Committed to**: Evaluate empirically in Module 4 (compare frameworks side-by-side)

---

## References

- Full comparison: `../docs/agent-frameworks-compared.md`
- Smolagents quickstart: `smolagents-quickstart.md`
- Best practices: `best-practices-2026.md`
- Curriculum: `../curriculum.md`
