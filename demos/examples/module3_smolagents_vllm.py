"""
Module 3: Smolagents + vLLM Integration

Purpose: Connect Smolagents to vLLM endpoint using LiteLLMModel.
This is the production pattern - same code works for local vLLM and OpenShift AI.

Prerequisites:
- Completed Module 1-2
- vLLM server running on port 8001
- Smolagents installed

vLLM Startup Command:
  vllm serve /workspaces/stardew-vision/models/base/Qwen2.5-VL-7B-Instruct \\
    --port 8001 \\
    --dtype float16 \\
    --enable-tool-calling \\
    --max-model-len 4096

What you'll learn:
- How to use LiteLLMModel for vLLM endpoints
- How to configure endpoint URL and API key
- Same agent code, different backend (vs Module 2)
- Debug connection issues
"""

import json
import sys
from pathlib import Path
import requests
from typing import Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


def check_vllm_server(endpoint: str = "http://localhost:8001") -> bool:
    """
    Check if vLLM server is running.

    Args:
        endpoint: vLLM base URL

    Returns:
        True if server is up and responding
    """
    try:
        response = requests.get(f"{endpoint}/v1/models", timeout=5)
        response.raise_for_status()

        models = response.json()
        print(f"✅ vLLM server detected at {endpoint}")
        print(f"📋 Available models: {models}")
        print()
        return True

    except requests.exceptions.ConnectionError:
        print(f"❌ vLLM server not running at {endpoint}")
        print()
        print("Start vLLM with:")
        print("  vllm serve /workspaces/stardew-vision/models/base/Qwen2.5-VL-7B-Instruct \\")
        print("    --port 8001 \\")
        print("    --dtype float16 \\")
        print("    --enable-tool-calling \\")
        print("    --max-model-len 4096")
        print()
        return False

    except Exception as e:
        print(f"❌ Error checking vLLM server: {e}")
        print()
        return False


def example_1_litellm_model():
    """Example 1: Configure LiteLLMModel for vLLM endpoint."""
    from smolagents import LiteLLMModel

    print("=" * 80)
    print("EXAMPLE 1: LiteLLMModel Configuration")
    print("=" * 80)
    print()

    print("LiteLLMModel is a universal backend that works with:")
    print("  - vLLM (local or remote)")
    print("  - OpenAI API")
    print("  - Anthropic API")
    print("  - Any OpenAI-compatible endpoint")
    print()

    print("For vLLM configuration:")
    print()

    # Show configuration
    config_code = """
    from smolagents import LiteLLMModel

    model = LiteLLMModel(
        model_id="Qwen2.5-VL-7B-Instruct",  # Model name for vLLM
        base_url="http://localhost:8001/v1",  # vLLM OpenAI-compatible endpoint
        api_key="EMPTY"  # vLLM doesn't require auth for local
    )
    """
    print(config_code)

    print("Creating model...")
    try:
        model = LiteLLMModel(
            model_id="Qwen2.5-VL-7B-Instruct",
            base_url="http://localhost:8001/v1",
            api_key="EMPTY"
        )
        print("✅ Model configured!")
        print()
        print("The model is now ready to use with CodeAgent.")
        print("Same model instance can be used for multiple agents.")
        print()
        return model

    except Exception as e:
        print(f"❌ Failed to configure model: {e}")
        print()
        return None


def example_2_codeagent_vllm():
    """Example 2: Use CodeAgent with vLLM backend."""
    from smolagents import CodeAgent, LiteLLMModel, Tool

    print("=" * 80)
    print("EXAMPLE 2: CodeAgent + vLLM")
    print("=" * 80)
    print()

    # Define tool
    class CropPierresPanelTool(Tool):
        """Same tool as Module 2, but will use vLLM backend."""
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
                print(f"  [Tool] Extraction successful!")
                return result
            except ImportError:
                # Mock data for demo
                print("  [Tool] Using mock data")
                return {
                    "name": "Parsnip",
                    "description": "A spring vegetable",
                    "price_per_unit": 20,
                    "quantity_selected": 5,
                    "total_cost": 100
                }

    # Configure model
    print("Connecting to vLLM endpoint...")
    model = LiteLLMModel(
        model_id="Qwen2.5-VL-7B-Instruct",
        base_url="http://localhost:8001/v1",
        api_key="EMPTY"
    )
    print("✅ Connected!")
    print()

    # Create agent
    print("Creating CodeAgent with vLLM backend...")
    tools = [CropPierresPanelTool()]

    agent = CodeAgent(
        tools=tools,
        model=model,
        add_base_tools=False,
        max_steps=3,
        verbosity=2
    )
    print("✅ Agent created!")
    print()

    # Run agent
    image_path = "/workspaces/stardew-vision/tests/fixtures/pierre_shop_001.png"

    print(f"Running agent on: {image_path}")
    print("-" * 80)

    try:
        result = agent.run(
            f"Extract item information from the screenshot at {image_path} "
            f"using the crop_pierres_detail_panel tool. Return the complete result."
        )

        print("-" * 80)
        print()
        print("Agent Result:")
        print(json.dumps(result, indent=2))
        print()

        print("✅ Extraction complete!")
        print()
        print("What happened:")
        print("  1. Agent sent prompt to vLLM endpoint (http://localhost:8001)")
        print("  2. vLLM served Qwen2.5-VL-7B-Instruct generated Python code")
        print("  3. Code executed (called crop_pierres_detail_panel)")
        print("  4. Result returned")
        print()
        print("Key insight: Same CodeAgent code as Module 2, different backend!")

        return result

    except Exception as e:
        print(f"❌ Agent execution failed: {e}")
        print()
        print("Common issues:")
        print("  - vLLM server not running")
        print("  - vLLM tool calling not enabled (--enable-tool-calling flag)")
        print("  - Model doesn't support tool calling")
        print("  - Network/timeout issues")
        print()
        return None


