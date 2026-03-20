# Agent/Tool-Calling Learning Curriculum

**Framework**: Smolagents (HuggingFace)
**Timeline**: 8-12 hours over 3-4 sessions
**Goal**: Build production VLM orchestrator for Stardew Vision

---

## Philosophy

**Progression**: Manual → Framework → Production

This curriculum follows the principle: **"Start development on each piece by driving it manually before hooking it into the larger architecture."**

Each module builds on the previous, with clear checkpoints for multi-session learning.

---

## Module 1: Manual Tool Dispatch (1-2 hours)

### Learning Objectives

- Understand OpenAI function-calling format
- Create tool definitions without any framework
- Build manual tool registry and dispatcher
- Learn JSON schema validation

### Why Start Manual?

Understanding the fundamentals without framework abstraction helps you:
- Debug framework issues later
- Know when frameworks are overkill
- Appreciate what frameworks automate
- Build custom solutions when needed

### Hands-On Activity

**File**: `examples/module1_manual_dispatch.py`

**Tasks**:
1. Study OpenAI function-calling specification
2. Create tool definition for `crop_pierres_detail_panel`
3. Build `TOOL_DEFINITIONS` list in OpenAI format
4. Implement manual dispatcher
5. Test with real screenshot

**Code Pattern**:

```python
"""
Module 1: Manual tool calling - no VLM, no framework.
Purpose: Understand tool interface fundamentals.
"""
import json
from pathlib import Path

# Tool definition in OpenAI format
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "crop_pierres_detail_panel",
            "description": "Extract item details from Pierre's General Store detail panel",
            "parameters": {
                "type": "object",
                "properties": {
                    "image_path": {
                        "type": "string",
                        "description": "Path to screenshot file"
                    }
                },
                "required": ["image_path"]
            }
        }
    }
]

def crop_pierres_detail_panel(image_path: str) -> dict:
    """
    Dummy implementation for testing.
    In production, this imports from stardew_vision.tools
    """
    from stardew_vision.tools import crop_pierres_detail_panel as real_tool
    return real_tool(image_path)

# Manual tool registry
TOOL_REGISTRY = {
    "crop_pierres_detail_panel": crop_pierres_detail_panel,
}

def dispatch_tool(tool_name: str, arguments: dict) -> dict:
    """
    Manually invoke a tool from registry.
    This is what frameworks automate.
    """
    if tool_name not in TOOL_REGISTRY:
        raise ValueError(f"Unknown tool: {tool_name}")

    print(f"Dispatching tool: {tool_name}")
    print(f"Arguments: {json.dumps(arguments, indent=2)}")

    result = TOOL_REGISTRY[tool_name](**arguments)

    print(f"Result: {json.dumps(result, indent=2)}")
    return result

# Simulate VLM tool call response
def simulate_vlm_response():
    """
    Simulate what a VLM would return (without actually running VLM).
    This is the JSON structure vLLM returns in tool_calls.
    """
    return {
        "tool_call": {
            "id": "call_123",
            "type": "function",
            "function": {
                "name": "crop_pierres_detail_panel",
                "arguments": json.dumps({
                    "image_path": "/workspaces/stardew-vision/tests/fixtures/pierre_shop_001.png"
                })
            }
        }
    }

if __name__ == "__main__":
    print("=" * 80)
    print("MODULE 1: MANUAL TOOL DISPATCH")
    print("=" * 80)
    print()

    # Show tool definitions
    print("Tool Definitions:")
    print(json.dumps(TOOL_DEFINITIONS, indent=2))
    print()

    # Simulate VLM response
    print("Simulated VLM Response:")
    vlm_response = simulate_vlm_response()
    print(json.dumps(vlm_response, indent=2))
    print()

    # Parse and dispatch
    print("Parsing and Dispatching:")
    tool_call = vlm_response["tool_call"]
    tool_name = tool_call["function"]["name"]
    arguments = json.loads(tool_call["function"]["arguments"])

    result = dispatch_tool(tool_name, arguments)

    print()
    print("✅ Module 1 Complete!")
    print("You now understand:")
    print("  - OpenAI function-calling format")
    print("  - Tool registry pattern")
    print("  - Manual dispatch logic")
    print()
    print("Next: Module 2 - Smolagents automates this!")
```

