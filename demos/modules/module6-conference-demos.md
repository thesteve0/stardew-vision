# Module 6: Conference Demos & Advanced Topics

**Duration**: 1-2 hours
**Prerequisites**: Modules 1-5 completed
**Example Code**: [`examples/module6_conference_demo.py`](../examples/module6_conference_demo.py)

---

## Learning Objectives

By the end of this module, you will:

- ✅ Understand when to use raw client vs Smolagents
- ✅ Know when to add LangGraph (Phase 2+)
- ✅ Create compelling conference demo progressions
- ✅ Share tools on HuggingFace Hub
- ✅ Make informed framework decisions

---

## Decision Framework: Choosing the Right Tools

After learning manual dispatch → Smolagents → vLLM → production wrapper, you might wonder: *"When do I use each approach?"*

### The Complexity Ladder

```
COMPLEXITY                         WHEN TO USE
───────────                        ───────────

Simple                 Raw Client
│                      └─ Single tool
│                      └─ Full control needed
│                      └─ No framework lock-in
│
│                      Smolagents
│                      └─ Multiple tools
│                      └─ VLM-specific features
├─ MVP ────────────────└─ Standard use case
│
│                      Smolagents + LangGraph
│                      └─ Conditional routing
│                      └─ State machines
│                      └─ Multi-step workflows
│
│                      Smolagents + Multi-Agent
│                      └─ Validator agent
│                      └─ Role-based workflow
Complex               └─ Collaboration patterns


DON'T START HERE! ───────────────────────────
Work your way UP the ladder as complexity demands it.
```

### Decision Tree

```
START: Do you need agent/tool-calling?
│
├─ NO → Use standard ML pipeline
│        (e.g., just PaddleOCR, no VLM)
│
└─ YES → Continue
         │
         ├─ Single tool, maximum control?
         │  └─ YES → Raw OpenAI client
         │           (Module 1 extended)
         │
         └─ NO → Multiple tools needed
                 │
                 ├─ Vision/video/audio?
                 │  └─ YES → Smolagents
                 │           (Modules 2-3)
                 │
                 └─ NO → Consider LangChain
                         (better for pure text)

         Multi-screen support needed?
         │
         ├─ Simple IF/ELSE routing?
         │  └─ YES → Smolagents with conditional logic
         │           (Module 4-5 + Python conditionals)
         │
         └─ NO → Complex state machine?
                 └─ YES → Add LangGraph
                         (Phase 2 of Stardew Vision)

         Need validation/quality checks?
         │
         └─ YES → Multi-agent pattern
                  └─ Extractor agent + Validator agent
                  └─ Use Smolagents multi-agent
                  └─ Phase 3 of Stardew Vision
```

---

## When to Use Each Approach

### Raw OpenAI Client

**Use when**:
- ✅ Single tool, simple dispatch
- ✅ Maximum control required
- ✅ Don't want framework dependencies
- ✅ Minimalist approach

**Code example**:
```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8001/v1", api_key="EMPTY")

tools = [
    {
        "type": "function",
        "function": {
            "name": "crop_pierres_detail_panel",
            "description": "...",
            "parameters": {...}
        }
    }
]

response = client.chat.completions.create(
    model="Qwen2.5-VL-7B-Instruct",
    messages=[{"role": "user", "content": "Extract from screenshot"}],
    tools=tools
)

# Manual dispatch (like Module 1)
tool_call = response.choices[0].message.tool_calls[0]
result = TOOL_REGISTRY[tool_call.function.name](**json.loads(tool_call.function.arguments))
```

**When NOT to use**:
- ❌ Multiple tools (tedious manual dispatch)
- ❌ Multi-modal (vision/audio) - Smolagents handles better
- ❌ Multi-step reasoning - Smolagents automates

**Stardew Vision decision**: We chose Smolagents because:
- Multiple tools (pierre_shop, tv_dialog, inventory)
- Vision-first (screenshots)
- Multi-step (classify → extract)

### Smolagents

