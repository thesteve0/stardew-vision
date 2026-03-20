"""
Module 2: Smolagents Basics

Purpose: Learn Smolagents framework - Tool class, CodeAgent, and InferenceClientModel.
This is your first introduction to the framework that will power the VLM orchestrator.

Prerequisites:
- Completed Module 1 (understand manual dispatch)
- Smolagents installed: uv add 'smolagents[toolkit,litellm]'

What you'll learn:
- How to create custom Tool classes
- How CodeAgent works (writes Python code to call tools)
- How to use InferenceClientModel (transformers backend)
- Difference between CodeAgent and ToolCallingAgent
"""

import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


def check_smolagents_installed():
    """Check if Smolagents is installed."""
    try:
        import smolagents
        print(f"✅ Smolagents installed (version {smolagents.__version__})")
        return True
    except ImportError:
        print("❌ Smolagents not installed!")
        print()
        print("Install with:")
        print("  uv add 'smolagents[toolkit,litellm]'")
        print()
        return False


def example_1_basic_tool():
    """Example 1: Create a basic Smolagents Tool."""
    from smolagents import Tool

    print("=" * 80)
    print("EXAMPLE 1: Basic Smolagents Tool")
    print("=" * 80)
    print()

    class CropPierresPanelTool(Tool):
        """
        Smolagents Tool wrapper for Pierre's shop extraction.

        Key components:
        - name: Tool identifier (what VLM sees)
        - description: What the tool does (shown to VLM for selection)
        - inputs: Parameter schema (type and description for each arg)
        - output_type: Return type (dict, str, image, etc.)
        - forward(): Actual implementation
        """
        name = "crop_pierres_detail_panel"
        description = "Extract item details from Pierre's General Store detail panel in a Stardew Valley screenshot"

        inputs = {
            "image_path": {
                "type": "string",
                "description": "Path to the screenshot file"
            }
        }

        output_type = "dict"

        def forward(self, image_path: str):
            """Execute the extraction tool."""
            print(f"  [Tool] Executing on {image_path}")

            try:
                from stardew_vision.tools import crop_pierres_detail_panel
                result = crop_pierres_detail_panel(image_path)
                print(f"  [Tool] Extraction successful: {result}")
                return result
            except ImportError:
                # Mock data for demo if tool not available
                print("  [Tool] Using mock data")
                return {
                    "name": "Parsnip",
                    "description": "A spring vegetable",
                    "price_per_unit": 20,
                    "quantity_selected": 5,
                    "total_cost": 100
                }

    # Create tool instance
    tool = CropPierresPanelTool()

    print("Tool created:")
    print(f"  Name: {tool.name}")
    print(f"  Description: {tool.description}")
    print(f"  Inputs: {tool.inputs}")
    print(f"  Output type: {tool.output_type}")
    print()

    # Test tool manually (without agent)
    print("Testing tool manually (calling forward() directly):")
    result = tool.forward("/workspaces/stardew-vision/tests/fixtures/pierre_shop_001.png")
    print()
    print(f"Result: {json.dumps(result, indent=2)}")
    print()

    print("✅ Tool creation complete!")
    print()
    print("Key insight: Smolagents Tool is a class that wraps your function")
    print("with metadata (name, description, inputs, output_type) that the VLM")
    print("uses to decide when to call it.")
    print()

    return tool