### Verification

```bash
python examples/module1_manual_dispatch.py
```

Expected output:
- Tool definitions printed
- Simulated VLM response
- Tool dispatched successfully
- Extraction result JSON

### Key Takeaways

1. **Tool definitions are just metadata** - JSON describing function signature
2. **Tool registry is a dict** - Maps names to callable functions
3. **Dispatch is simple** - Look up function, call with args
4. **VLM returns structured JSON** - Not magic, just JSON parsing

### Exercise

**File**: `exercises/exercise1_tool_creation.md`

Create a second tool:
- Name: `get_screen_type`
- Description: "Identify which UI panel is shown in screenshot"
- Parameters: `image_path`
- Returns: `{"screen_type": "pierre_shop" | "tv_dialog" | "inventory"}`

Add to `TOOL_DEFINITIONS` and `TOOL_REGISTRY`, test with `dispatch_tool()`.

---

## Module 2: Smolagents Basics (2-3 hours)

### Learning Objectives

- Install Smolagents
- Create custom `Tool` class
- Understand CodeAgent vs ToolCallingAgent
- Run first agent with transformers backend

### Why Smolagents?

- **VLM-optimized**: First-class support for vision, video, audio
- **Model-agnostic**: Works with Qwen, GPT, Claude, local models
- **CodeAgent paradigm**: Writes Python code (not JSON) to call tools
- **Minimal complexity**: ~1000 lines of code, easy to understand
- **Hub integrations**: Share tools as Spaces

### Installation

```bash
# Install with toolkit and LiteLLM support
uv add 'smolagents[toolkit,litellm]'

# Verify
python -c "import smolagents; print(smolagents.__version__)"
```

### Hands-On Activity

**File**: `examples/module2_smolagents_basic.py`

**Tasks**:
1. Create custom `Tool` class for Pierre's extraction
2. Initialize CodeAgent with tool
3. Run agent with test screenshot
4. Examine generated Python code

**Code Pattern**:

```python
"""
Module 2: Smolagents basics - first agent.
Purpose: Learn Smolagents Tool and CodeAgent classes.
"""
from smolagents import CodeAgent, Tool, InferenceClientModel
from PIL import Image
import json

class CropPierresPanelTool(Tool):
    """
    Smolagents Tool wrapper for crop_pierres_detail_panel.

    Tool classes define:
    - name: Tool identifier (matches function name)
    - description: What the tool does (shown to VLM)
    - inputs: Parameter schema (type, description)
    - output_type: Return type (str, dict, Image, etc.)
    - forward(): Actual implementation
    """
    name = "crop_pierres_detail_panel"
    description = "Extract item details from Pierre's General Store detail panel in screenshot"

    inputs = {
        "image_path": {
            "type": "string",
            "description": "Path to the screenshot file"
        }
    }

    output_type = "dict"

    def forward(self, image_path: str):
        """Execute the extraction tool."""
        from stardew_vision.tools import crop_pierres_detail_panel

        print(f"[CropPierresPanelTool] Executing on {image_path}")
        result = crop_pierres_detail_panel(image_path)
        print(f"[CropPierresPanelTool] Extraction successful: {result}")

        return result

def run_smolagents_basic():
    """Run CodeAgent with transformers backend."""
    print("=" * 80)
    print("MODULE 2: SMOLAGENTS BASICS")
    print("=" * 80)
    print()

    # Initialize model (transformers backend, downloads from HF Hub)
    print("Loading model (InferenceClientModel)...")
    model = InferenceClientModel(
        model_id="Qwen/Qwen2.5-VL-7B-Instruct"
    )
    print("Model loaded!")
    print()

    # Create tools
    tools = [CropPierresPanelTool()]

    # Initialize CodeAgent
    print("Initializing CodeAgent...")
    agent = CodeAgent(
        tools=tools,
        model=model,
        add_base_tools=False,  # Don't add default DuckDuckGo, etc.
        max_steps=3,           # Limit iterations
        verbosity=2            # Show reasoning
    )
    print("Agent initialized!")
    print()

    # Run agent
    image_path = "/workspaces/stardew-vision/tests/fixtures/pierre_shop_001.png"

    print(f"Running agent on: {image_path}")
    print("-" * 80)

    result = agent.run(
        f"Extract all item information from the Pierre's General Store screenshot at {image_path}. "
        f"Use the crop_pierres_detail_panel tool."
    )

    print("-" * 80)
    print()
    print("Agent Result:")
    print(json.dumps(result, indent=2))
    print()

    print("✅ Module 2 Complete!")
    print("You now understand:")
    print("  - How to create Smolagents Tool classes")
    print("  - How CodeAgent writes Python code to call tools")
    print("  - How InferenceClientModel works with HF models")

if __name__ == "__main__":
    run_smolagents_basic()
```