**Use when** (our choice):
- ✅ Multiple tools
- ✅ Vision/video/audio input
- ✅ VLM-optimized needed
- ✅ Want abstraction without over-engineering

**Code example** (from Modules 2-5):
```python
from smolagents import CodeAgent, LiteLLMModel

model = LiteLLMModel(base_url="http://localhost:8001/v1", api_key="EMPTY")
agent = CodeAgent(tools=[Tool1(), Tool2(), Tool3()], model=model)

result = agent.run("Classify and extract from screenshot")
# All dispatch, multi-step reasoning automated
```

**When NOT to use**:
- ❌ Pure text (LangChain better ecosystem)
- ❌ Need complex state machines (add LangGraph)
- ❌ Simple single-tool case (raw client simpler)

### Smolagents + LangGraph

**Use when** (Phase 2 of Stardew Vision):
- ✅ Complex conditional routing needed
- ✅ State machine workflows
- ✅ Multi-step with branching logic

**Example scenario**:
```
Screenshot → Classify screen type
    │
    ├─ pierre_shop → Extract shop details
    │                └─ Validate fields
    │                    └─ If missing → Re-extract
    │
    ├─ tv_dialog → Extract dialog text
    │              └─ Sentiment analysis
    │
    └─ inventory → Extract items
                   └─ Count items
                   └─ If >50 items → Summarize
```

**Code example**:
```python
from langgraph.graph import StateGraph

# Define states
class AgentState(TypedDict):
    screenshot: str
    screen_type: str
    extraction: dict
    validated: bool

# Define nodes
def classify_node(state):
    screen_type = classify_tool(state["screenshot"])
    return {"screen_type": screen_type}

def extract_node(state):
    if state["screen_type"] == "pierre_shop":
        result = pierre_tool(state["screenshot"])
    elif state["screen_type"] == "tv_dialog":
        result = tv_tool(state["screenshot"])
    return {"extraction": result}

def validate_node(state):
    is_valid = validate_tool(state["extraction"])
    return {"validated": is_valid}

# Build graph
graph = StateGraph(AgentState)
graph.add_node("classify", classify_node)
graph.add_node("extract", extract_node)
graph.add_node("validate", validate_node)

# Define edges (conditional routing)
graph.add_edge("classify", "extract")
graph.add_conditional_edges(
    "extract",
    lambda state: "validate" if state["extraction"] else "retry"
)

# Compile and run
app = graph.compile()
result = app.invoke({"screenshot": "image.png"})
```

**When NOT to use**:
- ❌ Simple linear flow (Smolagents alone is fine)
- ❌ No conditional logic needed
- ❌ Adds complexity without benefit

**Stardew Vision Phase 2**: We'll add LangGraph when we have 3+ screen types with different validation logic.

### Multi-Agent (CrewAI or Smolagents)

**Use when** (Phase 3 of Stardew Vision):
- ✅ Need validation/quality checks
- ✅ Role-based workflows (extractor, validator, summarizer)
- ✅ Collaboration between agents

**Example scenario**:
```
Extractor Agent: "I extracted: name=Parsnip, price=20"
    ↓
Validator Agent: "Field 'description' is missing. Re-extract."
    ↓
Extractor Agent: "Re-running tool... now I have description."
    ↓
Validator Agent: "All fields present. Quality score: 0.95"
    ↓
Return validated result
```

**Code example** (Smolagents multi-agent):
```python
from smolagents import CodeAgent, LiteLLMModel

# Extractor agent
extractor = CodeAgent(
    tools=[CropPierresPanelTool()],
    model=model,
    system_prompt="You extract data accurately from screenshots."
)

# Validator agent
validator = CodeAgent(
    tools=[ValidateExtractionTool()],
    model=model,
    system_prompt="You validate extractions and identify missing fields."
)

# Orchestrator
extraction = extractor.run("Extract from screenshot")
validation = validator.run(f"Validate this extraction: {extraction}")

if validation["is_valid"]:
    return extraction
else:
    # Re-extract with hints
    extraction = extractor.run(f"Re-extract, focusing on: {validation['missing_fields']}")
```

