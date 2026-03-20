"""
Module 5: FastAPI Integration

Purpose: Connect VLMOrchestrator to FastAPI web endpoints.
Learn how to build production API for screenshot analysis.

Prerequisites:
- Completed Module 1-4
- FastAPI installed (should be in pyproject.toml)
- VLMOrchestrator implemented

What you'll learn:
- Create FastAPI routes for screenshot upload
- Handle file uploads and temporary storage
- Async patterns for non-blocking I/O
- Error handling in web context
- OpenAPI documentation
"""

import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


def example_1_basic_route():
    """Example 1: Basic FastAPI route for screenshot analysis."""
    print("=" * 80)
    print("EXAMPLE 1: Basic FastAPI Route")
    print("=" * 80)
    print()

    print("Create a simple POST endpoint for screenshot upload:")
    print()

    code = '''
# src/stardew_vision/webapp/routes.py
from fastapi import APIRouter, UploadFile, HTTPException, File
from fastapi.responses import JSONResponse
import tempfile
from pathlib import Path

router = APIRouter()

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

    # Save to temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        # Analyze with orchestrator (imported at top of file)
        from stardew_vision.models.vlm_wrapper import VLMOrchestrator

        orchestrator = VLMOrchestrator(enable_mlflow=True)
        result = orchestrator.analyze_screenshot(tmp_path)

        return JSONResponse(content={
            "success": True,
            "filename": file.filename,
            "extraction": result
        })

    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))

    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        # Clean up temporary file
        Path(tmp_path).unlink(missing_ok=True)
    '''

    print(code)
    print()
    print("Key features:")
    print("  ✅ File upload handling")
    print("  ✅ Content type validation")
    print("  ✅ Temporary file management")
    print("  ✅ Proper HTTP status codes")
    print("  ✅ Cleanup (finally block)")
    print()


def example_2_fastapi_app():
    """Example 2: Complete FastAPI application."""
    print("=" * 80)
    print("EXAMPLE 2: Complete FastAPI Application")
    print("=" * 80)
    print()

    print("Wire up routes and create main FastAPI app:")
    print()

    code = '''
# src/stardew_vision/webapp/app.py
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
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS for browser access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly in production
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
        "docs": "/docs",
        "health": "/api/v1/health"
    }

@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint."""
    from stardew_vision.models.vlm_wrapper import VLMOrchestrator
    import requests

    health = {"status": "healthy", "checks": {}}

    # Check VLM endpoint
    try:
        response = requests.get("http://localhost:8001/v1/models", timeout=2)
        health["checks"]["vlm_endpoint"] = "up"
    except:
        health["checks"]["vlm_endpoint"] = "down"
        health["status"] = "degraded"

    # Check tools
    try:
        from stardew_vision.tools import TOOL_REGISTRY
        health["checks"]["tools_loaded"] = len(TOOL_REGISTRY)
    except:
        health["checks"]["tools_loaded"] = 0
        health["status"] = "degraded"

    return health
    '''

    print(code)
    print()
    print("Run the app:")
    print("  uvicorn stardew_vision.webapp.app:app --host 0.0.0.0 --port 8000 --reload")
    print()
    print("Access:")
    print("  - API root: http://localhost:8000/")
    print("  - Health check: http://localhost:8000/api/v1/health")
    print("  - Interactive docs: http://localhost:8000/docs")
    print("  - ReDoc: http://localhost:8000/redoc")
    print()


def example_3_singleton_orchestrator():
    """Example 3: Singleton pattern for orchestrator."""
    print("=" * 80)
    print("EXAMPLE 3: Singleton Orchestrator Pattern")
    print("=" * 80)
    print()

    print("Avoid creating new VLMOrchestrator on every request:")
    print()

    code = '''
# src/stardew_vision/webapp/routes.py
from fastapi import APIRouter, UploadFile, HTTPException, File
from stardew_vision.models.vlm_wrapper import VLMOrchestrator
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# Create orchestrator once (singleton)
# Reused across all requests
_orchestrator = None

def get_orchestrator() -> VLMOrchestrator:
    """Get or create singleton orchestrator."""
    global _orchestrator
    if _orchestrator is None:
        logger.info("Initializing VLMOrchestrator singleton")
        _orchestrator = VLMOrchestrator(enable_mlflow=True)
    return _orchestrator

@router.post("/analyze")
async def analyze_screenshot(file: UploadFile = File(...)):
    """Analyze screenshot using singleton orchestrator."""
    orchestrator = get_orchestrator()  # Reuses same instance

    # ... rest of implementation
    '''

    print(code)
    print()
    print("Benefits:")
    print("  ✅ Model loaded once (not per-request)")
    print("  ✅ Faster response times")
    print("  ✅ Lower memory usage")
    print()