def example_2_codeagent_local():
    """Example 2: Use CodeAgent with InferenceClientModel (local transformers)."""
    print("=" * 80)
    print("EXAMPLE 2: CodeAgent with InferenceClientModel")
    print("=" * 80)
    print()
    print("⚠️  WARNING: This example downloads Qwen2.5-VL-7B-Instruct (~15GB)")
    print("⚠️  and runs inference on CPU/GPU. May take several minutes.")
    print()

    # Ask user to confirm
    response = input("Continue? (y/N): ")
    if response.lower() != 'y':
        print("Skipped. Move to Module 3 for vLLM-based version (recommended).")
        return

    from smolagents import CodeAgent, InferenceClientModel, Tool

    class CropPierresPanelTool(Tool):
        name = "crop_pierres_detail_panel"
        description = "Extract item details from Pierre's General Store detail panel in screenshot"
        inputs = {"image_path": {"type": "string", "description": "Path to screenshot"}}
        output_type = "dict"

        def forward(self, image_path: str):
            try:
                from stardew_vision.tools import crop_pierres_detail_panel
                return crop_pierres_detail_panel(image_path)
            except ImportError:
                return {"name": "Mock", "description": "Mock data", "price_per_unit": 0, "quantity_selected": 0, "total_cost": 0}

    print("Loading model (this may take a while)...")
    print("Model: Qwen/Qwen2.5-VL-7B-Instruct")
    print()

    try:
        model = InferenceClientModel(
            model_id="Qwen/Qwen2.5-VL-7B-Instruct"
        )
        print("✅ Model loaded!")
        print()
    except Exception as e:
        print(f"❌ Failed to load model: {e}")
        print()
        print("This is expected if:")
        print("  - Model not downloaded")
        print("  - Insufficient memory")
        print("  - GPU not available")
        print()
        print("Recommended: Skip to Module 3 to use vLLM instead")
        return

    # Create agent
    print("Creating CodeAgent...")
    tools = [CropPierresPanelTool()]

    agent = CodeAgent(
        tools=tools,
        model=model,
        add_base_tools=False,  # Don't add default DuckDuckGo, etc.
        max_steps=3,           # Limit reasoning iterations
        verbosity=2            # 0=silent, 1=normal, 2=verbose
    )
    print("✅ Agent created!")
    print()

    # Run agent
    image_path = "/workspaces/stardew-vision/tests/fixtures/pierre_shop_001.png"

    print(f"Running agent on: {image_path}")
    print("-" * 80)

    try:
        result = agent.run(
            f"Extract all item information from the Pierre's General Store screenshot at {image_path}. "
            f"Use the crop_pierres_detail_panel tool and return the complete result."
        )

        print("-" * 80)
        print()
        print("Agent Result:")
        print(json.dumps(result, indent=2))
        print()

        print("✅ CodeAgent execution complete!")
        print()
        print("What happened:")
        print("  1. Agent received your prompt")
        print("  2. Agent analyzed the task")
        print("  3. Agent WROTE PYTHON CODE to call the tool")
        print("  4. Code was executed (sandboxed)")
        print("  5. Result returned")
        print()
        print("Inspect the Python code the agent wrote:")
        if hasattr(agent, 'logs') and agent.logs:
            print(agent.logs[-1].get("code", "Code not available"))

    except Exception as e:
        print(f"❌ Agent failed: {e}")
        print()
        print("This is a learning opportunity - what went wrong?")


def example_3_codeagent_vs_toolcalling():
    """Example 3: CodeAgent vs ToolCallingAgent."""
    print("=" * 80)
    print("EXAMPLE 3: CodeAgent vs ToolCallingAgent")
    print("=" * 80)
    print()

    print("Smolagents offers two agent paradigms:")
    print()
    print("1. CodeAgent (RECOMMENDED):")
    print("   - Agent writes PYTHON CODE to call tools")
    print("   - More robust (type-checked at runtime)")
    print("   - Composable (can chain tools naturally)")
    print("   - Example output:")
    print()
    print("     image_path = '/path/to/screenshot.png'")
    print("     result = crop_pierres_detail_panel(image_path=image_path)")
    print("     print(result)")
    print()
    print("2. ToolCallingAgent:")
    print("   - Agent uses JSON function calling (like OpenAI)")
    print("   - Compatible with more models")
    print("   - Less flexible than Python code")
    print("   - Example output:")
    print()
    print("     {")
    print('       "tool": "crop_pierres_detail_panel",')
    print('       "arguments": {"image_path": "/path/to/screenshot.png"}')
    print("     }")
    print()
    print("For Stardew Vision: Use CodeAgent")
    print("  - Qwen2.5-VL supports code generation")
    print("  - More robust than JSON parsing")
    print("  - Matches 'manual first' philosophy (same code you'd write)")
    print()


def main():
    print("=" * 80)
    print("MODULE 2: SMOLAGENTS BASICS")
    print("=" * 80)
    print()
    print("Learning objectives:")
    print("  1. Create custom Tool classes")
    print("  2. Understand CodeAgent paradigm")
    print("  3. Use InferenceClientModel (transformers backend)")
    print("  4. Compare CodeAgent vs ToolCallingAgent")
    print()

    # Check installation
    if not check_smolagents_installed():
        return

    print()

    # Example 1: Basic tool
    tool = example_1_basic_tool()

    input("Press Enter to continue to Example 2...")
    print()

    # Example 2: CodeAgent with transformers (optional)
    example_2_codeagent_local()

    print()
    input("Press Enter to continue to Example 3...")
    print()

    # Example 3: CodeAgent vs ToolCallingAgent
    example_3_codeagent_vs_toolcalling()

    # Summary
    print("=" * 80)
    print("✅ MODULE 2 COMPLETE!")
    print("=" * 80)
    print()
    print("You now understand:")
    print("  ✅ How to create Smolagents Tool classes")
    print("  ✅ How CodeAgent works (writes Python code)")
    print("  ✅ How InferenceClientModel works (transformers backend)")
    print("  ✅ Difference between CodeAgent and ToolCallingAgent")
    print()
    print("Key insights:")
    print("  - Tool class wraps function + metadata")
    print("  - CodeAgent writes Python code (not JSON)")
    print("  - InferenceClientModel downloads model from HF Hub")
    print("  - Verbosity=2 shows you what agent is thinking")
    print()
    print("Next: Module 3 - Connect to vLLM for production serving")
    print()


if __name__ == "__main__":
    main()