**When NOT to use**:
- ❌ Single-pass extraction is good enough
- ❌ No quality issues in practice
- ❌ Adds latency (2x VLM calls)

**Stardew Vision Phase 3**: We'll add validator agent if extraction accuracy < 95%.

---

## Conference Demo Progression

The best way to explain this curriculum is through a **progressive demo** showing evolution from manual to intelligent to production.

### Demo Structure (50 minutes)

**Part 1: The Problem** (5 min)
- Show Stardew Valley screenshot
- "Visually impaired players can't read item details"
- "We need to extract text and convert to audio"

**Part 2: Manual Solution** (5 min)
- Demo: `examples/module1_manual_dispatch.py`
- "Here's OpenCV + PaddleOCR extraction"
- "But what if screen type changes? We need classification."

**Part 3: Adding Intelligence** (10 min)
- Demo: `examples/module2_smolagents_basic.py`
- "VLM classifies screen type automatically"
- "Smolagents dispatches correct tool"
- "Show CodeAgent writing Python code"

**Part 4: Production Speed** (10 min)
- Demo: `examples/module3_smolagents_vllm.py`
- "Local vLLM for 2-4x faster inference"
- "Same code, different backend"
- "Show latency comparison: 5s → 1.5s"

**Part 5: Production Reliability** (10 min)
- Demo: `examples/module4_production_wrapper.py`
- "Error handling, validation, logging"
- "MLFlow observability"
- "Show test suite: unit + integration"

**Part 6: User-Facing API** (5 min)
- Demo: `examples/module5_fastapi_integration.py`
- "Web upload → extraction → JSON response"
- "Show Swagger docs at /docs"
- "Live demo: upload screenshot, get result"

**Part 7: Decision Framework** (5 min)
- "When to use each approach?"
- Show decision tree diagram
- "Start simple, add complexity as needed"

### Demo Script

**File**: `examples/module6_conference_demo.py`

