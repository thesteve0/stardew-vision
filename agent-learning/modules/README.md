# Learning Modules

Comprehensive, step-by-step guides for each curriculum module with diagrams, code walkthroughs, and hands-on activities.

## Overview

Each module document includes:

- **Learning objectives** - Clear goals
- **Conceptual overview** - "What" and "why" explanations
- **Diagrams** - ASCII art showing architecture and flow
- **Code walkthrough** - Line-by-line explanations with references to example code
- **Key patterns** - Best practices and anti-patterns
- **Hands-on activities** - Checkpoints and exercises
- **Common pitfalls** - Mistakes to avoid
- **Summary** - Key takeaways and next steps

## Modules

### ✅ Module 1: Manual Tool Dispatch
**File**: [`module1-manual-dispatch.md`](module1-manual-dispatch.md)
**Duration**: 1-2 hours
**Status**: Complete

Understanding OpenAI function-calling without frameworks:
- Tool definitions in JSON
- Manual registry and dispatcher
- VLM response parsing
- Foundation for everything else

**Diagrams**:
- Complete tool-calling flow (6 phases)
- Before/after framework comparison

### ✅ Module 2: Smolagents Basics
**File**: [`module2-smolagents-basics.md`](module2-smolagents-basics.md)
**Duration**: 2-3 hours
**Status**: Complete

Introduction to Smolagents framework:
- Tool classes (definition + implementation)
- CodeAgent vs ToolCallingAgent
- InferenceClientModel backend
- Automated dispatch

**Diagrams**:
- CodeAgent execution flow
- Comparison table (manual vs framework)

### 🚧 Module 3: vLLM Integration
**File**: `module3-vllm-integration.md`
**Duration**: 2-3 hours
**Status**: Planned

Production serving with vLLM:
- Start vLLM server
- LiteLLMModel backend
- OpenAI-compatible API
- Same code, different endpoint

### 🚧 Module 4: Production Wrapper
**File**: `module4-production-wrapper.md`
**Duration**: 2-3 hours
**Status**: Planned

Building VLMOrchestrator:
- Error handling
- MLFlow integration
- Unit testing with mocks
- Observability patterns

### 🚧 Module 5: FastAPI Integration
**File**: `module5-fastapi-integration.md`
**Duration**: 1-2 hours
**Status**: Planned

Web endpoint integration:
- File upload handling
- Async patterns
- Health checks
- OpenAPI docs

### 🚧 Module 6: Conference Demos
**File**: `module6-conference-demos.md`
**Duration**: 1-2 hours
**Status**: Planned

Advanced topics and demo materials:
- When to use raw client
- When to add LangGraph
- Demo progression script
- Hub tool sharing

## How to Use

### Linear Path (Recommended)
Read modules sequentially:
1. Module 1 → Understand fundamentals
2. Module 2 → Learn Smolagents
3. Module 3 → Add production serving
4. Module 4 → Add observability
5. Module 5 → Web integration
6. Module 6 → Advanced topics

### Reference Path
Jump to specific topics:
- Need to understand Tool classes? → Module 2
- Need to set up vLLM? → Module 3
- Need error handling patterns? → Module 4
- Need FastAPI integration? → Module 5

### Study Path
Read alongside example code:
1. Open module document
2. Open corresponding `examples/moduleX.py`
3. Read document section
4. Find referenced lines in code
5. Run example to verify understanding

## Diagrams

All ASCII diagrams are in [`../diagrams/`](../diagrams/):

- `tool-calling-flow.txt` - Complete end-to-end flow
- `codeagent-execution.txt` - How CodeAgent works
- `vllm-architecture.txt` - vLLM serving architecture (planned)
- `production-pipeline.txt` - Full production flow (planned)
- `fastapi-integration.txt` - Web API flow (planned)
- `phase-progression.txt` - MVP → Phase 2 → Phase 3 (planned)

## Module Format

Each module follows this structure:

```markdown
# Module X: Title

**Duration**: X-Y hours
**Prerequisites**: Previous modules, required knowledge
**Example Code**: Link to examples/moduleX.py

## Learning Objectives
- Clear, testable objectives

## Why [Topic]?
- Motivation and context
- Real-world analogy

## Conceptual Overview
- "What is this?"
- ASCII diagrams
- Flow charts

## Code Walkthrough
- Part 1: Component A (lines X-Y)
  - Code snippet
  - Line-by-line explanation
- Part 2: Component B (lines Z-W)
  - Code snippet
  - Detailed breakdown

## Hands-On Activity
- Checkpoint 1: Run the example
- Checkpoint 2: Modify parameters
- Checkpoint 3: Create your own

## Key Patterns
- Pattern 1: Best practice
- Pattern 2: Common approach
- Pattern 3: Anti-pattern to avoid

## Common Pitfalls
- Pitfall 1: Mistake + fix
- Pitfall 2: Mistake + fix

## Key Takeaways
- Summary of learning
- Connection to next module

## Additional Resources
- Related code
- Exercises
- Official docs
```

## Features

### 1. Line Number References
All code walkthroughs reference specific lines:
```markdown
### Part 3: Manual Dispatcher (Lines 74-107)
```

This lets you:
- Find exact code being discussed
- Navigate between document and code
- Verify explanations against implementation

### 2. Progressive Diagrams
Diagrams build on each other:
- Module 1: Basic tool calling flow
- Module 2: Add CodeAgent execution
- Module 3: Add vLLM serving
- Module 4: Add observability layer

### 3. Checkpoint-Based Learning
Each module has verification checkpoints:
```markdown
### Checkpoint 1: Run the Example
Expected output: ...
What to observe: ...

### Checkpoint 2: Modify Parameters
Try changing X, see how Y responds

### Checkpoint 3: Create Your Own
Build Z using pattern from Part N
```

### 4. Comparison Tables
Visual comparisons of approaches:
```
┌────────────┬─────────────────┬───────────────────┐
│ Aspect     │ Module 1        │ Module 2          │
├────────────┼─────────────────┼───────────────────┤
│ Dispatch   │ Manual          │ Automated         │
│ Code       │ ~20 lines       │ ~5 lines          │
└────────────┴─────────────────┴───────────────────┘
```

### 5. "Why" Explanations
Not just "how" but "why":
- Why start manual? (Understanding fundamentals)
- Why Smolagents? (VLM-first design)
- Why CodeAgent? (Composability and type safety)
- Why vLLM? (Production serving)

## Connection to Other Materials

### Examples
Each module references corresponding example file:
- Module 1 → `examples/module1_manual_dispatch.py`
- Module 2 → `examples/module2_smolagents_basic.py`
- etc.

### Exercises
Hands-on practice linked from modules:
- Exercise 1: Create custom tools
- Exercise 2: Configure agent parameters
- Exercise 3: Debug common issues

### Curriculum
High-level overview in [`curriculum.md`](../curriculum.md):
- Learning objectives
- Time estimates
- Verification steps

### Quick Reference
Cheat sheets in [`docs/`](../docs/):
- `smolagents-quickstart.md` - Common patterns
- `best-practices-2026.md` - Production patterns
- `framework-decision.md` - Why Smolagents

## Progress Tracking

As you complete modules, check them off:

- [x] Module 1: Manual Tool Dispatch
- [x] Module 2: Smolagents Basics
- [ ] Module 3: vLLM Integration
- [ ] Module 4: Production Wrapper
- [ ] Module 5: FastAPI Integration
- [ ] Module 6: Conference Demos

## Feedback

These modules are designed to be:
- **Self-contained** - Each module stands alone
- **Practical** - Focused on working code, not theory
- **Progressive** - Each builds on previous
- **Reference-friendly** - Easy to jump to specific topics

Found an issue? Have a suggestion? The modules are living documents and can be updated.

---

**Ready to start?** → Begin with [`module1-manual-dispatch.md`](module1-manual-dispatch.md)
