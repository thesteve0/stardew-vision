# 2026 Agentic Workflow Best Practices

Based on March 2026 research and production deployments.

## Core Principles

### 1. Observability First

**Log every tool call**:
```python
import mlflow
import logging

logger = logging.getLogger(__name__)

def tool_call_wrapper(tool_name: str, arguments: dict):
    """Wrap tool calls with logging."""
    with mlflow.start_run(nested=True):
        # Log inputs
        mlflow.log_param("tool_name", tool_name)
        mlflow.log_dict(arguments, "arguments.json")

        start_time = time.time()

        try:
            # Execute tool
            result = TOOL_REGISTRY[tool_name](**arguments)

            # Log success
            latency = time.time() - start_time
            mlflow.log_metric("latency_ms", latency * 1000)
            mlflow.log_metric("success", 1)
            mlflow.log_dict(result, "result.json")

            logger.info(f"Tool {tool_name} succeeded in {latency:.2f}s")
            return result

        except Exception as e:
            # Log failure
            latency = time.time() - start_time
            mlflow.log_metric("latency_ms", latency * 1000)
            mlflow.log_metric("success", 0)
            mlflow.log_param("error", str(e))

            logger.error(f"Tool {tool_name} failed: {e}")
            raise
```

**Track metrics**:
- Latency per tool
- Success/failure rates
- VLM token usage
- Error types (VLM vs tool vs validation)

### 2. Structured Outputs

**Enforce JSON schemas**:
```python
from pydantic import BaseModel, ValidationError

class PierreShopResult(BaseModel):
    """Schema for Pierre's shop extraction."""
    name: str
    description: str
    price_per_unit: int
    quantity_selected: int
    total_cost: int

def validate_extraction(result: dict) -> PierreShopResult:
    """Validate extraction result against schema."""
    try:
        return PierreShopResult(**result)
    except ValidationError as e:
        logger.error(f"Validation failed: {e}")
        raise ValueError(f"Invalid extraction result: {e}")
```

**Use response_format** (OpenAI API):
```python
response = client.chat.completions.create(
    model="Qwen2.5-VL-7B-Instruct",
    messages=[...],
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "pierre_shop_extraction",
            "schema": PierreShopResult.model_json_schema()
        }
    }
)
```

### 3. Verification-Aware Planning

**Add pass-fail checks**:
```python
def verify_extraction(result: dict) -> bool:
    """Verify extraction quality."""
    checks = [
        ("name_present", result.get("name") is not None),
        ("name_not_empty", bool(result.get("name", "").strip())),
        ("price_positive", result.get("price_per_unit", 0) > 0),
        ("quantity_positive", result.get("quantity_selected", 0) > 0),
        ("total_matches", result.get("total_cost") == result.get("price_per_unit", 0) * result.get("quantity_selected", 0))
    ]

    for check_name, passed in checks:
        mlflow.log_metric(f"check_{check_name}", int(passed))

    return all(passed for _, passed in checks)
```

**Retry with feedback**:
```python
def extract_with_retry(image_path: str, max_retries: int = 3):
    """Extract with automatic retry on verification failure."""
    for attempt in range(max_retries):
        result = orchestrator.analyze_screenshot(image_path)

        if verify_extraction(result):
            logger.info(f"Extraction verified on attempt {attempt + 1}")
            return result

        logger.warning(f"Verification failed on attempt {attempt + 1}")

    raise ValueError("Extraction failed all verification attempts")
```

### 4. Parallel Function Calling

**Batch independent tool calls**:
```python
# Instead of sequential:
text = extract_text(image_path)
summary = summarize(text)

# Use parallel when possible:
async def extract_and_summarize(image_path: str):
    """Extract and summarize in parallel (if independent)."""
    tasks = [
        extract_text_async(image_path),
        extract_metadata_async(image_path)
    ]
    text, metadata = await asyncio.gather(*tasks)

    # Then summarize (depends on text)
    summary = await summarize_async(text)

    return {"text": text, "metadata": metadata, "summary": summary}
```

**Note**: Only for independent operations. Tool calling in sequence is fine for MVP.

### 5. Guardrails at Boundaries

