# Module 4: Production Wrapper

**Duration**: 2-3 hours
**Prerequisites**: Modules 1-3 completed, pytest installed
**Example Code**: [`examples/module4_production_wrapper.py`](../examples/module4_production_wrapper.py)

---

## Learning Objectives

By the end of this module, you will:

- ✅ Create a production-ready `VLMOrchestrator` class
- ✅ Implement error handling and validation
- ✅ Add MLFlow integration for observability
- ✅ Write unit tests with mocking
- ✅ Understand testing strategies for VLM systems

---

## Why a Production Wrapper?

The examples in Modules 1-3 work great for learning, but they're **not production-ready**.

**What's missing?**

### 1. Error Handling

**Module 3 code**:
```python
result = agent.run("Extract from screenshot")
print(result)
```

**What if**:
- ❌ vLLM server is down?
- ❌ Image file doesn't exist?
- ❌ VLM returns malformed response?
- ❌ Tool execution fails?
- ❌ Network timeout?

**Result**: Your app crashes with cryptic errors.

### 2. Observability

**Module 3**: No logging, no metrics, no tracking

**Production needs**:
- ✅ Log every tool call
- ✅ Track latency metrics
- ✅ Record success/failure rates
- ✅ Store results for debugging
- ✅ Monitor model performance

### 3. Testing

**Module 3**: Can only test with real VLM running

**Production needs**:
- ✅ Unit tests without vLLM
- ✅ Mock VLM responses
- ✅ Test error cases
- ✅ Fast test suite (seconds, not minutes)

### 4. Configuration

**Module 3**: Hardcoded values

**Production needs**:
- ✅ Environment-specific config
- ✅ Easy to switch models
- ✅ Configurable retries, timeouts
- ✅ Feature flags

**Module 4 solves these problems** with a `VLMOrchestrator` wrapper class.

---

## Production Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    VLMORCHESTRATOR                           │
└──────────────────────────────────────────────────────────────┘

                    ┌──────────────────────┐
                    │  VLMOrchestrator     │
                    │  (Production Wrapper)│
                    └──────────┬───────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
        ▼                      ▼                      ▼
┌───────────────┐    ┌─────────────────┐    ┌──────────────┐
│ Error         │    │ MLFlow          │    │ Validation   │
│ Handling      │    │ Logging         │    │ Layer        │
│               │    │                 │    │              │
│ - Retries     │    │ - Parameters    │    │ - Schema     │
│ - Fallbacks   │    │ - Metrics       │    │ - Required   │
│ - Timeouts    │    │ - Artifacts     │    │   fields     │
└───────────────┘    └─────────────────┘    └──────────────┘
        │                      │                      │
        └──────────────────────┼──────────────────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │  CodeAgent           │
                    │  (from Module 2-3)   │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │  Tool Execution      │
                    └──────────────────────┘


FLOW WITH ERROR HANDLING:

User Request
     │
     ▼
VLMOrchestrator.analyze_screenshot()
     │
     ├─► Validate input (file exists?)
     │   └─► If invalid: raise clear error
     │
     ├─► Start MLFlow run
     │   └─► Log parameters (model, image path, etc.)
     │
     ├─► Call agent.run() [with timeout]
     │   │
     │   ├─► Success
     │   │   ├─► Validate result (schema check)
     │   │   ├─► Log metrics (success=1, latency)
     │   │   └─► Return result
     │   │
     │   └─► Failure
     │       ├─► Log error (success=0, error message)
     │       ├─► Retry if transient error
     │       └─► Return error response
     │
     └─► End MLFlow run
```

---

## Code Walkthrough: VLMOrchestrator

### Part 1: Imports and Setup (Lines 1-20)

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
import time

logger = logging.getLogger(__name__)
```

**New imports**:
- `logging` - Python logging (replace print statements)
- `typing` - Type hints for better IDE support
- `Path` - File path handling
- `mlflow` - Experiment tracking and observability
- `time` - Latency tracking