### CodeAgent vs ToolCallingAgent

**CodeAgent** (recommended):
- Writes **Python code** to call tools
- More robust (type-checked at runtime)
- Composable (can chain tools in code)
- Example output:
  ```python
  image_path = "/path/to/screenshot.png"
  result = crop_pierres_detail_panel(image_path=image_path)
  print(result)
  ```

**ToolCallingAgent**:
- Uses **JSON function calling** (like OpenAI)
- Compatible with more models
- Less flexible than Python code
- Example output:
  ```json
  {
    "tool": "crop_pierres_detail_panel",
    "arguments": {"image_path": "/path/to/screenshot.png"}
  }
  ```

**Recommendation**: Use CodeAgent for Qwen2.5-VL.

### Verification

```bash
python examples/module2_smolagents_basic.py
```

Expected output:
- Model loads (may download from HF Hub)
- Agent runs and generates Python code
- Tool executes successfully
- Extraction result returned

### Key Takeaways

1. **Tool class encapsulates everything** - name, description, inputs, implementation
2. **CodeAgent writes Python** - More robust than JSON
3. **InferenceClientModel is easy** - Just model ID, Smolagents handles rest
4. **Verbosity is helpful** - See what agent is thinking

### Exercise

**File**: `exercises/exercise2_agent_config.md`

Experiment with CodeAgent parameters:
- Try `max_steps=1` (single-shot)
- Try `verbosity=0` (silent)
- Try `add_base_tools=True` (see what default tools do)
- Add second tool and see if agent picks correct one

---

## Module 3: Smolagents + vLLM (2-3 hours)

### Learning Objectives

- Start vLLM server with tool calling enabled
- Use LiteLLMModel backend for vLLM
- Configure endpoint and API key
- Debug connection issues

### Why vLLM?

- **Production serving**: OpenAI-compatible API
- **GPU acceleration**: Faster than transformers
- **Tool calling support**: Native function calling
- **Same client code**: Works for local and OpenShift AI

### vLLM Setup

```bash
# Terminal 1: Start vLLM server
vllm serve /workspaces/stardew-vision/models/base/Qwen2.5-VL-7B-Instruct \
  --port 8001 \
  --dtype float16 \
  --enable-tool-calling \
  --max-model-len 4096

# Verify server is running
curl http://localhost:8001/v1/models
```

### Hands-On Activity

**File**: `examples/module3_smolagents_vllm.py`

**Tasks**:
1. Start vLLM server (separate terminal)
2. Configure LiteLLMModel to use vLLM endpoint
3. Run CodeAgent with vLLM backend
4. Compare performance with transformers

**Code Pattern**:

```python
"""
Module 3: Smolagents + vLLM integration.
Purpose: Use vLLM endpoint with LiteLLMModel backend.
"""
from smolagents import CodeAgent, Tool, LiteLLMModel
import json

class CropPierresPanelTool(Tool):
    """Same tool from Module 2."""
    name = "crop_pierres_detail_panel"
    description = "Extract item details from Pierre's General Store detail panel in screenshot"
    inputs = {
        "image_path": {
            "type": "string",
            "description": "Path to the screenshot file"
        }
    }
    output_type = "dict"

    def forward(self, image_path: str):
        from stardew_vision.tools import crop_pierres_detail_panel
        print(f"[Tool] Executing on {image_path}")
        result = crop_pierres_detail_panel(image_path)
        print(f"[Tool] Result: {result}")
        return result

def run_smolagents_vllm():
    """Run CodeAgent with vLLM backend."""
    print("=" * 80)
    print("MODULE 3: SMOLAGENTS + vLLM")
    print("=" * 80)
    print()

    # Configure LiteLLMModel for vLLM endpoint
    print("Connecting to vLLM endpoint at http://localhost:8001...")
    model = LiteLLMModel(
        model_id="Qwen2.5-VL-7B-Instruct",  # Model name for vLLM
        base_url="http://localhost:8001/v1",  # vLLM OpenAI-compatible endpoint
        api_key="EMPTY"  # vLLM doesn't require auth for local
    )
    print("Connected!")
    print()

    # Create tools
    tools = [CropPierresPanelTool()]

    # Initialize CodeAgent (same as Module 2, different model)
    print("Initializing CodeAgent with vLLM backend...")
    agent = CodeAgent(
        tools=tools,
        model=model,
        add_base_tools=False,
        max_steps=3,
        verbosity=2
    )
    print("Agent initialized!")
    print()

    # Run agent
    image_path = "/workspaces/stardew-vision/tests/fixtures/pierre_shop_001.png"

    print(f"Running agent on: {image_path}")
    print("-" * 80)

    result = agent.run(
        f"Extract item information from screenshot at {image_path} using crop_pierres_detail_panel."
    )

    print("-" * 80)
    print()
    print("Agent Result:")
    print(json.dumps(result, indent=2))
    print()

    print("✅ Module 3 Complete!")
    print("You now understand:")
    print("  - How to connect Smolagents to vLLM endpoint")
    print("  - How LiteLLMModel works (OpenAI-compatible wrapper)")
    print("  - Same agent code, different backend")
    print("  - This pattern works for OpenShift AI too!")

if __name__ == "__main__":
    # Check vLLM is running
    import requests
    try:
        r = requests.get("http://localhost:8001/v1/models", timeout=5)
        r.raise_for_status()
        print("✅ vLLM server detected")
        print()
    except Exception as e:
        print("❌ vLLM server not running!")
        print("Start it with:")
        print("  vllm serve models/base/Qwen2.5-VL-7B-Instruct --port 8001 --dtype float16 --enable-tool-calling")
        print()
        exit(1)

    run_smolagents_vllm()
```

### Debugging vLLM Connection

**Common issues**:

1. **Connection refused**:
   ```bash
   # Check vLLM is running
   curl http://localhost:8001/v1/models
   ```

2. **Tool calling not enabled**:
   ```bash
   # Restart vLLM with --enable-tool-calling flag
   vllm serve ... --enable-tool-calling
   ```

3. **Port already in use**:
   ```bash
   # Find process on port 8001
   lsof -i :8001
   # Kill it or use different port
   ```

4. **Model not found**:
   ```bash
   # Verify model path exists
   ls -la /workspaces/stardew-vision/models/base/Qwen2.5-VL-7B-Instruct
   ```

### Verification

```bash
# Terminal 1: vLLM server (keep running)
vllm serve models/base/Qwen2.5-VL-7B-Instruct --port 8001 --dtype float16 --enable-tool-calling

# Terminal 2: Run example
python examples/module3_smolagents_vllm.py
```

Expected output:
- vLLM connection successful
- Agent runs faster than Module 2
- Tool executes and returns result

### Key Takeaways

1. **LiteLLMModel is universal** - Works with vLLM, OpenAI, Anthropic, etc.
2. **Same agent code** - Only model initialization changes
3. **vLLM is production-ready** - Use for serving
4. **OpenAI-compatible API** - Standard pattern

### Exercise

**File**: `exercises/exercise3_debugging.md`

Debug these scenarios:
1. vLLM not running - handle gracefully
2. Wrong endpoint URL - timeout error
3. Model doesn't support tool calling - fallback
4. Tool execution fails - error handling

---

## Module 4: Production Wrapper (2-3 hours)

