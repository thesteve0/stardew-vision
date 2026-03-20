# Agent/Tool-Calling Learning Curriculum

This directory contains a progressive learning curriculum for agent/tool-calling patterns with VLMs, specifically designed for the Stardew Vision project but portable to other projects.

## Overview

**Primary Framework**: [Smolagents](https://huggingface.co/docs/smolagents) (HuggingFace's agent framework)

**Timeline**: 8-12 hours over 3-4 sessions

**Goal**: Build production-ready VLM orchestrator that classifies screenshots and dispatches tool calls

## Quick Start

1. **Read the framework comparison**: `../docs/agent-frameworks-compared.md`
2. **Install Smolagents**: `uv add 'smolagents[toolkit,litellm]'`
3. **Follow the curriculum**: `curriculum.md` (6 progressive modules)
4. **Run examples**: `examples/module*.py` scripts
5. **Complete exercises**: `exercises/exercise*.md` challenges

## Directory Structure

```
agent-learning/
├── README.md                          # This file - navigation and overview
├── curriculum.md                      # Full learning curriculum (6 modules)
├── docs/
│   ├── smolagents-quickstart.md      # Quick reference for Smolagents
│   ├── best-practices-2026.md        # 2026 agentic workflow patterns
│   └── framework-decision.md         # Why we chose Smolagents (summary)
├── examples/
│   ├── module1_manual_dispatch.py    # Manual tool calling (no framework)
│   ├── module2_smolagents_basic.py   # First Smolagents agent
│   ├── module3_smolagents_vllm.py    # Smolagents + vLLM integration
│   ├── module4_production_wrapper.py # Production VLMOrchestrator
│   ├── module5_fastapi_integration.py # Web endpoint
│   └── module6_conference_demo.py    # Demo progression for talks
├── exercises/
│   ├── exercise1_tool_creation.md    # Create your own tool
│   ├── exercise2_agent_config.md     # Configure agent parameters
│   └── exercise3_debugging.md        # Debug common issues
└── resources/
    ├── smolagents-cheatsheet.md      # Common patterns quick reference
    └── sources.md                     # All web research sources
```

## Modules

### Module 1: Manual Tool Dispatch (1-2 hours)
- Understand OpenAI function-calling format
- Create tool definitions manually
- Build tool registry and dispatcher
- **No framework** - just Python functions

### Module 2: Smolagents Basics (2-3 hours)
- Install Smolagents
- Create custom Tool class
- CodeAgent vs ToolCallingAgent
- First agent with Qwen2.5-VL

### Module 3: Smolagents + vLLM (2-3 hours)
- LiteLLMModel backend for vLLM
- Tool calling via vLLM endpoint
- Debugging and logging

### Module 4: Production Wrapper (2-3 hours)
- VLMOrchestrator using Smolagents
- Error handling and validation
- MLFlow integration
- Testing strategies

### Module 5: FastAPI Integration (1-2 hours)
- Connect orchestrator to web app
- File upload handling
- Async patterns

### Module 6: Advanced & Alternatives (1-2 hours)
- When to use raw client instead
- When to add LangGraph (Phase 2+)
- Conference demo scripts
- Hub tool sharing

## Prerequisites

**Technical**:
- Python 3.10+
- PyTorch 2.9.1 (ROCm 7.2)
- Qwen2.5-VL-7B-Instruct model downloaded
- vLLM 0.7.x installed
- Stardew Vision extraction tool working (`crop_pierres_detail_panel`)

**Knowledge**:
- Basic Python (functions, classes, async/await)
- REST API concepts
- Basic ML concepts (models, inference)
- Familiarity with OpenAI API (helpful but not required)

## Installation

```bash
# Install Smolagents with all backends
uv add 'smolagents[toolkit,litellm]'

# Optional: Install comparison frameworks (Module 4)
uv add openai-agents  # OpenAI Agents SDK
uv add langgraph      # LangGraph (for future)

# Verify installation
python -c "import smolagents; print(smolagents.__version__)"
```

## How to Use This Curriculum

### Multi-Session Approach (Recommended)

**Session 1** (3-4 hours):
- Modules 1-2: Manual dispatch + Smolagents basics
- **Checkpoint**: CodeAgent successfully calls tool

**Session 2** (3-4 hours):
- Modules 3-4: vLLM integration + production wrapper
- **Checkpoint**: VLMOrchestrator passes all tests

**Session 3** (2-3 hours):
- Modules 5-6: FastAPI integration + advanced topics
- **Checkpoint**: End-to-end web app working

### Single Intensive Session (8-12 hours)

Work through all modules sequentially. Take breaks between modules to review and consolidate learning.

### Self-Paced

- Each module is independent
- Can pause/resume at any checkpoint
- Examples run standalone for quick testing
- Exercises for hands-on practice

## Verification

After each module, verify your understanding:

**Module 1**: `python examples/module1_manual_dispatch.py` → JSON output

**Module 2**: `python examples/module2_smolagents_basic.py` → CodeAgent executes tool

**Module 3**:
```bash
# Terminal 1: Start vLLM
vllm serve models/base/Qwen2.5-VL-7B-Instruct --port 8001 --dtype float16

# Terminal 2: Test
python examples/module3_smolagents_vllm.py
```

**Module 4**: `pytest tests/test_vlm_wrapper.py -v` → All tests pass

**Module 5**:
```bash
# Terminal 1: vLLM (keep running)
# Terminal 2: Start webapp
uvicorn stardew_vision.webapp.app:app --port 8000

# Terminal 3: Test upload
curl -X POST http://localhost:8000/analyze -F "file=@tests/fixtures/pierre_shop_001.png"
```

**Module 6**: `python examples/module6_conference_demo.py` → All demos execute

## Learning Outcomes

By the end of this curriculum, you will:

1. ✅ Understand agent/tool-calling architecture patterns
2. ✅ Master Smolagents framework for VLM tool calling
3. ✅ Know when to use frameworks vs raw client
4. ✅ Build production-ready VLM orchestrator
5. ✅ Integrate agent with FastAPI web app
6. ✅ Debug VLM tool calling issues
7. ✅ Apply 2026 best practices (observability, structured outputs, guardrails)
8. ✅ Make informed decisions about framework choice

## Production Deliverables

This curriculum produces production code for Stardew Vision:

1. `src/stardew_vision/models/vlm_wrapper.py` - VLMOrchestrator class
2. `src/stardew_vision/webapp/routes.py` - FastAPI endpoints
3. `tests/test_vlm_wrapper.py` - Unit tests
4. `scripts/demo_progression.py` - Conference demo

## Conference Demo Materials

The curriculum includes materials for giving talks:

- **Demo progression**: Manual → VLM → Integrated (Module 6)
- **Framework comparison**: Decision rationale with code examples
- **Best practices**: 2026 agentic workflow patterns
- **Live coding**: Start from scratch to working agent in 15 minutes

## Troubleshooting

### Common Issues

**Smolagents import error**:
```bash
# Reinstall with correct extras
uv add 'smolagents[toolkit,litellm]'
```

**vLLM connection refused**:
```bash
# Check vLLM is running on port 8001
curl http://localhost:8001/v1/models
```

**Tool not found**:
```python
# Verify tool is in registry
from stardew_vision.tools import TOOL_REGISTRY
print(TOOL_REGISTRY.keys())
```

**ROCm GPU not found**:
```bash
# Check GPU access
rocm-smi
```

### Getting Help

1. **Check the docs**: `docs/smolagents-quickstart.md` for quick reference
2. **Review exercises**: `exercises/*.md` for hands-on practice
3. **Debug systematically**: Use logging and print statements
4. **Test incrementally**: Each module builds on previous

## Alternative Paths

### Want maximum control?

Skip Smolagents and use **raw OpenAI client**:
- See `examples/module1_manual_dispatch.py` extended version
- Use `AsyncOpenAI` directly with manual tool dispatch
- Less abstraction, more control

### Want state machines?

Add **LangGraph** in Phase 2+:
- Conditional routing for multi-screen support
- State management for complex workflows
- See `docs/best-practices-2026.md` for when to use

### Want multi-agent?

Explore **CrewAI** in Phase 3+:
- Extractor agent + Validator agent
- Role-based collaboration
- See `docs/agent-frameworks-compared.md` for comparison

## Additional Resources

**Official Smolagents**:
- [Main Documentation](https://huggingface.co/docs/smolagents/index)
- [Guided Tour](https://huggingface.co/docs/smolagents/guided_tour)
- [Building Good Agents](https://huggingface.co/docs/smolagents/tutorials/building_good_agents)
- [Tools Conceptual Guide](https://huggingface.co/docs/smolagents/main/en/conceptual_guides/tools)

**Project Documentation**:
- `../docs/agent-frameworks-compared.md` - Comprehensive framework comparison
- `../docs/adr/009-agent-tool-calling-architecture.md` - Architecture decisions
- `../docs/plan.md` - Overall project plan

**Research Sources**:
- `resources/sources.md` - All research links and references

## Next Steps

1. ✅ Read this README (you're here!)
2. Read `curriculum.md` for detailed module breakdown
3. Read `../docs/agent-frameworks-compared.md` for context
4. Install Smolagents: `uv add 'smolagents[toolkit,litellm]'`
5. Start Module 1: `examples/module1_manual_dispatch.py`
6. Work through modules sequentially
7. Complete exercises for practice
8. Build production VLMOrchestrator
9. Integrate with FastAPI
10. Prepare conference demos

**Happy learning!** 🚀
