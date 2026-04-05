# Module 5: FastAPI Integration

**Duration**: 1-2 hours
**Prerequisites**: Module 4 completed, FastAPI basics
**Example Code**: [`examples/module5_fastapi_integration.py`](../examples/module5_fastapi_integration.py)

---

## Learning Objectives

By the end of this module, you will:

- ✅ Create FastAPI routes for screenshot upload
- ✅ Handle file uploads and temporary storage
- ✅ Connect VLMOrchestrator to web endpoints
- ✅ Implement health checks and error responses
- ✅ Test with curl and interactive docs

---

## Why FastAPI?

In Module 4, you have a working `VLMOrchestrator` class:

```python
orchestrator = VLMOrchestrator()
result = orchestrator.analyze_screenshot("/path/to/image.png")
```

**But users can't use this directly!**

They need:
- ✅ Web interface to upload screenshots
- ✅ HTTP API for programmatic access
- ✅ No local file system access required

**FastAPI solves this** by providing a production-ready web framework.

### Why FastAPI vs Flask/Django?

**FastAPI advantages**:
- ✅ **Async support**: Non-blocking I/O (VLM calls don't block other requests)
- ✅ **Automatic docs**: Interactive API at `/docs` (OpenAPI/Swagger)
- ✅ **Type validation**: Pydantic models (request/response validation)
- ✅ **Performance**: Comparable to Node.js and Go
- ✅ **Modern Python**: async/await, type hints

**FastAPI is ideal for ML APIs**:
- Used by HuggingFace, Gradio, many ML startups
- Handles file uploads gracefully
- Built-in request validation
- Auto-generated API docs

---

## Architecture: Web Request Flow

```
USER                    FASTAPI APP              VLMORCHESTRATOR
┌──────┐               ┌─────────────┐           ┌──────────────┐
│      │               │             │           │              │
│Upload│  POST /analyze│  FastAPI    │  analyze_ │  Smolagents  │
│ PNG  │──────────────>│  Route      │──────────>│  CodeAgent   │
│      │               │             │  screenshot│              │
│      │               │  1. Validate│           │              │
│      │               │  2. Save to │           │  VLM call    │
│      │               │     temp    │           │  Tool exec   │
│      │               │  3. Call    │           │              │
│      │               │     orch    │<──────────│  Return dict │
│      │               │  4. Cleanup │  result   │              │
│      │               │  5. Return  │           │              │
│      │<──────────────│     JSON    │           │              │
│      │  HTTP 200     │             │           │              │
│      │  {"success":  │             │           │              │
│      │   true, ...}  │             │           │              │
└──────┘               └─────────────┘           └──────────────┘


ERROR HANDLING:

┌──────┐               ┌─────────────┐           ┌──────────────┐
│Upload│               │             │           │              │
│ TXT  │  POST /analyze│  FastAPI    │           │              │
│ file │──────────────>│  Route      │           │              │
│      │               │             │           │              │
│      │               │  Validate   │           │              │
│      │               │  content    │           │              │
│      │               │  type       │           │              │
│      │               │             │           │              │
│      │<──────────────│  ❌         │           │              │
│      │  HTTP 400     │             │           │              │
│      │  {"detail":   │             │           │              │
│      │   "Invalid    │             │           │              │
│      │   file type"} │             │           │              │
└──────┘               └─────────────┘           └──────────────┘
```

---

## Code Walkthrough: FastAPI Routes

### Part 1: Imports and App Creation (Lines 1-20)

```python
"""
FastAPI routes for Stardew Vision.
Handles screenshot uploads and returns audio narration.
"""
from fastapi import FastAPI, UploadFile, HTTPException, File
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from stardew_vision.models.vlm_wrapper import VLMOrchestrator
import tempfile
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Stardew Vision API",
    description="Extract UI panel contents from Stardew Valley screenshots",
    version="0.1.0"
)
```

**FastAPI app configuration**:
- `title`: Shown in docs
- `description`: API description
- `version`: API version (for clients)

These appear in the auto-generated docs at `/docs`.

### Part 2: CORS Middleware (Lines 22-28)

```python
# CORS for browser access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # Allow all origins
    allow_methods=["*"],          # Allow all HTTP methods
    allow_headers=["*"],          # Allow all headers
)
```

**Why CORS?**

Without CORS, browser requests fail:
```javascript
// Frontend (running on http://localhost:3000)
fetch('http://localhost:8000/api/v1/analyze', {
  method: 'POST',
  body: formData
})
// ❌ CORS error: Origin not allowed
```

With CORS middleware:
```javascript
// Same request
// ✅ Works!
```

**Production note**: Replace `allow_origins=["*"]` with specific domains:
```python
allow_origins=["https://stardew-vision.com"]
```

### Part 3: Initialize Orchestrator (Lines 30-32)

```python
# Initialize orchestrator (singleton)
orchestrator = VLMOrchestrator(enable_mlflow=True)
```

**Why singleton?**

**Bad** (create orchestrator per request):
```python
@app.post("/analyze")
async def analyze(file: UploadFile):
    orch = VLMOrchestrator()  # Slow! Loads model every request
    result = orch.analyze_screenshot(...)
```

**Good** (create once, reuse):
```python
# At module level (runs once on startup)
orchestrator = VLMOrchestrator()

@app.post("/analyze")
async def analyze(file: UploadFile):
    result = orchestrator.analyze_screenshot(...)  # Fast!
```

**Performance impact**:
- Bad: 10-30 seconds per request (model load time)
- Good: 1-2 seconds per request (inference only)

### Part 4: Upload Endpoint (Lines 34-90)

```python
@app.post("/api/v1/analyze")
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
```

**Line-by-line breakdown**:

**Lines 35-37: Route definition**
```python
@app.post("/api/v1/analyze")
async def analyze_screenshot(file: UploadFile = File(...)):
```

- `@app.post(...)`: HTTP POST endpoint
- `/api/v1/analyze`: URL path (versioned API)
- `async def`: Async function (non-blocking)
- `file: UploadFile`: FastAPI file upload handling
- `File(...)`: Required parameter (no default)

**Lines 50-54: File type validation**
```python
if not file.content_type.startswith("image/"):
    raise HTTPException(
        status_code=400,
        detail=f"Invalid file type: {file.content_type}. Must be image."
    )
```

**Why validate?**
- Reject text files, PDFs, etc.
- Prevent wasting VLM time
- Clear error message to user

**Content types**:
- `image/png` ✅
- `image/jpeg` ✅
- `image/jpg` ✅
- `text/plain` ❌
- `application/pdf` ❌

**Lines 58-61: Save to temporary file**
```python
with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
    content = await file.read()  # Read uploaded bytes
    tmp.write(content)           # Write to disk
    tmp_path = tmp.name          # Get file path
```

**Why temporary file?**
- VLMOrchestrator expects file path (not bytes)
- Tools (OpenCV, PaddleOCR) read from disk
- Temporary: automatically cleaned up

**`delete=False`**: We delete it ourselves in `finally` block (more control)

**Lines 63-78: Call orchestrator**
```python
try:
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
```

**Error handling pattern**:
1. Try to analyze
2. If succeeds: Return JSON with extraction
3. If fails: Log error, return HTTP error

**HTTP status codes**:
- `200 OK`: Success
- `400 Bad Request`: Invalid input (wrong file type)
- `500 Internal Server Error`: VLM failure

**Lines 80-82: Cleanup**
```python
finally:
    Path(tmp_path).unlink(missing_ok=True)
```

**Why finally?**
- Runs even if exception raised
- Prevents disk space leak
- `missing_ok=True`: Don't error if already deleted

### Part 5: Health Check (Lines 92-96)

```python
@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "model": orchestrator.model_id
    }
```

**Why health checks?**

Load balancers and orchestrators (Kubernetes, OpenShift) need to know if your app is alive:

```bash
# Kubernetes liveness probe
curl http://app:8000/api/v1/health
# Expected: {"status": "healthy", ...}
# If fails: Restart pod
```

**What to include**:
- `status`: "healthy" or "unhealthy"
- Model info (which model loaded)
- Optional: Check vLLM connectivity

**Advanced health check**:
```python
@app.get("/api/v1/health")
async def health_check():
    try:
        # Check vLLM is responding
        requests.get("http://localhost:8001/health", timeout=2)
        return {"status": "healthy", "vllm": "connected"}
    except:
        return {"status": "unhealthy", "vllm": "disconnected"}
```

### Part 6: Root Endpoint (Lines 98-105)

```python
@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": "Stardew Vision API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/api/v1/health",
        "analyze": "/api/v1/analyze"
    }
```

**Why a root endpoint?**

Users visiting `http://localhost:8000/` see useful info instead of 404.

**Response**:
```json
{
  "name": "Stardew Vision API",
  "version": "0.1.0",
  "docs": "/docs",
  "health": "/api/v1/health",
  "analyze": "/api/v1/analyze"
}
```

Guides users to docs and endpoints.

---

## Running the Web App

### Terminal 1: Start vLLM

```bash
vllm serve /workspaces/stardew-vision/models/base/Qwen2.5-VL-7B-Instruct \
  --port 8001 \
  --dtype float16 \
  --enable-tool-calling
```

### Terminal 2: Start FastAPI

```bash
cd /workspaces/stardew-vision

uvicorn stardew_vision.webapp.app:app \
  --host 0.0.0.0 \
  --port 8000 \
  --reload
```

**Parameters**:
- `stardew_vision.webapp.app:app`: Module path to FastAPI app
- `--host 0.0.0.0`: Listen on all interfaces (allows external access)
- `--port 8000`: HTTP port
- `--reload`: Auto-reload on code changes (development only)

**Expected output**:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [12345]
INFO:     Started server process [12346]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

---

## Hands-On Activity

### Checkpoint 1: Test with curl

**Terminal 3**: Test health check
```bash
curl http://localhost:8000/api/v1/health
```

**Expected**:
```json
{
  "status": "healthy",
  "model": "Qwen2.5-VL-7B-Instruct"
}
```

**Upload screenshot**:
```bash
curl -X POST http://localhost:8000/api/v1/analyze \
  -F "file=@/workspaces/stardew-vision/tests/fixtures/pierre_shop_001.png" \
  | jq
```

**Expected** (JSON formatted with jq):
```json
{
  "success": true,
  "filename": "pierre_shop_001.png",
  "extraction": {
    "name": "Parsnip",
    "description": "A spring vegetable. Still loved by many.",
    "price_per_unit": 20,
    "quantity_selected": 5,
    "total_cost": 100
  }
}
```

**Test error: Upload text file**:
```bash
echo "not an image" > /tmp/test.txt
curl -X POST http://localhost:8000/api/v1/analyze \
  -F "file=@/tmp/test.txt"
```

**Expected**:
```json
{
  "detail": "Invalid file type: text/plain. Must be image."
}
```

### Checkpoint 2: Test with Interactive Docs

**Open browser**: http://localhost:8000/docs

You'll see **Swagger UI** with:
- List of endpoints
- Try-it-out functionality
- Request/response examples

**To test upload**:
1. Click `/api/v1/analyze` endpoint
2. Click "Try it out"
3. Click "Choose File"
4. Select screenshot
5. Click "Execute"
6. See response below

**Screenshot of Swagger UI** (conceptual):
```
POST /api/v1/analyze
Analyze a Stardew Valley screenshot and extract panel contents

Parameters:
  file* (file): Screenshot file

Responses:
  200: Successful Response
  {
    "success": true,
    "filename": "screenshot.png",
    "extraction": {...}
  }

  400: Bad Request (invalid file type)
  500: Internal Server Error (VLM failed)
```

### Checkpoint 3: Test with Python Client

Create `test_client.py`:

```python
import requests

# Upload screenshot
with open("/workspaces/stardew-vision/tests/fixtures/pierre_shop_001.png", "rb") as f:
    files = {"file": f}
    response = requests.post("http://localhost:8000/api/v1/analyze", files=files)

# Check response
if response.status_code == 200:
    result = response.json()
    print("✅ Success!")
    print(f"Item: {result['extraction']['name']}")
    print(f"Price: {result['extraction']['price_per_unit']}")
else:
    print(f"❌ Error: {response.status_code}")
    print(response.json())
```

**Run**:
```bash
python test_client.py
```

**Expected**:
```
✅ Success!
Item: Parsnip
Price: 20
```

---

## Async Patterns

### Why Async?

**Synchronous (blocking)**:
```python
@app.post("/analyze")
def analyze(file: UploadFile):  # Not async!
    result = orchestrator.analyze_screenshot(...)  # Blocks for 2 seconds
    return result

# If 10 requests arrive:
# Request 1: 0-2s
# Request 2: 2-4s (waits for request 1!)
# Request 3: 4-6s (waits for request 1 and 2!)
# ...
# Request 10: 18-20s
# Total: 20 seconds
```

**Asynchronous (non-blocking)**:
```python
@app.post("/analyze")
async def analyze(file: UploadFile):  # Async!
    result = await run_in_threadpool(orchestrator.analyze_screenshot, ...)
    return result

# If 10 requests arrive:
# All start immediately
# All complete in ~2 seconds (parallel execution)
# Total: 2 seconds
```

**Performance gain**: 10x throughput

### Making VLMOrchestrator Async

**Option 1: Thread pool** (current):
```python
from fastapi.concurrency import run_in_threadpool

@app.post("/api/v1/analyze")
async def analyze_screenshot(file: UploadFile = File(...)):
    # ...save file...

    # Run in thread pool (doesn't block event loop)
    result = await run_in_threadpool(
        orchestrator.analyze_screenshot,
        tmp_path
    )

    return JSONResponse(content={"success": True, "extraction": result})
```

**Option 2: Async orchestrator** (future improvement):
```python
class VLMOrchestrator:
    async def analyze_screenshot(self, image_path: str) -> Dict[str, Any]:
        # Use async HTTP client for vLLM
        async with httpx.AsyncClient() as client:
            response = await client.post(...)
        # ...
```

**For now**, Module 5 example uses thread pool (simpler, good enough).

---

## Testing the API

### Unit Tests for Routes

```python
from fastapi.testclient import TestClient
from stardew_vision.webapp.app import app

client = TestClient(app)

def test_health_check():
    """Test health endpoint."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_analyze_success(tmp_path):
    """Test successful upload."""
    # Create dummy image
    image_path = tmp_path / "test.png"
    image_path.write_bytes(b"PNG fake data")

    # Upload
    with open(image_path, "rb") as f:
        response = client.post(
            "/api/v1/analyze",
            files={"file": ("test.png", f, "image/png")}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "extraction" in data

def test_analyze_invalid_file_type():
    """Test rejection of non-image files."""
    response = client.post(
        "/api/v1/analyze",
        files={"file": ("test.txt", b"not an image", "text/plain")}
    )

    assert response.status_code == 400
    assert "Invalid file type" in response.json()["detail"]
```

**Run tests**:
```bash
pytest tests/test_api.py -v
```

---

## Key Patterns

### Pattern 1: Temporary File Handling

```python
with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
    content = await file.read()
    tmp.write(content)
    tmp_path = tmp.name

try:
    result = process_file(tmp_path)
    return result
finally:
    Path(tmp_path).unlink(missing_ok=True)  # Always cleanup
```

### Pattern 2: HTTP Error Responses

```python
# Input validation error (400)
if not valid:
    raise HTTPException(status_code=400, detail="Clear error message")

# Processing error (500)
try:
    result = process()
except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))
```

### Pattern 3: Singleton Services

```python
# At module level (runs once)
orchestrator = VLMOrchestrator()

# In route handlers (reuses instance)
@app.post("/analyze")
async def analyze(...):
    result = orchestrator.analyze_screenshot(...)
```

---

## Common Pitfalls

### Pitfall 1: Forgetting to Clean Up Temp Files

**Wrong**:
```python
tmp = tempfile.NamedTemporaryFile(delete=False)
tmp.write(content)
result = process(tmp.name)
# File never deleted! Disk fills up over time
```

**Right**:
```python
tmp = tempfile.NamedTemporaryFile(delete=False)
try:
    tmp.write(content)
    result = process(tmp.name)
finally:
    Path(tmp.name).unlink(missing_ok=True)
```

### Pitfall 2: Creating Orchestrator Per Request

**Wrong** (slow):
```python
@app.post("/analyze")
async def analyze(...):
    orch = VLMOrchestrator()  # 10-30 seconds!
    result = orch.analyze_screenshot(...)
```

**Right** (fast):
```python
# Module level
orchestrator = VLMOrchestrator()

@app.post("/analyze")
async def analyze(...):
    result = orchestrator.analyze_screenshot(...)  # 1-2 seconds
```

### Pitfall 3: Not Validating File Types

**Wrong**:
```python
@app.post("/analyze")
async def analyze(file: UploadFile):
    # No validation! User could upload anything
    result = orchestrator.analyze_screenshot(file)
```

**Right**:
```python
if not file.content_type.startswith("image/"):
    raise HTTPException(status_code=400, detail="Must be image")
```

---

## Key Takeaways

### 1. FastAPI Provides Production Web Layer

Module 4: VLMOrchestrator class (business logic)
Module 5: FastAPI routes (web interface)

**Separation of concerns** - logic separate from web framework.

### 2. File Upload Pattern

1. Validate content type
2. Save to temporary file
3. Process file
4. Clean up temporary file
5. Return result

### 3. Interactive Docs Are Free

Just add docstrings to routes:
```python
@app.post("/analyze")
async def analyze(file: UploadFile):
    """
    Analyze a Stardew Valley screenshot and extract panel contents.
    """
```

FastAPI generates Swagger UI automatically at `/docs`.

### 4. Async Enables Concurrency

Without `async`: Sequential processing (slow)
With `async`: Concurrent processing (fast)

### 5. Health Checks Enable Monitoring

Load balancers and orchestrators rely on health endpoints:
```bash
curl /health
# {"status": "healthy"} → Keep running
# Error or {"status": "unhealthy"} → Restart
```

---

## Summary

You now understand:

1. ✅ **FastAPI routes** - Define endpoints with decorators
2. ✅ **File upload handling** - Temporary files, cleanup
3. ✅ **Error responses** - HTTP status codes, clear messages
4. ✅ **Health checks** - Monitoring and orchestration
5. ✅ **Interactive docs** - Auto-generated Swagger UI
6. ✅ **Async patterns** - Non-blocking I/O

**The complete stack**:
- Module 1: Manual dispatch (fundamentals)
- Module 2: Smolagents (automation)
- Module 3: vLLM (production speed)
- Module 4: VLMOrchestrator (error handling, observability)
- Module 5: FastAPI (web interface) ⬅ You are here
- Module 6: Advanced topics (decision framework, demos)

---

## Next Steps

**Current state**:
- ✅ Web API for screenshot upload
- ✅ Async request handling
- ✅ Interactive docs
- ✅ Error handling

**Module 6 covers**:
- When to use raw client vs Smolagents
- When to add LangGraph (Phase 2+)
- Conference demo scripts
- Hub tool sharing

---

## Additional Resources

**Code**:
- Full example: [`examples/module5_fastapi_integration.py`](../examples/module5_fastapi_integration.py)
- Tests: `tests/test_api.py`

**Diagrams**:
- [`diagrams/fastapi-integration.txt`](../diagrams/fastapi-integration.txt) - Request flow

**Documentation**:
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [FastAPI File Uploads](https://fastapi.tiangolo.com/tutorial/request-files/)
- [Uvicorn Documentation](https://www.uvicorn.org/)

---

**Ready for Module 6?** → [`module6-conference-demos.md`](module6-conference-demos.md)

Learn advanced patterns and prepare conference demos!