**Why logging instead of print?**
```python
# Bad (Module 3)
print("Starting agent...")  # Goes to stdout, hard to filter

# Good (Module 4)
logger.info("Starting agent...")  # Structured, filterable, configurable
```

### Part 2: Tool Class (Lines 22-45)

```python
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
```

**Changes from Module 3**:
- ✅ `logger.info()` instead of `print()`
- ✅ Try/except block in `forward()`
- ✅ Log errors before re-raising

**Why re-raise after logging?**
```python
try:
    result = crop_pierres_detail_panel(image_path)
    return result
except Exception as e:
    logger.error(f"Tool execution failed: {e}")
    raise  # Let orchestrator handle it!
```

Tool logs the error (for debugging), but lets orchestrator decide how to handle (retry, fallback, etc.).

### Part 3: VLMOrchestrator Class (Lines 47-110)

```python
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
```

**Why a class instead of functions?**

**Functions (Module 3)**:
```python
model = LiteLLMModel(...)
tools = [MyTool()]
agent = CodeAgent(...)

result = agent.run(...)  # Global state
```

**Class (Module 4)**:
```python
orchestrator = VLMOrchestrator()
result = orchestrator.analyze_screenshot(...)  # Encapsulated state
```

**Benefits**:
- ✅ Encapsulated configuration
- ✅ Reusable (create once, call many times)
- ✅ Testable (mock dependencies)
- ✅ Configurable (constructor params)

**Constructor parameters**:
- `model_id`: Which model to use
- `use_vllm`: vLLM (fast) or transformers (easy)
- `vllm_endpoint`: Where to find vLLM
- `enable_mlflow`: Turn logging on/off (off for tests)

**Flexible model backend**:
```python
if use_vllm:
    self.model = LiteLLMModel(...)  # Production
else:
    self.model = InferenceClientModel(...)  # Fallback
```

This allows graceful degradation if vLLM is unavailable.

### Part 4: Main Method with Error Handling (Lines 112-185)

```python
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
        # Track latency
        start_time = time.time()

        # Run agent
        result = self.agent.run(
            f"Extract all item information from the Pierre's General Store screenshot at {image_path}. "
            f"Use the crop_pierres_detail_panel tool and return the complete result."
        )

        # Calculate latency
        latency = time.time() - start_time

        logger.info("Analysis successful")

        if self.enable_mlflow:
            mlflow.log_dict(result, "extraction_result.json")
            mlflow.log_metric("success", 1)
            mlflow.log_metric("latency_seconds", latency)

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

**Line-by-line breakdown**:

**Lines 125-127: Input validation**
```python
if not Path(image_path).exists():
    raise FileNotFoundError(f"Image not found: {image_path}")
```

**Why validate early?**
- Fail fast with clear error
- Don't waste VLM time on invalid input
- Better error messages for users

**Lines 132-136: MLFlow run start**
```python
if self.enable_mlflow:
    mlflow.start_run()
    mlflow.log_param("image_path", image_path)
    mlflow.log_param("model_id", self.model_id)
    mlflow.log_param("use_vllm", self.use_vllm)
```

**MLFlow concepts**:
- **Run**: One execution (one screenshot analyzed)
- **Parameters**: Input config (what model, what image, etc.)
- **Metrics**: Output measurements (success, latency, etc.)
- **Artifacts**: Files (extracted JSON, etc.)

**Lines 138-145: Execute with latency tracking**
```python
start_time = time.time()
result = self.agent.run(...)
latency = time.time() - start_time
```

**Why track latency?**
- Monitor performance over time
- Detect slowdowns
- Optimize bottlenecks

**Lines 150-153: Log success metrics**
```python
if self.enable_mlflow:
    mlflow.log_dict(result, "extraction_result.json")  # Artifact
    mlflow.log_metric("success", 1)
    mlflow.log_metric("latency_seconds", latency)