```python
"""
Conference demo progression.
Shows evolution from manual to intelligent to integrated.
"""

def demo_1_manual():
    """Demo 1: Manual tool dispatch (no AI)."""
    print("\n" + "=" * 80)
    print("DEMO 1: MANUAL TOOL DISPATCH (No AI)")
    print("=" * 80)
    print()
    print("Starting point:")
    print("  - Tool definitions in JSON")
    print("  - Manual registry lookup")
    print("  - No intelligence, just dispatch")
    print()

    from stardew_vision.tools import crop_pierres_detail_panel
    result = crop_pierres_detail_panel(
        "/workspaces/stardew-vision/tests/fixtures/pierre_shop_001.png"
    )
    print("Result:", result)
    print()
    print("✅ Works, but requires manual classification")
    print("❌ What if screen type changes? We'd need to hardcode logic.")

def demo_2_smolagents():
    """Demo 2: Smolagents CodeAgent (AI-powered)."""
    print("\n" + "=" * 80)
    print("DEMO 2: SMOLAGENTS CODEAGENT (AI-Powered)")
    print("=" * 80)
    print()
    print("Adding VLM intelligence:")
    print("  - CodeAgent writes Python code")
    print("  - Automatically picks correct tool")
    print("  - VLM-optimized (vision, video, audio)")
    print()

    from smolagents import CodeAgent, LiteLLMModel
    from stardew_vision.models.vlm_wrapper import PierresPanelTool

    model = LiteLLMModel(
        model_id="Qwen2.5-VL-7B-Instruct",
        base_url="http://localhost:8001/v1",
        api_key="EMPTY"
    )
    agent = CodeAgent(tools=[PierresPanelTool()], model=model, verbosity=0)

    result = agent.run(
        "Extract information from /workspaces/stardew-vision/tests/fixtures/pierre_shop_001.png"
    )
    print("Result:", result)
    print()
    print("✅ VLM decides which tool to call!")
    print("✅ No hardcoded if/else logic")

def demo_3_production():
    """Demo 3: Production FastAPI integration."""
    print("\n" + "=" * 80)
    print("DEMO 3: PRODUCTION FASTAPI INTEGRATION")
    print("=" * 80)
    print()
    print("Full production pipeline:")
    print("  - FastAPI web endpoint")
    print("  - Automatic error handling")
    print("  - MLFlow observability")
    print("  - Ready for Phase 2: TTS → audio response")
    print()
    print("Upload screenshot:")
    print("  curl -X POST http://localhost:8000/api/v1/analyze \\")
    print("    -F 'file=@screenshot.png'")
    print()
    print("Returns:")
    print("  {")
    print("    \"success\": true,")
    print("    \"extraction\": {\"name\": \"Parsnip\", ...},")
    print("    \"audio_url\": \"/audio/result.wav\"  # Phase 2")
    print("  }")
    print()
    print("✅ Production-ready accessibility tool!")

def demo_4_framework_decision():
    """Demo 4: Why Smolagents over alternatives."""
    print("\n" + "=" * 80)
    print("DEMO 4: FRAMEWORK DECISION RATIONALE")
    print("=" * 80)
    print()
    print("Why Smolagents?")
    print("  ✅ VLM-first design (not retrofitted)")
    print("  ✅ Model-agnostic (Qwen, GPT, Claude, local)")
    print("  ✅ CodeAgent writes Python (robust)")
    print("  ✅ Hub integrations (conference friendly)")
    print("  ✅ Minimal complexity (~1000 LOC)")
    print("  ✅ Clear path to complexity (multi-agent, multi-step)")
    print()
    print("When to use alternatives:")
    print("  - Raw client: Maximum control, single tool")
    print("  - LangGraph: Complex state machines (Phase 2+)")
    print("  - CrewAI: Multi-agent collaboration (Phase 3+)")
    print()
    print("Decision principle:")
    print("  ⚡ Start simple, add complexity as needed")
    print("  ⚡ Don't anticipate complexity, respond to it")

if __name__ == "__main__":
    import sys

    # Check vLLM for demo 2+
    if len(sys.argv) > 1 and sys.argv[1] != "1":
        import requests
        try:
            requests.get("http://localhost:8001/v1/models", timeout=2)
        except:
            print("❌ Demos 2+ require vLLM server running")
            print("Start with: vllm serve models/base/Qwen2.5-VL-7B-Instruct --port 8001 --dtype float16 --enable-tool-calling")
            sys.exit(1)

    # Run all demos
    demo_1_manual()
    demo_2_smolagents()
    demo_3_production()
    demo_4_framework_decision()

    print("\n" + "=" * 80)
    print("✅ ALL DEMOS COMPLETE!")
    print("=" * 80)
    print()
    print("Key takeaways:")
    print("  1. Manual dispatch teaches fundamentals")
    print("  2. Smolagents adds intelligence without complexity")
    print("  3. Production wrapper adds reliability")
    print("  4. Choose tools based on ACTUAL needs, not anticipated")
```

---

## Hub Tool Sharing

Share your tools on HuggingFace Hub for the community:

### Publishing a Tool

```python
from smolagents import Tool

class PierresPanelTool(Tool):
    name = "crop_pierres_detail_panel"
    description = "Extract item details from Pierre's General Store detail panel in Stardew Valley screenshots"
    inputs = {
        "image_path": {"type": "string", "description": "Path to screenshot"}
    }
    output_type = "dict"

    def forward(self, image_path: str):
        from stardew_vision.tools import crop_pierres_detail_panel
        return crop_pierres_detail_panel(image_path)

# Push to Hub
tool = PierresPanelTool()
tool.push_to_hub("your-username/pierre-panel-tool")
```

### Using a Hub Tool

```python
from smolagents import load_tool

# Load from Hub
tool = load_tool("your-username/pierre-panel-tool")

# Use in agent
agent = CodeAgent(tools=[tool], model=model)
```

**Benefits**:
- ✅ Community can use your tools
- ✅ Version control
- ✅ Discoverability
- ✅ Reusability across projects