def example_3_production_pattern():
    """Example 3: Production pattern - same code for local and remote."""
    print("=" * 80)
    print("EXAMPLE 3: Production Pattern")
    print("=" * 80)
    print()

    print("The power of LiteLLMModel: Same agent code works everywhere!")
    print()

    # Show different configurations
    configs = {
        "Local vLLM": """
        model = LiteLLMModel(
            model_id="Qwen2.5-VL-7B-Instruct",
            base_url="http://localhost:8001/v1",
            api_key="EMPTY"
        )
        """,

        "OpenShift AI KServe": """
        model = LiteLLMModel(
            model_id="Qwen2.5-VL-7B-Instruct",
            base_url="https://qwen-vlm.apps.openshift.example.com/v1",
            api_key=os.environ["KSERVE_API_KEY"]
        )
        """,

        "OpenAI API": """
        model = LiteLLMModel(
            model_id="gpt-4o",
            api_key=os.environ["OPENAI_API_KEY"]
        )
        """,

        "Anthropic API": """
        model = LiteLLMModel(
            model_id="claude-sonnet-4",
            api_key=os.environ["ANTHROPIC_API_KEY"]
        )
        """
    }

    for name, config in configs.items():
        print(f"{name}:")
        print(config)
        print()

    print("Same CodeAgent code works with all of these!")
    print("Just change the model initialization.")
    print()
    print("This is the production pattern for Stardew Vision:")
    print("  - MVP: Local vLLM on port 8001")
    print("  - Production: OpenShift AI KServe endpoint")
    print("  - Same codebase, zero changes")


def example_4_debugging():
    """Example 4: Debug common vLLM connection issues."""
    print("=" * 80)
    print("EXAMPLE 4: Debugging vLLM Connection")
    print("=" * 80)
    print()

    print("Common issues and solutions:")
    print()

    issues = {
        "Connection refused": {
            "symptom": "requests.exceptions.ConnectionError",
            "cause": "vLLM server not running",
            "solution": "Start vLLM: vllm serve ... --port 8001"
        },

        "Tool calling not enabled": {
            "symptom": "Agent returns text instead of calling tool",
            "cause": "vLLM started without --enable-tool-calling",
            "solution": "Restart vLLM with --enable-tool-calling flag"
        },

        "Model not found": {
            "symptom": "404 error from vLLM",
            "cause": "Model path incorrect or not downloaded",
            "solution": "Check model path exists: ls models/base/Qwen2.5-VL-7B-Instruct"
        },

        "Timeout": {
            "symptom": "Request times out after 60s",
            "cause": "Model too slow on CPU or insufficient GPU memory",
            "solution": "Use smaller model or upgrade GPU"
        },

        "Wrong endpoint URL": {
            "symptom": "404 or connection refused",
            "cause": "base_url is incorrect",
            "solution": "Verify endpoint: curl http://localhost:8001/v1/models"
        }
    }

    for issue, details in issues.items():
        print(f"❌ {issue}")
        print(f"   Symptom: {details['symptom']}")
        print(f"   Cause: {details['cause']}")
        print(f"   Solution: {details['solution']}")
        print()

    print("Quick health check:")
    check_vllm_server()


def main():
    print("=" * 80)
    print("MODULE 3: SMOLAGENTS + vLLM INTEGRATION")
    print("=" * 80)
    print()
    print("Learning objectives:")
    print("  1. Configure LiteLLMModel for vLLM endpoint")
    print("  2. Use CodeAgent with vLLM backend")
    print("  3. Understand production deployment pattern")
    print("  4. Debug connection issues")
    print()

    # Check vLLM server
    print("Checking vLLM server status...")
    if not check_vllm_server():
        print("⚠️  vLLM server not detected. Examples may not run.")
        print()
        response = input("Continue anyway? (y/N): ")
        if response.lower() != 'y':
            print("Exiting. Start vLLM and re-run this module.")
            return
        print()

    # Example 1: LiteLLMModel configuration
    model = example_1_litellm_model()
    if not model:
        print("Skipping remaining examples (model configuration failed)")
        return

    print()
    input("Press Enter to continue to Example 2...")
    print()

    # Example 2: CodeAgent with vLLM
    result = example_2_codeagent_vllm()

    print()
    input("Press Enter to continue to Example 3...")
    print()

    # Example 3: Production pattern
    example_3_production_pattern()

    print()
    input("Press Enter to continue to Example 4...")
    print()

    # Example 4: Debugging
    example_4_debugging()

    # Summary
    print("=" * 80)
    print("✅ MODULE 3 COMPLETE!")
    print("=" * 80)
    print()
    print("You now understand:")
    print("  ✅ How to connect Smolagents to vLLM endpoint")
    print("  ✅ How LiteLLMModel works (OpenAI-compatible wrapper)")
    print("  ✅ Same agent code, different backend (local vs remote)")
    print("  ✅ How to debug vLLM connection issues")
    print()
    print("Key insights:")
    print("  - LiteLLMModel is universal (vLLM, OpenAI, Anthropic)")
    print("  - Same CodeAgent code works everywhere")
    print("  - vLLM uses OpenAI-compatible API")
    print("  - This pattern works for OpenShift AI too")
    print()
    print("Next: Module 4 - Production wrapper with error handling and testing")
    print()


if __name__ == "__main__":
    main()