### Learning Objectives

- Create VLMOrchestrator class
- Implement error handling and validation
- Add MLFlow logging
- Write unit tests with pytest
- Mock VLM responses for testing

### Production Requirements

- **Error handling**: VLM failures, tool errors, validation errors
- **Logging**: All tool calls logged to MLFlow
- **Testing**: Unit tests with mocked VLM
- **Observability**: Latency tracking, success/failure rates
- **Validation**: JSON schema validation

### Hands-On Activity

**File**: `src/stardew_vision/models/vlm_wrapper.py`

**Code Pattern**:

```python
"""
VLM orchestrator wrapper using Smolagents.
Production-ready with error handling, logging, testing.
"""
import json
import logging
from typing import Optional, Dict, Any
from pathlib import Path
from smolagents import CodeAgent, Tool, LiteLLMModel
import mlflow

logger = logging.getLogger(__name__)

class PierresPanelTool(Tool):
    """Smolagents tool wrapper for Pierre's shop extraction."""
    name = "crop_pierres_detail_panel"
    description = "Extract item details from Pierre's General Store detail panel in screenshot"
    inputs = {
        "image_path": {
            "type": "string",
            "description": "Path to the screenshot file"
        }
    }
    output_type = "dict"

    def forward(self, image_path: str):
        """Execute the extraction tool."""
        from stardew_vision.tools import crop_pierres_detail_panel
        logger.info(f"Executing {self.name} on {image_path}")
        try:
            result = crop_pierres_detail_panel(image_path)
            logger.info(f"Extraction successful: {result}")
            return result
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            raise

class VLMOrchestrator:
    """
    Orchestrator VLM using Smolagents CodeAgent.
    Classifies screenshot and dispatches tool calls.
    """

    def __init__(
        self,
        model_id: str = "Qwen2.5-VL-7B-Instruct",
        use_vllm: bool = True,
        vllm_endpoint: str = "http://localhost:8001/v1",
        enable_mlflow: bool = True
    ):
        """
        Initialize orchestrator.

        Args:
            model_id: HuggingFace model ID
            use_vllm: If True, use vLLM via LiteLLM; if False, use transformers
            vllm_endpoint: vLLM server endpoint
            enable_mlflow: Enable MLFlow logging
        """
        self.model_id = model_id
        self.use_vllm = use_vllm
        self.enable_mlflow = enable_mlflow

        # Initialize model
        if use_vllm:
            logger.info(f"Using vLLM endpoint: {vllm_endpoint}")
            self.model = LiteLLMModel(
                model_id=model_id,
                base_url=vllm_endpoint,
                api_key="EMPTY"
            )
        else:
            logger.info(f"Using transformers with model: {model_id}")
            from smolagents import InferenceClientModel
            self.model = InferenceClientModel(model_id=model_id)

        # Initialize tools
        self.tools = [PierresPanelTool()]

        # Initialize agent
        self.agent = CodeAgent(
            tools=self.tools,
            model=self.model,
            add_base_tools=False,
            max_steps=3,
            verbosity=1
        )

        logger.info("VLMOrchestrator initialized successfully")

    def analyze_screenshot(self, image_path: str) -> Dict[str, Any]:
        """
        Classify screenshot and extract fields.

        Args:
            image_path: Path to screenshot file

        Returns:
            Extracted fields as dict

        Raises:
            ValueError: If extraction fails
            FileNotFoundError: If image not found
        """
        # Validate image exists
        if not Path(image_path).exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        logger.info(f"Analyzing screenshot: {image_path}")

        # Start MLFlow run
        if self.enable_mlflow:
            mlflow.start_run()
            mlflow.log_param("image_path", image_path)
            mlflow.log_param("model_id", self.model_id)
            mlflow.log_param("use_vllm", self.use_vllm)

        try:
            # Run agent
            result = self.agent.run(
                f"Extract all item information from the Pierre's General Store screenshot at {image_path}. "
                f"Use the crop_pierres_detail_panel tool and return the complete result."
            )

            logger.info("Analysis successful")

            if self.enable_mlflow:
                mlflow.log_dict(result, "extraction_result.json")
                mlflow.log_metric("success", 1)

            return result

        except Exception as e:
            logger.error(f"Analysis failed: {e}")

            if self.enable_mlflow:
                mlflow.log_metric("success", 0)
                mlflow.log_param("error", str(e))

            raise ValueError(f"VLM analysis failed: {e}")

        finally:
            if self.enable_mlflow:
                mlflow.end_run()
```

