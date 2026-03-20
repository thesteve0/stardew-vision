"""
Module 6: Conference Demo & Advanced Topics

Purpose: Create compelling demo progression for conference talks.
Show evolution from manual to intelligent to production-ready system.

Prerequisites:
- Completed Module 1-5
- All production code implemented

What you'll learn:
- Conference demo narrative arc
- When to use alternatives (raw client, LangGraph, CrewAI)
- Hub tool sharing for community contributions
- Future enhancements (Phase 2+)
"""

import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


def demo_1_manual():
    """Demo 1: Manual tool dispatch (no AI)."""
    print("\n" + "=" * 80)
    print("DEMO 1: MANUAL TOOL DISPATCH (Pre-AI Baseline)")
    print("=" * 80)
    print()
    print("🎯 Point: This is where we started")
    print()

    print("The problem:")
    print("  - Visually impaired players can't read Pierre's shop UI")
    print("  - Manual narration required for each screenshot")
    print()

    print("The manual solution:")
    print("  - Extract text with OpenCV + PaddleOCR")
    print("  - Parse fields (name, description, price)")
    print("  - Works, but requires knowing which screen type")
    print()

    # Show tool registry
    print("Tool registry (manual dispatch):")
    code = '''
from stardew_vision.tools import TOOL_REGISTRY

# Developer must know screen type
result = TOOL_REGISTRY["crop_pierres_detail_panel"](
    image_path="screenshot.png"
)

print(result)
# {'name': 'Parsnip', 'description': 'A spring vegetable', ...}
    '''
    print(code)
    print()

    print("✅ Works for single screen type")
    print("❌ Doesn't scale to multiple screen types (TV, inventory, etc.)")
    print("❌ User must classify screen manually")
    print()

    print("💡 Key insight: We need intelligence to classify screen type")
    print()


def demo_2_smolagents():
    """Demo 2: Smolagents CodeAgent (AI-powered classification)."""
    print("=" * 80)
    print("DEMO 2: SMOLAGENTS CODEAGENT (AI-Powered Intelligence)")
    print("=" * 80)
    print()
    print("🎯 Point: Add VLM to classify screen type and call correct tool")
    print()

    print("The upgrade:")
    print("  - VLM (Qwen2.5-VL-7B) analyzes screenshot")
    print("  - Identifies UI panel type (Pierre's shop)")
    print("  - Writes Python code to call extraction tool")
    print("  - Returns structured data")
    print()

    # Show Smolagents code
    print("Smolagents implementation:")
    code = '''
from smolagents import CodeAgent, LiteLLMModel, Tool

class PierresPanelTool(Tool):
    name = "crop_pierres_detail_panel"
    description = "Extract item details from Pierre's General Store"
    inputs = {"image_path": {"type": "string"}}
    output_type = "dict"

    def forward(self, image_path: str):
        from stardew_vision.tools import crop_pierres_detail_panel
        return crop_pierres_detail_panel(image_path)

# Connect to vLLM endpoint
model = LiteLLMModel(
    model_id="Qwen2.5-VL-7B-Instruct",
    base_url="http://localhost:8001/v1",
    api_key="EMPTY"
)

# Create agent
agent = CodeAgent(tools=[PierresPanelTool()], model=model)

# User just uploads screenshot - no classification needed
result = agent.run("Extract information from screenshot.png")
    '''
    print(code)
    print()

    print("What the VLM generates (Python code!):")
    generated_code = '''
# CodeAgent writes this:
image_path = "screenshot.png"
result = crop_pierres_detail_panel(image_path=image_path)
print(result)
    '''
    print(generated_code)
    print()

    print("✅ Automatic screen classification")
    print("✅ No manual tool selection")
    print("✅ Scales to multiple screen types (add more tools)")
    print("✅ VLM-first design (vision, video, audio)")
    print()

    print("💡 Key insight: CodeAgent writes Python (more robust than JSON)")
    print()


