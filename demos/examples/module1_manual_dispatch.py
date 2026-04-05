"""
Module 1: Manual Tool Calling

Purpose: Understand OpenAI function-calling format without any framework.
Learn the fundamentals of tool definitions, registries, and dispatch.

This is the foundation - everything else builds on this.
"""

import json
import sys
from pathlib import Path

# Add src to path so we can import stardew_vision
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


# =============================================================================
# TOOL DEFINITION (OpenAI Format)
# =============================================================================

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "crop_pierres_detail_panel",
            "description": "Extract item details from Pierre's General Store detail panel in a Stardew Valley screenshot",
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
]

# =============================================================================
# TOOL REGISTRY
# =============================================================================

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

# =============================================================================
# MANUAL DISPATCH LOGIC
# =============================================================================

def dispatch_tool(tool_name: str, arguments: dict) -> dict:
    """
    Manually invoke a tool from registry.

    This is what frameworks like Smolagents automate.
    Understanding this helps you debug framework issues later.

    Args:
        tool_name: Name of tool to call
        arguments: Dict of arguments to pass

    Returns:
        Tool result dict

    Raises:
        ValueError: If tool not found in registry
    """
    if tool_name not in TOOL_REGISTRY:
        available = ", ".join(TOOL_REGISTRY.keys())
        raise ValueError(f"Unknown tool: {tool_name}. Available: {available}")

    print(f"📞 Dispatching tool: {tool_name}")
    print(f"📋 Arguments: {json.dumps(arguments, indent=2)}")
    print()

    # Call the function
    result = TOOL_REGISTRY[tool_name](**arguments)

    print(f"✅ Result:")
    print(json.dumps(result, indent=2))
    print()

    return result


# =============================================================================
# SIMULATE VLM RESPONSE
# =============================================================================

def simulate_vlm_response(image_path: str) -> dict:
    """
    Simulate what a VLM would return (without actually running VLM).

    This is the JSON structure that vLLM returns in the `tool_calls` field.
    Understanding this structure is critical for parsing VLM responses.
    """
    return {
        "tool_call": {
            "id": "call_abc123",
            "type": "function",
            "function": {
                "name": "crop_pierres_detail_panel",
                "arguments": json.dumps({
                    "image_path": image_path
                })
            }
        }
    }


# =============================================================================
# MAIN DEMONSTRATION
# =============================================================================

def main():
    print("=" * 80)
    print("MODULE 1: MANUAL TOOL DISPATCH (No Framework, No VLM)")
    print("=" * 80)
    print()
    print("Learning objectives:")
    print("  1. Understand OpenAI function-calling format")
    print("  2. Create tool definitions manually")
    print("  3. Build tool registry and dispatcher")
    print("  4. Parse VLM responses and execute tools")
    print()

    # -------------------------------------------------------------------------
    # Step 1: Show Tool Definitions
    # -------------------------------------------------------------------------

    print("-" * 80)
    print("STEP 1: Tool Definitions (OpenAI Format)")
    print("-" * 80)
    print()
    print("These are the JSON schemas that tell the VLM what tools are available.")
    print("The VLM uses this to decide which tool to call and what arguments to pass.")
    print()
    print(json.dumps(TOOL_DEFINITIONS, indent=2))
    print()

    # -------------------------------------------------------------------------
    # Step 2: Show Tool Registry
    # -------------------------------------------------------------------------

    print("-" * 80)
    print("STEP 2: Tool Registry")
    print("-" * 80)
    print()
    print("The registry maps tool names to actual Python functions.")
    print("This is a simple dict: {name: function}")
    print()
    print("Available tools:")
    for name, func in TOOL_REGISTRY.items():
        print(f"  - {name}: {func.__doc__.strip() if func.__doc__ else 'No description'}")
    print()

    # -------------------------------------------------------------------------
    # Step 3: Simulate VLM Response
    # -------------------------------------------------------------------------

    print("-" * 80)
    print("STEP 3: Simulated VLM Response")
    print("-" * 80)
    print()
    print("In a real system, the VLM would analyze the screenshot and return")
    print("a tool_call JSON structure like this:")
    print()

    image_path = "/workspaces/stardew-vision/tests/fixtures/pierre_shop_001.png"
    vlm_response = simulate_vlm_response(image_path)

    print(json.dumps(vlm_response, indent=2))
    print()

    # -------------------------------------------------------------------------
    # Step 4: Parse and Dispatch
    # -------------------------------------------------------------------------

    print("-" * 80)
    print("STEP 4: Parse VLM Response and Dispatch Tool")
    print("-" * 80)
    print()

    # Extract tool call details
    tool_call = vlm_response["tool_call"]
    tool_name = tool_call["function"]["name"]
    arguments = json.loads(tool_call["function"]["arguments"])

    print(f"Extracted tool name: {tool_name}")
    print(f"Extracted arguments: {arguments}")
    print()

    # Dispatch to actual tool
    try:
        result = dispatch_tool(tool_name, arguments)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

    # -------------------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------------------

    print("-" * 80)
    print("✅ MODULE 1 COMPLETE!")
    print("-" * 80)
    print()
    print("You now understand:")
    print("  ✅ OpenAI function-calling format (JSON schema)")
    print("  ✅ Tool registry pattern (dict of name → function)")
    print("  ✅ Manual dispatch logic (look up function, call with args)")
    print("  ✅ VLM response structure (tool_calls field)")
    print()
    print("Key insight: Tool calling is NOT magic. It's just:")
    print("  1. VLM returns JSON with tool name + args")
    print("  2. You parse the JSON")
    print("  3. You call the function from your registry")
    print()
    print("Frameworks like Smolagents automate step 2-3, but understanding")
    print("this manual process helps you debug issues later.")
    print()
    print("Next: Module 2 - Smolagents automates this!")


if __name__ == "__main__":
    main()