---

## Hands-On Activity

### Checkpoint 1: Run Demo Progression

```bash
# Terminal 1: vLLM (keep running)
vllm serve models/base/Qwen2.5-VL-7B-Instruct \
  --port 8001 --dtype float16 --enable-tool-calling

# Terminal 2: Run demo script
cd /workspaces/stardew-vision
python agent-learning/examples/module6_conference_demo.py
```

**Expected output**:
- All 4 demos execute
- Shows progression clearly
- Framework rationale explained

### Checkpoint 2: Prepare Conference Talk

**Create presentation outline**:

1. **Title slide**: "Building Accessible Gaming Tools with VLMs and Smolagents"

2. **Problem statement** (1 slide):
   - Screenshot showing Pierre's shop
   - "Visually impaired players can't read this"

3. **Solution architecture** (1 slide):
   - Diagram: Screenshot → VLM → Tool → TTS → Audio

4. **Live demo progression** (10 minutes):
   - Run `demo_1_manual()`
   - Run `demo_2_smolagents()`
   - Run `demo_3_production()`
   - Show actual extraction results

5. **Technical deep dive** (3 slides):
   - Slide 1: Tool calling flow diagram
   - Slide 2: CodeAgent execution
   - Slide 3: Production architecture

6. **Framework decision** (1 slide):
   - Decision tree
   - "Start simple, add complexity as needed"

7. **Results** (1 slide):
   - Performance metrics (latency, accuracy)
   - MLFlow screenshots

8. **Roadmap** (1 slide):
   - Phase 1: Pierre's shop ✅
   - Phase 2: Multi-screen support
   - Phase 3: Multi-agent validation

9. **Q&A**

### Checkpoint 3: Practice Decision Framework

**Scenario 1**: New project - recipe extraction from food blog screenshots

**Question**: Which approach?

**Answer**:
- Input: Images (screenshots)
- Task: Extract structured data (recipe)
- Tools: 1 extraction tool
- Complexity: Simple

**Recommendation**: Start with **Smolagents** (VLM-optimized, single tool is fine)

**Scenario 2**: Extend to 5 different blog layouts

**Question**: Add LangGraph?

**Answer**:
- If conditional logic is simple: No, use Python if/else
- If complex state machine: Yes, add LangGraph

**Start simple, add when needed!**

---

## Key Patterns

### Pattern 1: Progressive Demo

```
Simple → Intelligent → Production

Demo 1: "Here's the manual approach"
Demo 2: "Now let's add intelligence"
Demo 3: "Here's production-ready"
Demo 4: "When to choose each"
```

**Why this works**:
- Shows evolution, not just final state
- Audience understands trade-offs
- Clear decision-making process

### Pattern 2: Decision Documentation

```python
# Good: Document why you chose an approach
"""
We chose Smolagents because:
1. VLM-first design for screenshots
2. Multiple tools (pierre_shop, tv_dialog, inventory)
3. Hub integrations for sharing

We'll add LangGraph in Phase 2 when we have:
- 3+ screen types with different validation rules
- Conditional routing based on screen classification

See docs/framework-decision.md for details.
"""
```

### Pattern 3: Complexity Budget

```
Phase 1 (MVP):
  - Smolagents + single tool ✅
  - Total complexity: LOW

Phase 2 (Multi-screen):
  - Smolagents + 3 tools + simple routing ✅
  - Add LangGraph only if routing logic > 20 lines
  - Total complexity: MEDIUM

Phase 3 (Validation):
  - Add validator agent only if accuracy < 95% ✅
  - Total complexity: MEDIUM-HIGH
```

**Always ask**: "Is this complexity earning its keep?"

---

## Key Takeaways

### 1. Choose Based on Actual Needs

❌ "We might need state machines later, so let's use LangGraph now"
✅ "We need state machines now (3+ screens), so let's add LangGraph"

**Avoid premature complexity.**

### 2. Demo Progression Tells a Story

Don't just show final product. Show:
1. The problem
2. Simple solution
3. Intelligent solution
4. Production solution
5. Decision rationale