### Unit Tests

**File**: `tests/test_vlm_wrapper.py`

```python
"""
Unit tests for VLMOrchestrator.
Uses mocking to avoid running actual VLM.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from stardew_vision.models.vlm_wrapper import VLMOrchestrator

@pytest.fixture
def orchestrator():
    """Create VLMOrchestrator with mocked components."""
    with patch('stardew_vision.models.vlm_wrapper.LiteLLMModel'):
        orch = VLMOrchestrator(enable_mlflow=False)
        return orch

def test_orchestrator_initialization(orchestrator):
    """Test orchestrator initializes correctly."""
    assert orchestrator.model_id == "Qwen2.5-VL-7B-Instruct"
    assert orchestrator.use_vllm is True
    assert len(orchestrator.tools) == 1

def test_analyze_screenshot_success(orchestrator, tmp_path):
    """Test successful screenshot analysis."""
    # Create dummy image
    image_path = tmp_path / "test.png"
    image_path.write_bytes(b"fake image")

    # Mock agent result
    expected_result = {
        "name": "Parsnip",
        "description": "A spring vegetable",
        "price_per_unit": 20,
        "quantity_selected": 5,
        "total_cost": 100
    }
    orchestrator.agent.run = Mock(return_value=expected_result)

    # Test
    result = orchestrator.analyze_screenshot(str(image_path))

    assert result == expected_result
    orchestrator.agent.run.assert_called_once()

def test_analyze_screenshot_file_not_found(orchestrator):
    """Test error when image file not found."""
    with pytest.raises(FileNotFoundError):
        orchestrator.analyze_screenshot("/nonexistent/path.png")

def test_analyze_screenshot_vlm_failure(orchestrator, tmp_path):
    """Test error handling when VLM fails."""
    image_path = tmp_path / "test.png"
    image_path.write_bytes(b"fake image")

    # Mock VLM failure
    orchestrator.agent.run = Mock(side_effect=Exception("VLM timeout"))

    with pytest.raises(ValueError, match="VLM analysis failed"):
        orchestrator.analyze_screenshot(str(image_path))

@pytest.mark.integration
def test_analyze_screenshot_real_vllm():
    """Integration test with real vLLM server (requires vLLM running)."""
    import requests

    # Check vLLM is running
    try:
        requests.get("http://localhost:8001/v1/models", timeout=2)
    except:
        pytest.skip("vLLM server not running")

    # Create orchestrator
    orch = VLMOrchestrator(enable_mlflow=False)

    # Test with real screenshot
    result = orch.analyze_screenshot(
        "/workspaces/stardew-vision/tests/fixtures/pierre_shop_001.png"
    )

    # Verify result structure
    assert isinstance(result, dict)
    assert "name" in result or "error" in result
```

### Verification

```bash
# Unit tests (no vLLM required)
pytest tests/test_vlm_wrapper.py -v

# Integration test (requires vLLM)
pytest tests/test_vlm_wrapper.py -v -m integration
```

### Key Takeaways

1. **Production code needs error handling** - Don't assume success
2. **Logging is essential** - MLFlow for observability
3. **Unit tests with mocks** - Fast, no dependencies
4. **Integration tests separate** - Marked with `@pytest.mark.integration`

---

## Module 5: FastAPI Integration (1-2 hours)

### Learning Objectives

- Create FastAPI routes for screenshot upload
- Handle file uploads and temporary storage
- Connect VLMOrchestrator to web endpoint
- Test with curl and browser

### Why FastAPI?

- **Async support**: Non-blocking I/O for VLM calls
- **Automatic docs**: Interactive API at `/docs`
- **Type validation**: Pydantic models
- **Production-ready**: Used by many ML APIs

