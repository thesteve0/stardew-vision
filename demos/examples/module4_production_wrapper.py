"""
Module 4: Production VLM Wrapper

Purpose: Create production-ready VLMOrchestrator class with:
- Error handling (VLM failures, tool errors, validation errors)
- MLFlow logging and observability
- Unit testing with mocks
- Schema validation

This is the actual production code that will be used in Stardew Vision.

Prerequisites:
- Completed Module 1-3
- MLFlow installed (should be in pyproject.toml)
- pytest for testing

What you'll learn:
- Production error handling patterns
- MLFlow integration for observability
- Unit testing with mocked VLM
- JSON schema validation with Pydantic
"""

import json
import sys
import logging
from pathlib import Path
from typing import Dict, Any, Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def example_1_orchestrator_class():
    """Example 1: Production VLMOrchestrator class."""
    print("=" * 80)
    print("EXAMPLE 1: VLMOrchestrator Class")
    print("=" * 80)
    print()

    print("This is the production wrapper that will go in:")
    print("  src/stardew_vision/models/vlm_wrapper.py")
    print()

    # Show the class structure
    code = '''
from smolagents import CodeAgent, Tool, LiteLLMModel
import mlflow
import logging
from typing import Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)

class PierresPanelTool(Tool):
    """Smolagents tool wrapper for Pierre's shop extraction."""
    name = "crop_pierres_detail_panel"
    description = "Extract item details from Pierre's General Store detail panel"
    inputs = {"image_path": {"type": "string", "description": "Path to screenshot"}}
    output_type = "dict"

    def forward(self, image_path: str):
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
    """Production VLM orchestrator using Smolagents."""

    def __init__(
        self,
        model_id: str = "Qwen2.5-VL-7B-Instruct",
        use_vllm: bool = True,
        vllm_endpoint: str = "http://localhost:8001/v1",
        enable_mlflow: bool = True
    ):
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
            from smolagents import InferenceClientModel
            logger.info(f"Using transformers: {model_id}")
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

        logger.info("VLMOrchestrator initialized")

    def analyze_screenshot(self, image_path: str) -> Dict[str, Any]:
        """
        Classify screenshot and extract fields.

        Args:
            image_path: Path to screenshot

        Returns:
            Extracted fields as dict

        Raises:
            FileNotFoundError: Image not found
            ValueError: VLM analysis failed
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

        try:
            # Run agent
            result = self.agent.run(
                f"Extract all item information from the Pierre's General Store "
                f"screenshot at {image_path}. Use the crop_pierres_detail_panel "
                f"tool and return the complete result."
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
    '''

    print(code)
    print()
    print("Key features:")
    print("  ✅ Error handling (FileNotFoundError, ValueError)")
    print("  ✅ MLFlow logging (params, metrics, artifacts)")
    print("  ✅ Flexible backend (vLLM or transformers)")
    print("  ✅ Structured logging")
    print("  ✅ Path validation")
    print()


def example_2_schema_validation():
    """Example 2: Schema validation with Pydantic."""
    print("=" * 80)
    print("EXAMPLE 2: Schema Validation")
    print("=" * 80)
    print()

    print("Validate extraction results against expected schema:")
    print()

    code = '''
from pydantic import BaseModel, Field, ValidationError

class PierreShopResult(BaseModel):
    """Expected schema for Pierre's shop extraction."""
    name: str = Field(..., min_length=1, description="Item name")
    description: str = Field(..., min_length=1, description="Item description")
    price_per_unit: int = Field(..., gt=0, description="Price per unit in gold")
    quantity_selected: int = Field(..., gt=0, description="Quantity selected")
    total_cost: int = Field(..., gt=0, description="Total cost in gold")

    def verify_total(self) -> bool:
        """Verify total_cost matches price * quantity."""
        expected = self.price_per_unit * self.quantity_selected
        return self.total_cost == expected

def validate_extraction(result: dict) -> PierreShopResult:
    """
    Validate extraction result against schema.

    Args:
        result: Raw extraction dict from VLM

    Returns:
        Validated PierreShopResult

    Raises:
        ValidationError: If result doesn't match schema
    """
    try:
        validated = PierreShopResult(**result)

        # Additional validation
        if not validated.verify_total():
            logger.warning(
                f"Total cost mismatch: {validated.total_cost} != "
                f"{validated.price_per_unit} * {validated.quantity_selected}"
            )

        return validated

    except ValidationError as e:
        logger.error(f"Validation failed: {e}")
        raise ValueError(f"Invalid extraction result: {e}")

# Usage
result = orchestrator.analyze_screenshot(image_path)
validated = validate_extraction(result)  # Raises if invalid
    '''

    print(code)
    print()
    print("Benefits:")
    print("  ✅ Type safety (catches bad data early)")
    print("  ✅ Automatic validation (min_length, gt=0)")
    print("  ✅ Custom validators (verify_total)")
    print("  ✅ Clear error messages")
    print()