```

**Logged to MLFlow**:
- Artifact: `extraction_result.json` (actual result)
- Metric: `success=1` (for filtering successful runs)
- Metric: `latency_seconds=1.23` (for performance analysis)

**Lines 157-162: Error handling**
```python
except Exception as e:
    logger.error(f"Analysis failed: {e}")

    if self.enable_mlflow:
        mlflow.log_metric("success", 0)  # Failed!
        mlflow.log_param("error", str(e))

    raise ValueError(f"VLM analysis failed: {e}")
```

**Error handling pattern**:
1. Log error (for debugging)
2. Log to MLFlow (for metrics)
3. Re-raise as clear error (for caller)

**Why re-raise?**
- Caller (web app) needs to know it failed
- Can return HTTP 500 error
- Can retry or show user message

**Lines 164-166: Cleanup**
```python
finally:
    if self.enable_mlflow:
        mlflow.end_run()
```

**Why finally block?**
- Runs even if exception raised
- Ensures MLFlow run is closed
- Prevents orphaned runs

---

## Testing Strategy

### Why Mock the VLM?

**Problem**: Real VLM tests are:
- ❌ Slow (2-10 seconds per test)
- ❌ Flaky (network issues, GPU availability)
- ❌ Expensive (GPU compute)
- ❌ Hard to test edge cases (how to trigger errors?)

**Solution**: Mock the VLM response

**Mock tests are**:
- ✅ Fast (<0.1 seconds per test)
- ✅ Reliable (no external dependencies)
- ✅ Cheap (CPU only)
- ✅ Comprehensive (test all error cases)

### Unit Test Example (Lines 1-50 in test file)

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
```

**Key testing patterns**:

**1. Fixtures** (Lines 10-13):
```python
@pytest.fixture
def orchestrator():
    """Create VLMOrchestrator with mocked components."""
    with patch('stardew_vision.models.vlm_wrapper.LiteLLMModel'):
        orch = VLMOrchestrator(enable_mlflow=False)
        return orch
```