### 3. Framework Minimalism

**Smolagents**: ~1,000 LOC
**LangChain**: ~50,000 LOC

**Implication**: Start with minimal framework. Add complexity only when needed.

### 4. Document Decisions

Future you (and teammates) will ask: "Why did we choose X?"

Write it down:
- `docs/framework-decision.md`
- `docs/adr/009-agent-tool-calling-architecture.md`

### 5. Community Sharing

Share tools on HuggingFace Hub:
- Others can use your work
- You get feedback
- Builds portfolio

---

## Summary

You now understand:

1. ✅ **Decision framework** - When to use raw client vs Smolagents vs LangGraph
2. ✅ **Conference demos** - Progressive storytelling (manual → intelligent → production)
3. ✅ **Hub sharing** - Publish tools for community
4. ✅ **Complexity management** - Start simple, add as needed
5. ✅ **Documentation** - Record decisions for future reference

**The complete curriculum**:
- Module 1: Manual dispatch (fundamentals) ✅
- Module 2: Smolagents (automation) ✅
- Module 3: vLLM (production speed) ✅
- Module 4: VLMOrchestrator (reliability) ✅
- Module 5: FastAPI (web interface) ✅
- Module 6: Advanced topics (decision-making) ✅

**You've completed the agent/tool-calling learning curriculum!** 🎉

---

## Next Steps

### Immediate Actions

1. **Implement VLMOrchestrator** in `src/stardew_vision/models/vlm_wrapper.py`
2. **Implement FastAPI routes** in `src/stardew_vision/webapp/routes.py`
3. **Write tests** in `tests/test_vlm_wrapper.py` and `tests/test_api.py`
4. **Run end-to-end test**: Upload → VLM → Extraction → JSON

### Short-term (This Week)

1. Fine-tune Qwen2.5-VL on tool-calling pairs
2. Add MeloTTS integration (audio output)
3. Create conference demo slides
4. Test on multiple Pierre's shop screenshots

### Medium-term (This Month)

1. Add TV dialog extraction tool (Phase 2)
2. Evaluate need for LangGraph (conditional routing)
3. Deploy to OpenShift AI (KServe)
4. Create HuggingFace Space for demos

### Long-term (This Quarter)

1. Multi-agent validation (Phase 3)
2. Feast feature store integration
3. Community contributions (Hub tools)
4. Conference presentations

---

## Portability

This entire `agent-learning/` curriculum is **portable**:

- ✅ Copy to other projects
- ✅ Share with colleagues
- ✅ Use as template for VLM projects
- ✅ Adapt for different domains

**Stardew Vision is the example**, but the patterns apply to any VLM tool-calling project.

---

## Additional Resources

**Code**:
- Full demo script: [`examples/module6_conference_demo.py`](../examples/module6_conference_demo.py)

**Diagrams**:
- [`diagrams/phase-progression.txt`](../diagrams/phase-progression.txt) - MVP → Phase 2 → Phase 3

**Documentation**:
- [`docs/framework-decision.md`](../docs/framework-decision.md) - Why Smolagents
- [`docs/best-practices-2026.md`](../docs/best-practices-2026.md) - Production patterns

**Official Docs**:
- [Smolagents Documentation](https://huggingface.co/docs/smolagents)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [CrewAI Documentation](https://docs.crewai.com/)

---

## Congratulations! 🎉

You've completed the agent/tool-calling learning curriculum!

**You've mastered**:
- ✅ OpenAI function-calling fundamentals
- ✅ Smolagents framework
- ✅ vLLM production serving
- ✅ Error handling and observability
- ✅ Web API integration
- ✅ Framework decision-making

**You can now**:
- Build production VLM systems
- Make informed framework choices
- Give conference talks on the topic
- Contribute to the community

**Go build something amazing!** 🚀

---

**Questions? Feedback?** Review the curriculum, run the examples, and experiment with the patterns.

**Ready to contribute?** Share your tools on HuggingFace Hub and help the community!