def example_3_error_handling():
    """Example 3: Comprehensive error handling."""
    print("=" * 80)
    print("EXAMPLE 3: Error Handling Strategy")
    print("=" * 80)
    print()

    print("Distinguish error types for proper handling:")
    print()

    code = '''
class VLMError(Exception):
    """VLM-specific error (may retry)."""
    pass

class ToolError(Exception):
    """Tool execution error (fail fast)."""
    pass

class ValidationError(Exception):
    """Validation error (bad data)."""
    pass

def analyze_with_retry(
    image_path: str,
    max_retries: int = 3,
    backoff: float = 1.0
) -> Dict[str, Any]:
    """
    Analyze with automatic retry on transient failures.

    Args:
        image_path: Path to screenshot
        max_retries: Max retry attempts
        backoff: Backoff multiplier (seconds)

    Returns:
        Extraction result

    Raises:
        ToolError: Tool failed (non-retryable)
        ValidationError: Bad extraction (non-retryable)
        VLMError: VLM failed after all retries
    """
    import time

    for attempt in range(max_retries):
        try:
            result = orchestrator.analyze_screenshot(image_path)

            # Validate result
            validated = validate_extraction(result)

            logger.info(f"Success on attempt {attempt + 1}")
            return validated.dict()

        except FileNotFoundError as e:
            # Not retryable
            raise ToolError(f"Image not found: {e}")

        except ValidationError as e:
            # Bad extraction - not retryable
            logger.error(f"Validation failed: {e}")
            raise

        except Exception as e:
            # VLM timeout/overload - retryable
            if attempt < max_retries - 1:
                wait = backoff * (2 ** attempt)
                logger.warning(f"VLM error (attempt {attempt + 1}), retrying in {wait}s: {e}")
                time.sleep(wait)
            else:
                logger.error(f"VLM failed after {max_retries} attempts")
                raise VLMError(f"VLM failed: {e}")

# Usage
try:
    result = analyze_with_retry(image_path)
except VLMError:
    # Log and return error response
    pass
except ToolError:
    # Log critical error, investigate
    pass
except ValidationError:
    # Log bad extraction, might be wrong screen type
    pass
    '''

    print(code)
    print()
    print("Error handling strategy:")
    print("  🔄 VLMError: Retry with exponential backoff")
    print("  ❌ ToolError: Fail fast, don't retry")
    print("  ❌ ValidationError: Fail fast, log for review")
    print()


def example_4_unit_testing():
    """Example 4: Unit testing with mocks."""
    print("=" * 80)
    print("EXAMPLE 4: Unit Testing")
    print("=" * 80)
    print()

    print("Test production code without running actual VLM:")
    print()

    code = '''
# tests/test_vlm_wrapper.py
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
    image_path.write_bytes(b"fake image data")

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
    with pytest.raises(FileNotFoundError, match="Image not found"):
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
    assert "name" in result
    assert "price_per_unit" in result
    '''

    print(code)
    print()
    print("Testing strategy:")
    print("  ✅ Unit tests: Mock VLM (fast, no dependencies)")
    print("  ✅ Integration tests: Real vLLM (slower, marked @pytest.mark.integration)")
    print("  ✅ Fixtures: Reusable test setup")
    print("  ✅ Coverage: All error paths tested")
    print()
    print("Run tests:")
    print("  # Unit tests only (fast)")
    print("  pytest tests/test_vlm_wrapper.py -v")
    print()
    print("  # Integration tests (requires vLLM)")
    print("  pytest tests/test_vlm_wrapper.py -v -m integration")
    print()