def demo_3_production():
    """Demo 3: Production FastAPI integration."""
    print("=" * 80)
    print("DEMO 3: PRODUCTION WEB API (Accessibility Tool)")
    print("=" * 80)
    print()
    print("🎯 Point: Full production pipeline with observability")
    print()

    print("The complete system:")
    print("  1. User uploads screenshot via web UI")
    print("  2. FastAPI endpoint validates and saves file")
    print("  3. VLMOrchestrator analyzes with Smolagents")
    print("  4. Extraction result validated against schema")
    print("  5. MLFlow logs all metrics (latency, success rate)")
    print("  6. [Phase 2] MeloTTS synthesizes audio narration")
    print("  7. Return JSON (or audio) to user")
    print()

    # Show end-to-end flow
    print("Production architecture:")
    arch = '''
┌─────────────────────────────────────────────────────────┐
│                    User (Web Browser)                    │
└─────────────────────┬───────────────────────────────────┘
                      │ Upload screenshot.png
                      ▼
┌─────────────────────────────────────────────────────────┐
│              FastAPI (Port 8000)                         │
│  POST /api/v1/analyze                                    │
│    - Validate file (image/png)                           │
│    - Save to temp file                                   │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│         VLMOrchestrator (Smolagents)                     │
│  - CodeAgent with vLLM backend (port 8001)               │
│  - Classifies: "Pierre's shop detail panel"             │
│  - Calls: crop_pierres_detail_panel(image_path)         │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│      Extraction Tool (OpenCV + PaddleOCR)                │
│  - Template matching (find panel region)                 │
│  - OCR (extract text)                                    │
│  - Parse fields (name, description, price, qty, total)   │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│           Validation (Pydantic Schema)                   │
│  - Verify all required fields present                    │
│  - Check total_cost = price * quantity                   │
│  - Raise error if validation fails                       │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│              MLFlow Logging                              │
│  - Log params (image_path, model_id)                     │
│  - Log metrics (latency_ms, success, validation_passed)  │
│  - Log artifacts (extraction_result.json)                │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼ JSON response
┌─────────────────────────────────────────────────────────┐
│                    User (Web Browser)                    │
│  {                                                        │
│    "success": true,                                       │
│    "extraction": {                                        │
│      "name": "Parsnip",                                   │
│      "description": "A spring vegetable",                 │
│      "price_per_unit": 20,                                │
│      "quantity_selected": 5,                              │
│      "total_cost": 100                                    │
│    }                                                       │
│  }                                                         │
└─────────────────────────────────────────────────────────┘
    '''
    print(arch)
    print()

    print("✅ Production-ready API")
    print("✅ Automatic error handling and retry")
    print("✅ Schema validation prevents bad data")
    print("✅ MLFlow observability (debug, optimize)")
    print("✅ Health checks and graceful degradation")
    print()

    print("💡 Key insight: Production = MVP + observability + error handling")
    print()


def demo_4_framework_decision():
    """Demo 4: Why Smolagents over alternatives."""
    print("=" * 80)
    print("DEMO 4: FRAMEWORK DECISION RATIONALE")
    print("=" * 80)
    print()
    print("🎯 Point: Choosing the right tool for the job")
    print()

    print("We evaluated 4 approaches:")
    print()

    comparisons = {
        "Raw OpenAI Client": {
            "pros": ["Maximum control", "No framework lock-in", "Debuggable"],
            "cons": ["Manual error handling", "No observability hooks", "Repetitive code"],
            "verdict": "✅ Valid choice for maximum simplicity"
        },
        "Smolagents": {
            "pros": ["VLM-first design", "Model-agnostic", "CodeAgent (Python code)", "Hub integrations"],
            "cons": ["Newer ecosystem", "Less mature than OpenAI/Claude SDKs"],
            "verdict": "✅ CHOSEN - Best for VLM projects"
        },
        "OpenAI Agents SDK": {
            "pros": ["Production-ready", "MCP integration", "Built-in sessions"],
            "cons": ["GPT-optimized (may not work well with Qwen)", "Less VLM support"],
            "verdict": "⚠️ Consider if switching to GPT-5"
        },
        "Claude Agent SDK": {
            "pros": ["Rich hooks", "Observability", "Tool Calling 2.0"],
            "cons": ["Claude API only", "Can't use with local Qwen", "Costs credits"],
            "verdict": "❌ Blocked - requires Claude API"
        }
    }

    for framework, details in comparisons.items():
        print(f"{framework}:")
        print(f"  Pros: {', '.join(details['pros'])}")
        print(f"  Cons: {', '.join(details['cons'])}")
        print(f"  Verdict: {details['verdict']}")
        print()

    print("Decision criteria:")
    print("  1. Works with Qwen2.5-VL (local or vLLM)")
    print("  2. VLM-optimized (vision, not retrofitted)")
    print("  3. Minimal complexity for MVP")
    print("  4. Open path to Phase 2+ (multi-screen, multi-agent)")
    print("  5. Conference demo friendly (Hub integrations)")
    print()

    print("✅ Smolagents wins on all criteria")
    print()

    print("💡 Key insight: Choose based on actual complexity, not anticipated")
    print()