**Validate inputs**:
```python
def validate_upload(file: UploadFile) -> None:
    """Validate uploaded file at API boundary."""
    # Check content type
    if not file.content_type.startswith("image/"):
        raise ValueError(f"Invalid content type: {file.content_type}")

    # Check file size
    max_size = 10 * 1024 * 1024  # 10 MB
    if file.size > max_size:
        raise ValueError(f"File too large: {file.size} bytes")

    # Check dimensions (if needed)
    from PIL import Image
    import io

    content = file.file.read()
    file.file.seek(0)  # Reset for later reads

    image = Image.open(io.BytesIO(content))
    if image.width > 4096 or image.height > 4096:
        raise ValueError(f"Image too large: {image.size}")
```

**Sanitize outputs**:
```python
def sanitize_extraction(result: dict) -> dict:
    """Sanitize extraction result before returning."""
    sanitized = {}

    # Remove any system paths
    for key, value in result.items():
        if isinstance(value, str):
            # Remove file paths
            value = re.sub(r'/\S+/\S+', '[PATH]', value)
            # Remove special characters
            value = ''.join(c for c in value if c.isprintable())

        sanitized[key] = value

    return sanitized
```

### 6. Error Handling Strategy

**Distinguish error types**:
```python
class VLMError(Exception):
    """VLM-specific error (may retry)."""
    pass

class ToolError(Exception):
    """Tool execution error (fail fast)."""
    pass

class ValidationError(Exception):
    """Validation error (bad data)."""
    pass

def handle_errors(func):
    """Error handling decorator."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)

        except VLMError as e:
            # VLM timeout/overload - retry with backoff
            logger.warning(f"VLM error (retryable): {e}")
            mlflow.log_param("error_type", "vlm")
            # Retry logic here
            raise

        except ToolError as e:
            # Tool bug/missing dependency - fail fast
            logger.error(f"Tool error (not retryable): {e}")
            mlflow.log_param("error_type", "tool")
            raise

        except ValidationError as e:
            # Bad extraction result - may indicate wrong screen type
            logger.error(f"Validation error: {e}")
            mlflow.log_param("error_type", "validation")
            raise

    return wrapper
```

### 7. Testing Strategy

**Unit tests with mocks**:
```python
@pytest.fixture
def mock_orchestrator():
    """Mock VLMOrchestrator for fast unit tests."""
    with patch('module.VLMOrchestrator') as mock:
        mock.return_value.analyze_screenshot.return_value = {
            "name": "Parsnip",
            "description": "A spring vegetable",
            "price_per_unit": 20,
            "quantity_selected": 5,
            "total_cost": 100
        }
        yield mock

def test_api_endpoint(mock_orchestrator, client):
    """Test API endpoint without running VLM."""
    response = client.post("/analyze", files={"file": ("test.png", b"data", "image/png")})

    assert response.status_code == 200
    assert response.json()["extraction"]["name"] == "Parsnip"
```

**Integration tests separate**:
```python
@pytest.mark.integration
@pytest.mark.requires_vllm
def test_real_vlm():
    """Integration test with real vLLM server."""
    orchestrator = VLMOrchestrator()  # Real instance
    result = orchestrator.analyze_screenshot("tests/fixtures/pierre_shop_001.png")

    assert "name" in result
    assert result["price_per_unit"] > 0
```

### 8. Framework Minimalism

**Decision tree**:
1. **Can I do this with a function?** → Use function
2. **Do I need tool calling?** → Use raw OpenAI client
3. **Do I need VLM-specific features?** → Use Smolagents
4. **Do I need state machines?** → Use LangGraph
5. **Do I need multi-agent?** → Use CrewAI or Smolagents multi-agent

**Don't prematurely abstract**:
```python
# ❌ Overkill for single tool
class ToolOrchestrator:
    def __init__(self):
        self.router = ToolRouter()
        self.executor = ToolExecutor()
        self.validator = ToolValidator()
        # ... 200 lines later

# ✅ Start simple
def dispatch_tool(name: str, args: dict) -> dict:
    return TOOL_REGISTRY[name](**args)
```

### 9. Production Readiness

**Health checks**:
```python
@app.get("/health")
async def health_check():
    """Comprehensive health check."""
    health = {"status": "healthy", "checks": {}}

    # Check VLM endpoint
    try:
        response = await client.get(f"{vlm_endpoint}/v1/models", timeout=2)
        health["checks"]["vlm"] = "up"
    except Exception as e:
        health["checks"]["vlm"] = f"down: {e}"
        health["status"] = "unhealthy"

    # Check extraction tool
    try:
        TOOL_REGISTRY["crop_pierres_detail_panel"]
        health["checks"]["tools"] = "loaded"
    except Exception as e:
        health["checks"]["tools"] = f"error: {e}"
        health["status"] = "unhealthy"

    return health
```