def example_5_mlflow_observability():
    """Example 5: MLFlow observability patterns."""
    print("=" * 80)
    print("EXAMPLE 5: MLFlow Observability")
    print("=" * 80)
    print()

    print("Track all tool calls for debugging and optimization:")
    print()

    code = '''
import mlflow
import time

def analyze_with_observability(image_path: str) -> Dict[str, Any]:
    """Analyze with comprehensive MLFlow tracking."""

    with mlflow.start_run(run_name=f"extraction_{Path(image_path).stem}"):
        # Log inputs
        mlflow.log_param("image_path", image_path)
        mlflow.log_param("model_id", orchestrator.model_id)
        mlflow.log_param("use_vllm", orchestrator.use_vllm)

        # Track latency
        start_time = time.time()

        try:
            # Run extraction
            result = orchestrator.analyze_screenshot(image_path)

            # Log success metrics
            latency = time.time() - start_time
            mlflow.log_metric("latency_ms", latency * 1000)
            mlflow.log_metric("success", 1)

            # Log result
            mlflow.log_dict(result, "extraction_result.json")

            # Log quality metrics
            mlflow.log_metric("field_count", len(result))
            mlflow.log_metric("has_name", int("name" in result))
            mlflow.log_metric("has_price", int("price_per_unit" in result))

            # Validate and log validation status
            try:
                validated = validate_extraction(result)
                mlflow.log_metric("validation_passed", 1)
                mlflow.log_metric("total_verified", int(validated.verify_total()))
            except ValidationError:
                mlflow.log_metric("validation_passed", 0)

            return result

        except Exception as e:
            # Log failure
            latency = time.time() - start_time
            mlflow.log_metric("latency_ms", latency * 1000)
            mlflow.log_metric("success", 0)
            mlflow.log_param("error_type", type(e).__name__)
            mlflow.log_param("error_message", str(e))

            raise

# View results in MLFlow UI
# mlflow ui --port 5000
# Open http://localhost:5000
    '''

    print(code)
    print()
    print("Metrics tracked:")
    print("  📊 Latency (ms)")
    print("  📊 Success/failure rate")
    print("  📊 Validation pass rate")
    print("  📊 Field completeness")
    print("  📊 Error types")
    print()
    print("Benefits:")
    print("  ✅ Identify slow extractions")
    print("  ✅ Track VLM reliability")
    print("  ✅ Debug validation failures")
    print("  ✅ Compare model versions")
    print()


def main():
    print("=" * 80)
    print("MODULE 4: PRODUCTION VLM WRAPPER")
    print("=" * 80)
    print()
    print("Learning objectives:")
    print("  1. Create production VLMOrchestrator class")
    print("  2. Implement schema validation with Pydantic")
    print("  3. Add comprehensive error handling")
    print("  4. Write unit tests with mocking")
    print("  5. Integrate MLFlow observability")
    print()

    # Example 1: Orchestrator class
    example_1_orchestrator_class()
    print()
    input("Press Enter to continue to Example 2...")
    print()

    # Example 2: Schema validation
    example_2_schema_validation()
    print()
    input("Press Enter to continue to Example 3...")
    print()

    # Example 3: Error handling
    example_3_error_handling()
    print()
    input("Press Enter to continue to Example 4...")
    print()

    # Example 4: Unit testing
    example_4_unit_testing()
    print()
    input("Press Enter to continue to Example 5...")
    print()

    # Example 5: MLFlow observability
    example_5_mlflow_observability()

    # Summary
    print()
    print("=" * 80)
    print("✅ MODULE 4 COMPLETE!")
    print("=" * 80)
    print()
    print("You now understand:")
    print("  ✅ Production-ready VLMOrchestrator pattern")
    print("  ✅ Schema validation with Pydantic")
    print("  ✅ Error handling (VLM vs Tool vs Validation)")
    print("  ✅ Unit testing with mocked VLM")
    print("  ✅ MLFlow observability and metrics")
    print()
    print("Key insights:")
    print("  - Production code needs robust error handling")
    print("  - Validation prevents bad data from propagating")
    print("  - Unit tests with mocks are fast and reliable")
    print("  - MLFlow provides essential observability")
    print("  - Distinguish retryable vs non-retryable errors")
    print()
    print("Next steps:")
    print("  1. Implement VLMOrchestrator in src/stardew_vision/models/vlm_wrapper.py")
    print("  2. Write tests in tests/test_vlm_wrapper.py")
    print("  3. Run pytest to verify all tests pass")
    print("  4. Move to Module 5 for FastAPI integration")
    print()


if __name__ == "__main__":
    main()