def demo_5_when_to_use_alternatives():
    """Demo 5: When to reconsider framework choice."""
    print("=" * 80)
    print("DEMO 5: WHEN TO USE ALTERNATIVES")
    print("=" * 80)
    print()
    print("🎯 Point: Framework choice isn't permanent - adapt as needed")
    print()

    scenarios = {
        "Use LangGraph when": [
            "Phase 2+: Multi-screen routing gets complex",
            "Need conditional state machines (IF shop THEN extract_shop ELSE IF tv THEN extract_tv)",
            "Multi-step workflows with branches",
            "Example: Router → Shop | TV | Inventory → Validator"
        ],

        "Use CrewAI when": [
            "Phase 3+: Need multi-agent collaboration",
            "Extractor agent + Validator agent + Summarizer agent",
            "Role-based workflows (Planner, Researcher, Writer)",
            "Example: Extractor → Validator → TTS (different agents)"
        ],

        "Use Raw Client when": [
            "Smolagents overhead too high",
            "Need maximum control for debugging",
            "Single-shot task (no complex workflows)",
            "Example: One-off script, not production API"
        ],

        "Stick with Smolagents when": [
            "CodeAgent handles routing well (Python code)",
            "Multi-agent needs met by managed_agents",
            "VLM-optimized features still valuable",
            "Example: MVP → Phase 2 → Phase 3 all work with Smolagents"
        ]
    }

    for scenario, reasons in scenarios.items():
        print(f"{scenario}:")
        for reason in reasons:
            print(f"  - {reason}")
        print()

    print("💡 Key insight: Defer complexity until needed. Test Smolagents first.")
    print()


def demo_6_hub_sharing():
    """Demo 6: Sharing tools on HuggingFace Hub."""
    print("=" * 80)
    print("DEMO 6: HUB TOOL SHARING (Community Contributions)")
    print("=" * 80)
    print()
    print("🎯 Point: Conference attendees can try and contribute tools")
    print()

    print("Share PierresPanelTool on HuggingFace Hub:")
    code = '''
from smolagents import Tool

class PierresPanelTool(Tool):
    name = "crop_pierres_detail_panel"
    description = "Extract item details from Pierre's General Store in Stardew Valley"
    # ... (full implementation)

# Push to Hub
tool = PierresPanelTool()
tool.push_to_hub("yourusername/pierre-panel-tool")

# Others can use it:
from smolagents import load_tool
tool = load_tool("yourusername/pierre-panel-tool")

# Create agent with Hub tool
agent = CodeAgent(tools=[tool], model=model)
    '''
    print(code)
    print()

    print("Benefits for conference demos:")
    print("  ✅ Attendees try tool in browser (HF Spaces)")
    print("  ✅ Version control for tool definitions")
    print("  ✅ Community can contribute TV dialog tool, inventory tool, etc.")
    print("  ✅ Share fine-tuned VLM models on Hub")
    print()

    print("Potential Hub contributions:")
    print("  - pierre-panel-tool (MVP)")
    print("  - tv-dialog-tool (Phase 2)")
    print("  - inventory-tooltip-tool (Phase 2)")
    print("  - qwen-vlm-stardew-finetuned (Phase 1 fine-tuning)")
    print()

    print("💡 Key insight: Hub integrations make accessibility tools shareable")
    print()


def demo_7_future_enhancements():
    """Demo 7: Future enhancements (Phase 2+)."""
    print("=" * 80)
    print("DEMO 7: FUTURE ENHANCEMENTS (Conference Roadmap)")
    print("=" * 80)
    print()
    print("🎯 Point: This is just the beginning")
    print()

    roadmap = {
        "Phase 1 (MVP - Current)": [
            "✅ Pierre's shop detail panel extraction",
            "✅ Smolagents CodeAgent with Qwen2.5-VL",
            "✅ FastAPI web endpoint",
            "✅ MLFlow observability",
            "🔄 MeloTTS audio narration (next)"
        ],

        "Phase 2 (Multi-Screen)": [
            "TV dialog extraction tool",
            "Inventory tooltip extraction tool",
            "Router logic (classify → dispatch correct tool)",
            "Consider LangGraph if routing gets complex",
            "Fine-tune VLM on tool-calling pairs"
        ],

        "Phase 3 (Quality & Scale)": [
            "Validator agent (check extraction quality)",
            "Multi-agent with Smolagents or CrewAI",
            "Feast feature store (replace filesystem)",
            "OpenShift AI deployment (KServe)",
            "Ray Train for distributed fine-tuning"
        ],

        "Phase 4 (Advanced)": [
            "Live gameplay narration (video input)",
            "Real-time screen reader integration",
            "User feedback loop (improve extractions)",
            "Community-contributed tools (Hub)",
            "Upgrade to Qwen3-VL (native tool calling)"
        ]
    }

    for phase, features in roadmap.items():
        print(f"{phase}:")
        for feature in features:
            print(f"  {feature}")
        print()

    print("💡 Key insight: Architecture supports growth without rewrites")
    print()