### Hands-On Activity

**File**: `src/stardew_vision/webapp/routes.py`

**Code Pattern**:

```python
"""
FastAPI routes for Stardew Vision.
Handles screenshot uploads and returns audio narration.
"""
from fastapi import APIRouter, UploadFile, HTTPException, File
from fastapi.responses import JSONResponse
from stardew_vision.models.vlm_wrapper import VLMOrchestrator
import tempfile
from pathlib import Path
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize orchestrator (singleton)
orchestrator = VLMOrchestrator(enable_mlflow=True)

@router.post("/analyze")
async def analyze_screenshot(file: UploadFile = File(...)):
    """
    Analyze a Stardew Valley screenshot and extract panel contents.

    Args:
        file: Uploaded screenshot (PNG/JPG)

    Returns:
        JSON with extracted fields

    Raises:
        400: Invalid file format
        500: VLM analysis failed
    """
    # Validate file type
    if not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {file.content_type}. Must be image."
        )

    logger.info(f"Received upload: {file.filename} ({file.content_type})")

    # Save to temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        # Analyze with orchestrator
        result = orchestrator.analyze_screenshot(tmp_path)

        logger.info(f"Analysis successful: {result}")

        return JSONResponse(content={
            "success": True,
            "filename": file.filename,
            "extraction": result
        })

    except FileNotFoundError as e:
        logger.error(f"File error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    except ValueError as e:
        logger.error(f"VLM error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        # Clean up temporary file
        Path(tmp_path).unlink(missing_ok=True)

@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "model": orchestrator.model_id}
```

**File**: `src/stardew_vision/webapp/app.py`

```python
"""
FastAPI application for Stardew Vision.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from stardew_vision.webapp.routes import router
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app = FastAPI(
    title="Stardew Vision API",
    description="Extract UI panel contents from Stardew Valley screenshots",
    version="0.1.0"
)

# CORS for browser access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(router, prefix="/api/v1", tags=["analysis"])

@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": "Stardew Vision API",
        "version": "0.1.0",
        "docs": "/docs"
    }
```

### Running the Web App

```bash
# Terminal 1: vLLM server (keep running)
vllm serve models/base/Qwen2.5-VL-7B-Instruct --port 8001 --dtype float16 --enable-tool-calling

# Terminal 2: FastAPI app
uvicorn stardew_vision.webapp.app:app --host 0.0.0.0 --port 8000 --reload

# Terminal 3: Test with curl
curl -X POST http://localhost:8000/api/v1/analyze \
  -F "file=@tests/fixtures/pierre_shop_001.png"

# Or open browser
open http://localhost:8000/docs
```

### Verification

1. **Health check**:
   ```bash
   curl http://localhost:8000/api/v1/health
   ```

2. **Screenshot analysis**:
   ```bash
   curl -X POST http://localhost:8000/api/v1/analyze \
     -F "file=@tests/fixtures/pierre_shop_001.png" \
     | jq .
   ```

3. **Interactive docs**:
   - Open `http://localhost:8000/docs`
   - Upload screenshot via browser
   - See result immediately

### Key Takeaways

1. **Temporary files** - Clean up after processing
2. **Error handling** - Return proper HTTP status codes
3. **Async patterns** - Non-blocking VLM calls
4. **FastAPI docs** - Auto-generated, interactive

---

## Module 6: Advanced & Alternatives (1-2 hours)

### Learning Objectives

- When to use raw client vs Smolagents
- When to add LangGraph (Phase 2+)
- Conference demo scripts
- Hub tool sharing

### Decision Framework

**Use Raw OpenAI Client when**:
- Maximum control required
- No framework lock-in desired
- Single-shot tool calling
- Simplest possible code

**Use Smolagents when**:
- VLM-optimized features needed
- Multi-modal (vision, video, audio)
- Hub integrations desired
- CodeAgent paradigm preferred

**Add LangGraph when**:
- Complex conditional routing
- Multi-step state machines
- Phase 2+ multi-screen support

**Add CrewAI when**:
- Multi-agent collaboration
- Validator agent needed
- Role-based workflows

