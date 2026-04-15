# Lessons Learned

This document captures important lessons learned during development that should inform future projects.

## OpenShift Permissions vs Local Devcontainer

**Date:** 2026-04-13

**Problem:** PaddleOCR/PaddleX worked perfectly in local devcontainer but failed in OpenShift with `Permission denied: '/.paddlex'` errors.

**Root Cause:** Local devcontainers often run with relaxed filesystem permissions (user's UID or privileged container mode), allowing writes to root-owned directories like `/.paddlex`, `/.cache`, etc. to succeed silently. OpenShift enforces strict security - containers run with random UIDs (e.g., 1000860000) and cannot write to most filesystem locations.

**The Hidden Bug:** PaddleX was ignoring Dockerfile `ENV` variables (like `ENV PADDLEX_HOME=/tmp/.paddlex`) and still trying to write to the hardcoded default `/.paddlex`. This worked locally due to relaxed permissions, so we never saw the bug. OpenShift's strict permissions exposed it immediately.

**The Fix:** Setting environment variables in Python code **before** imports:

```python
# At the very top of the module, before any imports that trigger initialization
import os
os.environ.setdefault('PADDLEX_HOME', '/tmp/.paddlex')
os.environ.setdefault('PADDLEX_CACHE_DIR', '/tmp/.paddlex/cache')
os.environ.setdefault('PADDLE_HUB_HOME', '/tmp/.paddlex/hub')
os.environ.setdefault('PADDLE_OCR_BASE_DIR', '/tmp/.paddleocr')

# NOW safe to import
from paddleocr import PaddleOCR
```

**Key Takeaways for Future Projects:**

1. **Assume local permissions hide bugs** - Code that works in local devcontainer may have hidden filesystem permission issues that only surface in OpenShift

2. **Audit third-party libraries** - When moving to OpenShift, actively look for any library that writes cache/config/temp files. Check if they respect environment variables.

3. **Dockerfile ENV is not enough** - Some libraries (like PaddleX) read environment variables during module initialization in ways that don't see Dockerfile `ENV` statements. Set them in Python code with `os.environ.setdefault()` BEFORE imports.

4. **Only use writable locations** - In OpenShift, assume you can only write to:
   - `/tmp` (always writable)
   - Mounted PersistentVolumeClaims
   - Never assume write access to root directories or home directories

5. **Test in OpenShift early** - Don't wait until late in deployment to test in the target environment. OpenShift's strict permissions are a feature, not a bug - they expose real portability problems.

6. **Check every service** - When debugging permission issues, audit ALL services (OCR, TTS, coordinator), not just the one currently failing. Each may have different libraries with different cache behaviors.

**Files Changed:**
- `services/pierres_buying_tool/stardew_pierres_buying/crop_pierres_detail_panel.py` - Added `os.environ.setdefault()` calls before imports
- `services/pierres_buying_tool/Dockerfile` - Added `ENV` variables (belt-and-suspenders, even though code fix is primary)

**Related:** See memory file `feedback_openshift_permissions.md` for detailed guidance on this pattern.

---

## PaddlePaddle MKLDNN/OneDNN CPU Architecture Incompatibility

**Date:** 2026-04-13

**Problem:** After fixing permissions, OCR service in OpenShift crashed with `SIGTERM` during inference. Error trace showed `OneDNNPhiKernelInstruction::Run()` followed by termination signal. Models downloaded successfully, but pod died during actual OCR processing with "Processing 5 items: 100%" then SIGTERM.

**Root Cause:** PaddlePaddle is compiled with Intel MKLDNN (OneDNN) optimizations enabled by default. These optimizations require specific CPU instruction sets (AVX, AVX2, AVX-512). When the container runs on a Kubernetes/OpenShift node with an incompatible CPU architecture, MKLDNN attempts to use unavailable instructions, causing illegal instruction errors and SIGTERM.

**Evidence:**
- Local container (AMD Strix Halo with AVX2): Works perfectly, 730 MiB memory usage, no crashes
- OpenShift cluster node (unknown CPU): SIGTERM crash during OneDNN kernel execution
- Local dev script (`data/dev/test_ocr_on_panel.py`) already disables MKLDNN with comment "Disable OneDNN optimizations that seem to be causing issues"

**The Fix:** Disable MKLDNN and XDNN optimizations via environment variables:

```python
# Disable MKLDNN/OneDNN optimizations to avoid CPU architecture incompatibilities
# in Kubernetes/OpenShift environments
os.environ.setdefault('FLAGS_use_mkldnn', '0')
os.environ.setdefault('FLAGS_use_xdnn', '0')
```

**Memory Impact:** Disabling MKLDNN does NOT significantly increase memory usage. Local testing shows:
- With optimizations: ~730 MiB
- Expected without: Similar (MKLDNN is for CPU performance, not memory)

**Performance Impact:** MKLDNN provides 2-4x CPU inference speedup on compatible hardware. Disabling it will make OCR slower, but correct and portable across all CPU architectures. For production with known compatible CPUs, this can be re-enabled.

**Key Takeaways for Future Projects:**

1. **CPU architecture portability** - Libraries compiled with architecture-specific optimizations (MKLDNN, AVX, NEON) may not work on all cluster nodes. Disable optimizations for portability or use node selectors to target compatible hardware.

2. **Check local dev scripts** - If dev scripts already disable optimizations, that's a clue the production service needs the same fix. Don't assume "it works locally" means the optimizations are safe.

3. **SIGTERM during model inference** - Not always OOM. Check for `OneDNN`, `MKLDNN`, `AVX` in stack traces - these indicate CPU instruction incompatibility, not resource limits.

4. **Test with actual inference** - Health checks may pass (they don't load models), but first real request crashes. Always test end-to-end with real data.

**Files Changed:**
- `services/pierres_buying_tool/stardew_pierres_buying/app.py` - Added `FLAGS_use_mkldnn=0` and `FLAGS_use_xdnn=0` environment variables

**Related Issues:**
- [PaddleOCR Issue #16789: paddleocr gives 'Illegal instruction' on ARM/CPU-only docker](https://github.com/PaddlePaddle/PaddleOCR/issues/16789)
- [Paddle Issue #76111: PaddleOCR v3.3.0 + PaddlePaddle v3.0.0 fails in Docker (ARM64 & x86_64)](https://github.com/PaddlePaddle/Paddle/issues/76111)

---

## Model Instance Caching for Inference Services

**Date:** 2026-04-13

**Problem:** OCR service in OpenShift was taking 32 seconds per request even after models were downloaded and cached in a PVC. Every request returned "Creating model" logs showing models being loaded from disk into memory.

**Root Cause:** The OCR extraction function called `_load_ocr()` which created a **new** PaddleOCR instance on every request. PaddleOCR model loading involves:
1. Reading 200MB+ model files from disk
2. Deserializing model weights
3. Initializing inference engine
4. Allocating memory structures

This took ~30 seconds per request, even though model files were already cached on disk.

**The Fix:** Cache the PaddleOCR instance in a module-level variable:

```python
# Module-level cache
_OCR_INSTANCE = None

def _load_ocr():
    """Lazy-load PaddleOCR and cache the instance."""
    global _OCR_INSTANCE
    if _OCR_INSTANCE is None:
        from paddleocr import PaddleOCR
        _OCR_INSTANCE = PaddleOCR(
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            lang="en",
        )
    return _OCR_INSTANCE
```

**Performance Impact:**
- **Before**: 32s per request (model loading from disk every time)
- **After**: First request ~30s (one-time loading), subsequent requests ~2s (inference only)

**Memory Impact:**
- OCR service memory usage: ~730 MiB with models loaded
- Acceptable for the performance gain (16x faster on subsequent requests)

**Key Takeaways for Future Projects:**

1. **Distinguish model file caching from instance caching** - PVCs cache files on disk; in-memory caching avoids disk I/O and deserialization overhead. You need both.

2. **First request is slow, by design** - The first request after pod startup must pay the model loading cost. This is acceptable if documented. Log it clearly so operators know it's expected behavior.

3. **Use module-level variables for singletons** - Python's module import system ensures thread-safe singleton behavior. A module-level cached instance is simpler and more reliable than manual singleton patterns.

4. **Memory limits must accommodate loaded models** - Set memory requests/limits based on models loaded in memory (not just model file size). PaddleOCR models are ~200MB on disk but use ~700MB in memory.

5. **Init containers for cold start optimization** - Use init containers to pre-download and pre-load models before the main container becomes ready. This moves the cold start delay to pod startup time instead of first user request.

6. **Test with realistic request patterns** - Don't just test the first request. Test 5-10 sequential requests to verify caching is working and memory isn't growing unboundedly.

7. **Log model loading clearly** - Add INFO logs when loading models ("Loading PaddleOCR models from /cache/paddlex...") and when using cached instance ("Using cached PaddleOCR instance"). Makes debugging much easier.

**Applicability to Other Frameworks:**
- HuggingFace Transformers: Same pattern - cache `pipeline()` or model instances
- TensorFlow/PyTorch: Cache loaded models, not just downloaded weights
- spaCy: Cache `spacy.load()` results
- Any framework with expensive model initialization

**Files Changed:**
- `services/pierres_buying_tool/stardew_pierres_buying/crop_pierres_detail_panel.py` - Added `_OCR_INSTANCE` global cache
- `configs/serving/openshift/10-deployment-pierres-buying-tool.yaml` - Increased memory limits to 4Gi request, 8Gi limit

**Related:** See ADR-012 for full OpenShift deployment architecture including model caching strategy.