def example_4_response_models():
    """Example 4: Response models with Pydantic."""
    print("=" * 80)
    print("EXAMPLE 4: Response Models")
    print("=" * 80)
    print()

    print("Define response schemas for OpenAPI documentation:")
    print()

    code = '''
# src/stardew_vision/webapp/models.py
from pydantic import BaseModel, Field
from typing import Optional

class ExtractionResult(BaseModel):
    """Extraction result for Pierre's shop panel."""
    name: str = Field(..., description="Item name")
    description: str = Field(..., description="Item description")
    price_per_unit: int = Field(..., description="Price per unit in gold")
    quantity_selected: int = Field(..., description="Quantity selected")
    total_cost: int = Field(..., description="Total cost in gold")

class AnalysisResponse(BaseModel):
    """Response from /analyze endpoint."""
    success: bool = Field(..., description="Whether analysis succeeded")
    filename: str = Field(..., description="Original filename")
    extraction: ExtractionResult = Field(..., description="Extracted data")
    audio_url: Optional[str] = Field(None, description="TTS audio URL (Phase 2)")

class ErrorResponse(BaseModel):
    """Error response."""
    success: bool = Field(False, description="Always false for errors")
    error: str = Field(..., description="Error message")
    error_type: str = Field(..., description="Error type (vlm, tool, validation)")

# Usage in routes.py
from stardew_vision.webapp.models import AnalysisResponse, ErrorResponse

@router.post("/analyze", response_model=AnalysisResponse, responses={
    400: {"model": ErrorResponse, "description": "Invalid file format"},
    500: {"model": ErrorResponse, "description": "Analysis failed"}
})
async def analyze_screenshot(file: UploadFile = File(...)) -> AnalysisResponse:
    # ... implementation
    pass
    '''

    print(code)
    print()
    print("Benefits:")
    print("  ✅ Automatic OpenAPI schema generation")
    print("  ✅ Response validation")
    print("  ✅ Clear API documentation")
    print("  ✅ Type safety")
    print()


def example_5_async_patterns():
    """Example 5: Async patterns for non-blocking I/O."""
    print("=" * 80)
    print("EXAMPLE 5: Async Patterns")
    print("=" * 80)
    print()

    print("Use async/await for non-blocking VLM calls:")
    print()

    code = '''
import asyncio
from typing import Dict, Any

async def analyze_screenshot_async(
    orchestrator: VLMOrchestrator,
    image_path: str
) -> Dict[str, Any]:
    """
    Async wrapper for VLM analysis.

    This allows the web server to handle other requests
    while waiting for VLM response.
    """
    # Run blocking VLM call in thread pool
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,  # Use default executor
        orchestrator.analyze_screenshot,
        image_path
    )
    return result

# Usage in route
@router.post("/analyze")
async def analyze_screenshot(file: UploadFile = File(...)):
    orchestrator = get_orchestrator()

    # Save file...
    tmp_path = save_temp_file(file)

    try:
        # Non-blocking VLM call
        result = await analyze_screenshot_async(orchestrator, tmp_path)
        return {"success": True, "extraction": result}

    finally:
        cleanup_temp_file(tmp_path)
    '''

    print(code)
    print()
    print("Benefits:")
    print("  ✅ Server doesn't block on VLM calls")
    print("  ✅ Can handle multiple concurrent requests")
    print("  ✅ Better throughput")
    print()
    print("Note: Smolagents CodeAgent is synchronous by default.")
    print("Wrapping in run_in_executor allows async usage.")
    print()


def example_6_testing_endpoints():
    """Example 6: Testing FastAPI endpoints."""
    print("=" * 80)
    print("EXAMPLE 6: Testing Endpoints")
    print("=" * 80)
    print()

    print("Test FastAPI routes with TestClient:")
    print()

    code = '''
# tests/test_api.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock
from stardew_vision.webapp.app import app
import io

client = TestClient(app)

@pytest.fixture
def mock_orchestrator():
    """Mock VLMOrchestrator for API tests."""
    with patch('stardew_vision.webapp.routes.get_orchestrator') as mock:
        orchestrator = Mock()
        orchestrator.analyze_screenshot.return_value = {
            "name": "Parsnip",
            "description": "A spring vegetable",
            "price_per_unit": 20,
            "quantity_selected": 5,
            "total_cost": 100
        }
        mock.return_value = orchestrator
        yield orchestrator

def test_root_endpoint():
    """Test root endpoint returns API info."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["name"] == "Stardew Vision API"

def test_health_check():
    """Test health check endpoint."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert "status" in response.json()

def test_analyze_screenshot_success(mock_orchestrator):
    """Test successful screenshot analysis."""
    # Create fake image file
    fake_image = io.BytesIO(b"fake image data")

    response = client.post(
        "/api/v1/analyze",
        files={"file": ("test.png", fake_image, "image/png")}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["extraction"]["name"] == "Parsnip"

def test_analyze_screenshot_invalid_file():
    """Test error on non-image file."""
    fake_file = io.BytesIO(b"not an image")

    response = client.post(
        "/api/v1/analyze",
        files={"file": ("test.txt", fake_file, "text/plain")}
    )

    assert response.status_code == 400
    assert "Invalid file type" in response.json()["detail"]

def test_analyze_screenshot_vlm_failure(mock_orchestrator):
    """Test error when VLM fails."""
    # Mock VLM failure
    mock_orchestrator.analyze_screenshot.side_effect = ValueError("VLM timeout")

    fake_image = io.BytesIO(b"fake image")

    response = client.post(
        "/api/v1/analyze",
        files={"file": ("test.png", fake_image, "image/png")}
    )

    assert response.status_code == 500

# Run tests
# pytest tests/test_api.py -v
    '''

    print(code)
    print()
    print("Testing strategy:")
    print("  ✅ Mock VLMOrchestrator (don't run actual VLM)")
    print("  ✅ Test all endpoints (root, health, analyze)")
    print("  ✅ Test error cases (invalid file, VLM failure)")
    print("  ✅ Use TestClient (no need to start server)")
    print()