### Conference Demo Script

**File**: `examples/module6_conference_demo.py`

```python
"""
Module 6: Conference demo progression.
Shows evolution from manual to intelligent to integrated.
"""

def demo_1_manual():
    """Demo 1: Manual tool dispatch (no AI)."""
    print("\n" + "=" * 80)
    print("DEMO 1: MANUAL TOOL DISPATCH (No AI)")
    print("=" * 80)
    print()
    print("This is where we started:")
    print("  - Tool definitions in JSON")
    print("  - Manual registry lookup")
    print("  - No intelligence, just dispatch")
    print()

    from stardew_vision.tools import TOOL_REGISTRY
    result = TOOL_REGISTRY["crop_pierres_detail_panel"](
        "/workspaces/stardew-vision/tests/fixtures/pierre_shop_001.png"
    )
    print("Result:", result)
    print()
    print("✅ Works, but requires manual classification")

def demo_2_smolagents():
    """Demo 2: Smolagents CodeAgent (AI-powered)."""
    print("\n" + "=" * 80)
    print("DEMO 2: SMOLAGENTS CODEAGENT (AI-Powered)")
    print("=" * 80)
    print()
    print("Now with VLM intelligence:")
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
    print("  - Can add TTS → audio response")
    print()
    print("Upload screenshot:")
    print("  curl -X POST http://localhost:8000/api/v1/analyze \\")
    print("    -F 'file=@screenshot.png'")
    print()
    print("Returns:")
    print("  {")
    print("    \"success\": true,")
    print("    \"extraction\": {\"name\": \"Parsnip\", ...},")
    print("    \"audio_url\": \"/audio/result.wav\"  # TODO: Phase 2")
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
    print("  ✅ Open path to complexity (multi-agent, multi-step)")
    print()
    print("When to use alternatives:")
    print("  - Raw client: Maximum control")
    print("  - LangGraph: Complex state machines")
    print("  - CrewAI: Multi-agent collaboration")
    print()
    print("✅ Choose based on actual complexity, not anticipated!")

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
```

### Hub Tool Sharing

Share tools on HuggingFace Hub:

```python
"""Share PierresPanelTool as HuggingFace Space."""
from smolagents import Tool

class PierresPanelTool(Tool):
    # ... (same as before)
    pass

# Push to Hub
tool = PierresPanelTool()
tool.push_to_hub("username/pierre-panel-tool")

# Others can use it
from smolagents import load_tool
tool = load_tool("username/pierre-panel-tool")
```

### Verification

```bash
python examples/module6_conference_demo.py
```

Expected output:
- All 4 demos execute successfully
- Shows progression clearly
- Framework rationale explained

### Key Takeaways

1. **Framework minimalism** - Use raw code until complexity demands abstraction
2. **Progressive enhancement** - Start simple, add intelligence incrementally
3. **Decision criteria** - Choose based on actual needs, not anticipated
4. **Conference-ready** - Clear progression tells compelling story

---

## Summary

You've completed the agent/tool-calling curriculum! You now have:

1. ✅ **Production VLMOrchestrator** using Smolagents
2. ✅ **FastAPI web endpoint** for screenshot upload
3. ✅ **Unit tests** with mocking
4. ✅ **MLFlow observability** for all tool calls
5. ✅ **Conference demo** materials
6. ✅ **Framework comparison** knowledge
7. ✅ **Decision framework** for choosing tools

## Next Steps

**Phase 2: Multi-Screen Support**
- Add TV dialog tool
- Conditional routing (if needed → consider LangGraph)
- Multi-tool selection

**Phase 3: Validation Agent**
- Quality checks on extraction
- Multi-agent pattern (consider CrewAI or Smolagents multi-agent)

**Production Deployment**
- OpenShift AI KServe for vLLM
- Same LiteLLMModel code, different endpoint
- MLFlow tracking in production

**Conference Talks**
- Use demo progression script
- Show framework comparison
- Explain decision rationale
- Live coding: Manual → Intelligent in 15 minutes

---

**Congratulations!** 🎉

You've mastered agent/tool-calling patterns with VLMs using Smolagents!