**What's happening?**
- `@pytest.fixture`: Runs before each test
- `patch(...)`: Mock LiteLLMModel (don't create real model)
- `enable_mlflow=False`: Don't log to MLFlow in tests
- Returns orchestrator for test to use

**2. Mock agent responses** (Lines 30-35):
```python
expected_result = {"name": "Parsnip", ...}
orchestrator.agent.run = Mock(return_value=expected_result)

result = orchestrator.analyze_screenshot(str(image_path))

assert result == expected_result
```

**What's happening?**
- Replace `agent.run()` with Mock that returns fixed value
- Call orchestrator method
- Verify result matches expected

**No VLM called!** Test runs in milliseconds.

**3. Test error cases** (Lines 49-57):
```python
orchestrator.agent.run = Mock(side_effect=Exception("VLM timeout"))

with pytest.raises(ValueError, match="VLM analysis failed"):
    orchestrator.analyze_screenshot(str(image_path))
```

**What's happening?**
- Mock `agent.run()` to raise exception
- Verify orchestrator raises clear error
- Verify error message contains useful info

**Why this is valuable**:
- Hard to trigger VLM timeouts in real tests
- Easy to simulate with mocks
- Test error handling without breaking anything

### Integration Tests (Lines 60-80)

```python
@pytest.mark.integration
def test_analyze_screenshot_real_vllm():
    """Integration test with real vLLM server (requires vLLM running)."""
    import requests

    # Check vLLM is running
    try:
        requests.get("http://localhost:8001/v1/models", timeout=2)
    except:
        pytest.skip("vLLM server not running")

    # Create orchestrator (real, not mocked)
    orch = VLMOrchestrator(enable_mlflow=False)

    # Test with real screenshot
    result = orch.analyze_screenshot(
        "/workspaces/stardew-vision/tests/fixtures/pierre_shop_001.png"
    )

    # Verify result structure
    assert isinstance(result, dict)
    assert "name" in result or "error" in result
```

**When to use integration tests?**
- Verify end-to-end flow works
- Test actual VLM behavior
- Catch integration issues

**When to use unit tests?**
- Test business logic
- Test error handling
- Fast feedback loop

**Best practice**:
- Many unit tests (100s)
- Few integration tests (10s)
- Marked separately (`@pytest.mark.integration`)

---

## MLFlow Integration

### What is MLFlow?

**MLFlow** = Machine Learning Flow

An experiment tracking platform for ML projects:
- **Track experiments**: Different models, hyperparameters, results
- **Log metrics**: Accuracy, latency, success rate
- **Store artifacts**: Model files, extracted data
- **Compare runs**: Which config performed best?

**Why use MLFlow for Stardew Vision?**
- Track VLM performance over time
- Compare different extraction tools
- Debug failures (view error logs)
- Monitor production (success rates, latency)

### MLFlow Concepts

```
┌─────────────────────────────────────────────────────────┐
│                     MLFLOW RUN                          │
│                                                         │
│  Parameters (Input config):                             │
│    - image_path: "/path/to/screenshot.png"              │
│    - model_id: "Qwen2.5-VL-7B-Instruct"                 │
│    - use_vllm: true                                     │
│                                                         │
│  Metrics (Output measurements):                         │
│    - success: 1                                         │
│    - latency_seconds: 1.23                              │
│                                                         │
│  Artifacts (Files):                                     │
│    - extraction_result.json                             │
│                                                         │
│  Metadata:                                              │
│    - run_id: abc123...                                  │
│    - start_time: 2026-03-20 10:00:00                    │
│    - end_time: 2026-03-20 10:00:01                      │
│    - status: FINISHED                                   │
└─────────────────────────────────────────────────────────┘
```

### Using MLFlow UI

```bash
# Start MLFlow server
mlflow ui --host 0.0.0.0 --port 5000

# Open in browser
http://localhost:5000
```

**UI features**:
- List all runs
- Filter by success/failure
- Compare metrics across runs
- View artifacts
- Search by parameters

### Query MLFlow Programmatically

```python
import mlflow

# Get all successful runs
runs = mlflow.search_runs(
    filter_string="metrics.success = 1"
)

# Get average latency
avg_latency = runs["metrics.latency_seconds"].mean()
print(f"Average latency: {avg_latency:.2f}s")

# Find failed runs
failed = mlflow.search_runs(
    filter_string="metrics.success = 0"
)

# Get error messages
for _, run in failed.iterrows():
    print(f"Error: {run['params.error']}")
```

---

## Hands-On Activity

### Checkpoint 1: Run Production Wrapper

```bash
# Make sure vLLM is running (Terminal 1)
vllm serve /workspaces/stardew-vision/models/base/Qwen2.5-VL-7B-Instruct \
  --port 8001 --dtype float16 --enable-tool-calling

# Run production wrapper example (Terminal 2)
cd /workspaces/stardew-vision
python agent-learning/examples/module4_production_wrapper.py
```

**Expected output**:
```
INFO:__main__:Using vLLM endpoint: http://localhost:8001/v1
INFO:__main__:VLMOrchestrator initialized successfully
INFO:__main__:Analyzing screenshot: /workspaces/stardew-vision/tests/fixtures/pierre_shop_001.png
INFO:__main__:Executing crop_pierres_detail_panel on /workspaces/stardew-vision/tests/fixtures/pierre_shop_001.png
INFO:__main__:Extraction successful: {...}
INFO:__main__:Analysis successful

Result:
{
  "name": "Parsnip",
  "description": "A spring vegetable. Still loved by many.",
  "price_per_unit": 20,
  "quantity_selected": 5,
  "total_cost": 100
}

✅ Module 4 Complete!
```

**Check MLFlow**:
```bash
# View logged run
mlflow ui --port 5000

# Open browser: http://localhost:5000
# See run with parameters and metrics
```

### Checkpoint 2: Run Unit Tests

```bash
# Run unit tests (no vLLM required!)
pytest tests/test_vlm_wrapper.py -v

# Run with coverage
pytest tests/test_vlm_wrapper.py --cov=src/stardew_vision/models
```

**Expected output**:
```
tests/test_vlm_wrapper.py::test_orchestrator_initialization PASSED
tests/test_vlm_wrapper.py::test_analyze_screenshot_success PASSED
tests/test_vlm_wrapper.py::test_analyze_screenshot_file_not_found PASSED
tests/test_vlm_wrapper.py::test_analyze_screenshot_vlm_failure PASSED

===== 4 passed in 0.23s =====
```

**Observe**:
- Tests run in <1 second
- No vLLM required
- All error cases tested

### Checkpoint 3: Run Integration Test

```bash
# Integration test (requires vLLM running)
pytest tests/test_vlm_wrapper.py -v -m integration
```

**Expected output**:
```
tests/test_vlm_wrapper.py::test_analyze_screenshot_real_vllm PASSED

===== 1 passed in 2.45s =====
```

**If vLLM not running**:
```
tests/test_vlm_wrapper.py::test_analyze_screenshot_real_vllm SKIPPED (vLLM server not running)
```

**This is expected!** Integration tests skip if dependencies unavailable.

### Checkpoint 4: Test Error Handling

**Modify example to trigger errors**:

**Test 1: File not found**
```python
orch = VLMOrchestrator(enable_mlflow=False)
result = orch.analyze_screenshot("/nonexistent/path.png")
# Expected: FileNotFoundError with clear message
```

**Test 2: vLLM down**
```python
# Stop vLLM server (CTRL+C in Terminal 1)
orch = VLMOrchestrator(enable_mlflow=True)
result = orch.analyze_screenshot("tests/fixtures/pierre_shop_001.png")
# Expected: ValueError with "VLM analysis failed"
# MLFlow logs: success=0, error message
```

**Test 3: Fallback to transformers**
```python
# vLLM down, use transformers
orch = VLMOrchestrator(use_vllm=False, enable_mlflow=False)
result = orch.analyze_screenshot("tests/fixtures/pierre_shop_001.png")
# Expected: Works, but slower
```

---

## Key Patterns

### Pattern 1: Defensive Input Validation

```python
def analyze_screenshot(self, image_path: str) -> Dict[str, Any]:
    # Validate BEFORE expensive operations
    if not Path(image_path).exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    if not image_path.endswith(('.png', '.jpg', '.jpeg')):
        raise ValueError(f"Unsupported format: {image_path}")

    # Now proceed with VLM call...
```

### Pattern 2: Latency Tracking

```python
start_time = time.time()
result = expensive_operation()
latency = time.time() - start_time

mlflow.log_metric("latency_seconds", latency)
```

### Pattern 3: Success/Failure Metrics

```python
try:
    result = operation()
    mlflow.log_metric("success", 1)
    return result
except Exception as e:
    mlflow.log_metric("success", 0)
    mlflow.log_param("error", str(e))
    raise
```

**Why binary success metric?**
- Easy to calculate success rate
- Filter successful vs failed runs
- Track reliability over time

### Pattern 4: Test Organization

```
tests/
├── test_vlm_wrapper.py      # Unit tests (fast, mocked)
├── test_integration.py       # Integration tests (slow, real VLM)
└── conftest.py               # Shared fixtures
```

**Run subset**:
```bash
# Only unit tests (fast)
pytest tests/test_vlm_wrapper.py

# Only integration tests (slow)
pytest -m integration

# Everything
pytest tests/
```

---

## Common Pitfalls

### Pitfall 1: Forgetting to Close MLFlow Run

**Wrong**:
```python
mlflow.start_run()
result = agent.run(...)
mlflow.log_metric("success", 1)
# Forgot mlflow.end_run()!
```

**Right**:
```python
mlflow.start_run()
try:
    result = agent.run(...)
    mlflow.log_metric("success", 1)
finally:
    mlflow.end_run()  # Always close!
```

### Pitfall 2: Testing with Real VLM in Unit Tests

**Wrong**:
```python
def test_orchestrator():
    # Creates real vLLM connection!
    orch = VLMOrchestrator()
    result = orch.analyze_screenshot(...)
```

**Right**:
```python
def test_orchestrator():
    # Mock the model
    with patch('...LiteLLMModel'):
        orch = VLMOrchestrator(enable_mlflow=False)
        orch.agent.run = Mock(return_value={...})
        result = orch.analyze_screenshot(...)
```

### Pitfall 3: Not Disabling MLFlow in Tests

**Wrong**:
```python
orch = VLMOrchestrator()  # enable_mlflow=True by default!
# Tests create MLFlow runs, pollute tracking
```

**Right**:
```python
orch = VLMOrchestrator(enable_mlflow=False)
# Clean tests, no MLFlow pollution
```

---

## Key Takeaways

### 1. Production Needs More Than Happy Path

Modules 1-3: "How to make it work"
Module 4: "How to make it reliable"

**Production requires**:
- Error handling
- Logging
- Testing
- Monitoring

### 2. MLFlow Provides Observability

Track every run:
- What inputs were used
- What outputs were generated
- How long it took
- Did it succeed?

**Use MLFlow to**:
- Debug failures
- Optimize performance
- Compare approaches

### 3. Mocking Enables Fast Tests

**Without mocking**: 10 tests × 2 seconds = 20 seconds
**With mocking**: 10 tests × 0.02 seconds = 0.2 seconds

**100x faster!**

### 4. Separate Unit and Integration Tests

**Unit tests**: Business logic, error handling
**Integration tests**: End-to-end flow, real VLM

Mark integration tests: `@pytest.mark.integration`

### 5. VLMOrchestrator is Production-Ready

```python
# Create once
orchestrator = VLMOrchestrator()

# Use many times
result1 = orchestrator.analyze_screenshot("image1.png")
result2 = orchestrator.analyze_screenshot("image2.png")

# All calls logged, tracked, error-handled
```

---

## Summary

You now understand:

1. ✅ **Production wrapper pattern** - VLMOrchestrator class
2. ✅ **Error handling** - Validate inputs, catch exceptions, clear errors
3. ✅ **MLFlow integration** - Log params, metrics, artifacts
4. ✅ **Testing strategies** - Unit (fast, mocked) vs integration (slow, real)
5. ✅ **Observability** - Track latency, success rate, errors

**The progression**:
- Module 1: Manual dispatch (fundamentals)
- Module 2: Smolagents (automation)
- Module 3: vLLM (production speed)
- Module 4: Error handling + observability (reliability)
- Module 5: Web integration (user-facing API)

---

## Next Steps

**Current state**:
- ✅ Production-ready orchestrator class
- ✅ Error handling and validation
- ✅ MLFlow observability
- ✅ Comprehensive tests

**Still need**:
- ❌ Web API (how do users interact?)
- ❌ File upload handling
- ❌ Async patterns (non-blocking)

**Module 5** adds FastAPI integration:
- HTTP endpoints for screenshot upload
- Async orchestrator calls
- Health checks
- OpenAPI documentation

---

## Additional Resources

**Code**:
- Full example: [`examples/module4_production_wrapper.py`](../examples/module4_production_wrapper.py)
- Tests: `tests/test_vlm_wrapper.py`

**Diagrams**:
- [`diagrams/production-pipeline.txt`](../diagrams/production-pipeline.txt) - Full flow with observability

**Documentation**:
- [MLFlow Documentation](https://mlflow.org/docs/latest/index.html)
- [pytest Documentation](https://docs.pytest.org/)
- [unittest.mock Guide](https://docs.python.org/3/library/unittest.mock.html)

**Related**:
- ADR-005: Serving strategy
- `docs/plan.md`: Production deployment

---

**Ready for Module 5?** → [`module5-fastapi-integration.md`](module5-fastapi-integration.md)

Learn how to expose VLMOrchestrator as a web API with FastAPI!