**Graceful degradation**:
```python
async def analyze_with_fallback(image_path: str):
    """Try VLM, fall back to rule-based."""
    try:
        return await vlm_analyze(image_path)
    except VLMError:
        logger.warning("VLM failed, using rule-based fallback")
        return rule_based_analyze(image_path)
```

### 10. Documentation as Code

**OpenAPI schemas**:
```python
@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_screenshot(
    file: UploadFile = File(..., description="Screenshot PNG/JPG")
) -> AnalysisResponse:
    """
    Analyze a Stardew Valley screenshot and extract UI panel contents.

    **Supported panels**:
    - Pierre's General Store detail panel

    **Returns**:
    - Extracted fields (name, description, price, quantity, total)

    **Errors**:
    - 400: Invalid file format
    - 500: VLM analysis failed
    """
    # Implementation
    pass
```

Auto-generated docs at `/docs` with FastAPI.

## Anti-Patterns

### ❌ Don't Hallucinate Tools

```python
# ❌ Wrong: VLM invents non-existent tools
TOOL_DEFINITIONS = []  # Empty!

# VLM response: {"tool": "extract_everything", ...}
# Result: KeyError

# ✅ Right: Provide all available tools upfront
TOOL_DEFINITIONS = [
    {"name": "crop_pierres_detail_panel", ...},
    # All real tools
]
```

### ❌ Don't Trust VLM Paths

```python
# ❌ Wrong: Use VLM-provided path
tool_call = response.tool_calls[0]
args = json.loads(tool_call.arguments)
result = extract(args["image_path"])  # VLM might hallucinate path!

# ✅ Right: Override with actual path
args["image_path"] = actual_image_path
result = extract(args["image_path"])
```

### ❌ Don't Ignore Validation

```python
# ❌ Wrong: Assume VLM result is correct
result = vlm.analyze(image)
return result  # Might be garbage

# ✅ Right: Validate before returning
result = vlm.analyze(image)
validated = validate_schema(result)
if not verify_quality(validated):
    raise ValueError("Extraction quality too low")
return validated
```

### ❌ Don't Block on Synchronous Calls

```python
# ❌ Wrong: Block web server on slow VLM
@app.post("/analyze")
def analyze(file):
    result = vlm.analyze(file)  # Blocks for 2+ seconds
    return result

# ✅ Right: Use async
@app.post("/analyze")
async def analyze(file):
    result = await vlm.analyze_async(file)
    return result
```

## Production Checklist

- [ ] All tool calls logged to MLFlow
- [ ] JSON schema validation on outputs
- [ ] Pass-fail checks for extraction quality
- [ ] Error handling (VLM vs tool vs validation)
- [ ] Unit tests with mocked VLM (fast)
- [ ] Integration tests with real VLM (slower, marked)
- [ ] Health check endpoint
- [ ] Graceful degradation/fallbacks
- [ ] Input validation at API boundaries
- [ ] Output sanitization (remove paths, etc.)
- [ ] Async API endpoints (non-blocking)
- [ ] OpenAPI documentation
- [ ] Observability dashboard (MLFlow UI)
- [ ] Framework minimalism (no premature abstraction)

## Measurement

**Key metrics to track**:
1. **Latency**: P50, P95, P99 for tool calls
2. **Success rate**: % of successful extractions
3. **Validation rate**: % passing quality checks
4. **Error distribution**: VLM vs tool vs validation errors
5. **Token usage**: VLM input/output tokens (cost)
6. **Throughput**: Requests/second
7. **User satisfaction**: Accuracy on test set

## Resources

**Research Sources**:
- [Best AI Models for Agentic Workflows in 2026](https://www.mindstudio.ai/blog/best-ai-models-agentic-workflows-2026)
- [How Tools Are Called in AI Agents: Complete 2025 Guide](https://medium.com/@sayalisureshkumbhar/how-tools-are-called-in-ai-agents-complete-2025-guide-with-examples-42dcdfe6ba38)
- [Agents At Work: 2026 Playbook](https://promptengineering.org/agents-at-work-the-2026-playbook-for-building-reliable-agentic-workflows/)
- [Tool Calling in AI Agents 2026](https://www.techjunkgigs.com/tool-calling-in-ai-agents-how-llms-execute-real-world-actions-in-2026/)

---

**Remember**: Best practices evolve. These are 2026 standards based on production deployments. Always validate against your specific use case and constraints.