def example_7_curl_examples():
    """Example 7: Testing with curl."""
    print("=" * 80)
    print("EXAMPLE 7: Testing with curl")
    print("=" * 80)
    print()

    print("Manual testing with curl commands:")
    print()

    commands = {
        "Health check": "curl http://localhost:8000/api/v1/health",

        "Upload screenshot": """curl -X POST http://localhost:8000/api/v1/analyze \\
  -F "file=@tests/fixtures/pierre_shop_001.png" \\
  | jq .""",

        "Pretty print JSON": """curl -X POST http://localhost:8000/api/v1/analyze \\
  -F "file=@tests/fixtures/pierre_shop_001.png" \\
  -s | jq .extraction""",

        "Save result to file": """curl -X POST http://localhost:8000/api/v1/analyze \\
  -F "file=@tests/fixtures/pierre_shop_001.png" \\
  -o result.json"""
    }

    for name, cmd in commands.items():
        print(f"{name}:")
        print(f"  {cmd}")
        print()

    print("Interactive docs (recommended):")
    print("  Open http://localhost:8000/docs in browser")
    print("  Click 'Try it out' on /analyze endpoint")
    print("  Upload file and execute")
    print()


def main():
    print("=" * 80)
    print("MODULE 5: FASTAPI INTEGRATION")
    print("=" * 80)
    print()
    print("Learning objectives:")
    print("  1. Create FastAPI routes for screenshot upload")
    print("  2. Handle file uploads and temporary storage")
    print("  3. Use async patterns for non-blocking I/O")
    print("  4. Define response models with Pydantic")
    print("  5. Write tests for API endpoints")
    print("  6. Use singleton pattern for orchestrator")
    print()

    # Example 1: Basic route
    example_1_basic_route()
    print()
    input("Press Enter to continue to Example 2...")
    print()

    # Example 2: FastAPI app
    example_2_fastapi_app()
    print()
    input("Press Enter to continue to Example 3...")
    print()

    # Example 3: Singleton pattern
    example_3_singleton_orchestrator()
    print()
    input("Press Enter to continue to Example 4...")
    print()

    # Example 4: Response models
    example_4_response_models()
    print()
    input("Press Enter to continue to Example 5...")
    print()

    # Example 5: Async patterns
    example_5_async_patterns()
    print()
    input("Press Enter to continue to Example 6...")
    print()

    # Example 6: Testing
    example_6_testing_endpoints()
    print()
    input("Press Enter to continue to Example 7...")
    print()

    # Example 7: curl examples
    example_7_curl_examples()

    # Summary
    print()
    print("=" * 80)
    print("✅ MODULE 5 COMPLETE!")
    print("=" * 80)
    print()
    print("You now understand:")
    print("  ✅ FastAPI route creation and file upload handling")
    print("  ✅ Singleton pattern for orchestrator (performance)")
    print("  ✅ Response models and OpenAPI documentation")
    print("  ✅ Async patterns for non-blocking I/O")
    print("  ✅ Testing FastAPI endpoints with TestClient")
    print("  ✅ Manual testing with curl and interactive docs")
    print()
    print("Key insights:")
    print("  - FastAPI provides automatic OpenAPI docs")
    print("  - Singleton orchestrator avoids model reloading")
    print("  - Async/await allows concurrent request handling")
    print("  - TestClient enables testing without server")
    print("  - Always clean up temporary files (finally block)")
    print()
    print("Next steps:")
    print("  1. Implement routes in src/stardew_vision/webapp/")
    print("  2. Write API tests in tests/test_api.py")
    print("  3. Start webapp: uvicorn stardew_vision.webapp.app:app --port 8000")
    print("  4. Test with curl or browser at http://localhost:8000/docs")
    print("  5. Move to Module 6 for conference demo materials")
    print()


if __name__ == "__main__":
    main()