def main():
    print("=" * 80)
    print("MODULE 6: CONFERENCE DEMO & ADVANCED TOPICS")
    print("=" * 80)
    print()
    print("This module creates compelling demo materials for conference talks.")
    print("Show the journey: Manual → Intelligent → Production")
    print()
    print("Demo progression:")
    print("  1. Manual tool dispatch (baseline)")
    print("  2. Smolagents CodeAgent (intelligence)")
    print("  3. Production FastAPI (complete system)")
    print("  4. Framework decision rationale")
    print("  5. When to use alternatives")
    print("  6. Hub tool sharing")
    print("  7. Future enhancements")
    print()

    input("Press Enter to start Demo 1...")
    demo_1_manual()

    input("Press Enter for Demo 2...")
    demo_2_smolagents()

    input("Press Enter for Demo 3...")
    demo_3_production()

    input("Press Enter for Demo 4...")
    demo_4_framework_decision()

    input("Press Enter for Demo 5...")
    demo_5_when_to_use_alternatives()

    input("Press Enter for Demo 6...")
    demo_6_hub_sharing()

    input("Press Enter for Demo 7...")
    demo_7_future_enhancements()

    # Summary
    print()
    print("=" * 80)
    print("✅ MODULE 6 COMPLETE!")
    print("=" * 80)
    print()
    print("✅ ALL 6 MODULES COMPLETE!")
    print()
    print("You now have:")
    print("  ✅ Complete understanding of agent/tool-calling patterns")
    print("  ✅ Production VLMOrchestrator using Smolagents")
    print("  ✅ FastAPI web endpoint for screenshot uploads")
    print("  ✅ MLFlow observability and testing strategy")
    print("  ✅ Conference demo materials and narrative arc")
    print("  ✅ Framework decision knowledge and alternatives")
    print()
    print("Conference talk structure:")
    print("  1. The Problem (5 min)")
    print("     - Visually impaired gamers struggle with Stardew Valley UI")
    print("     - Show Pierre's shop screenshot")
    print()
    print("  2. Manual Solution (5 min)")
    print("     - OpenCV + PaddleOCR extraction")
    print("     - Works but doesn't scale")
    print("     - Demo: TOOL_REGISTRY['crop_pierres_detail_panel']")
    print()
    print("  3. Adding Intelligence (10 min)")
    print("     - VLM (Qwen2.5-VL) classifies screen type")
    print("     - Smolagents CodeAgent writes Python code")
    print("     - Demo: agent.run('Extract from screenshot')")
    print()
    print("  4. Production System (10 min)")
    print("     - FastAPI web endpoint")
    print("     - Schema validation, error handling, MLFlow")
    print("     - Demo: Upload screenshot via /docs UI")
    print()
    print("  5. Framework Decision (5 min)")
    print("     - Why Smolagents over OpenAI/Claude SDKs")
    print("     - When to use alternatives (LangGraph, CrewAI)")
    print()
    print("  6. Live Coding (10 min)")
    print("     - Build agent from scratch: Manual → Smolagents → Production")
    print("     - 15 lines of code for working agent")
    print()
    print("  7. Future & Community (5 min)")
    print("     - Phase 2: Multi-screen support")
    print("     - Hub tool sharing")
    print("     - Call for contributions")
    print()
    print("Total: 50 minutes (10 min for Q&A)")
    print()
    print("Materials ready:")
    print("  📁 agent-learning/ - Portable curriculum")
    print("  📄 docs/agent-frameworks-compared.md - Decision rationale")
    print("  📄 examples/*.py - Live coding scripts")
    print("  🎯 This demo progression - Conference narrative")
    print()
    print("Next steps:")
    print("  1. Practice live coding demo (examples/module2_smolagents_basic.py)")
    print("  2. Test end-to-end: vLLM → FastAPI → Browser")
    print("  3. Create slides with architecture diagrams")
    print("  4. Prepare HuggingFace Space for attendees to try")
    print("  5. Record demo video as backup")
    print()
    print("🎉 Congratulations! You've completed the agent/tool-calling curriculum!")
    print()


if __name__ == "__main__":
    main()
