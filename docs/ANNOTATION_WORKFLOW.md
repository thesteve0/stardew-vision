# Pierre's Shop Screenshot Annotation Workflow

**Status**: Infrastructure complete, ready to annotate 20 images
**Created**: 2026-03-31
**Last Updated**: 2026-03-31

## Overview

We have 22 Pierre's shop screenshots that need ground truth annotations for training and evaluation. The extraction tool auto-succeeded on 2 images but failed on 20 due to template matching issues (iPad vs PC resolution differences). These 20 need manual annotation.

## Current State

### Completed ✅
- ✅ Directory structure created (`datasets/raw/pierre_shop/`, `datasets/annotated/pierre_shop/`, `datasets/splits/`)
- ✅ 22 screenshots copied to `datasets/raw/pierre_shop/`
- ✅ Annotation schema created (`configs/annotation_schema.json`) with `image_hash` + `original_file_name` fields
- ✅ Auto-generation script created (`scripts/annotate_pierre_shop.py`)
- ✅ 22 annotations auto-generated in `datasets/annotated/pierre_shop/annotations.jsonl`
  - 2 succeeded automatically (1_pierres_top.jpg, IMG_7731.jpg)
  - 20 need manual input (all IMG_*.jpg files)
- ✅ Interactive annotation script created (`scripts/interactive_annotate.py`)
- ✅ HTML viewer generated (`annotation_viewer.html`)
- ✅ PaddlePaddle downgraded to 3.2.0 (was 3.3.0 with OneDNN bug)
- ✅ JSON bug fixed in `datasets/assets/templates/pierre_panel_layout.json`

### Blocked ❌
- **GUI display doesn't work in devcontainer** - Wayland is configured but no image viewer is installed
- **Solution**: Use HTML viewer on host + terminal prompts in container (see workflow below)

## Annotation Workflow (READY TO USE)

### Step 1: Start HTTP Server in Devcontainer

In the **devcontainer terminal**:

```bash
python scripts/serve_annotation_viewer.py
```

This starts a local HTTP server on port 8888 (already forwarded by the devcontainer). The server will display:
- The URL to open: `http://localhost:8888/annotation_viewer.html`
- Instructions for the workflow
- Server status messages

**Keep this terminal running** during the entire annotation session.

**Why HTTP server?** Opening `annotation_viewer.html` directly with `file://` protocol doesn't work because browsers block relative image paths for security reasons. The HTTP server resolves this by serving the workspace directory properly.

### Step 2: Open Annotation Viewer in Browser

Open the URL shown by the server (typically):
```
http://localhost:8888/annotation_viewer.html
```

The HTML page shows all 20 images that need annotation in a scrollable view. The devcontainer forwards port 8888, so you can access this from your host browser.

### Step 3: Run Interactive Annotation Script in Separate Terminal

In a **NEW devcontainer terminal** (keep the server running in the first terminal):

```bash
python scripts/interactive_annotate.py
```

### Step 4: Annotate Each Image

For each of the 20 images:

1. **Terminal shows**: Image number, filename, hash, resolution
2. **You scroll** in the HTML viewer to find that image
3. **Look at the RIGHT PANEL** (orange detail view) in the screenshot
4. **Terminal prompts** for 5 fields:
   - Item name (e.g., "Bean Starter")
   - Item description (e.g., "Plant these in the spring. Takes 10 days to mature, but keeps producing after that. Grows on a trellis.")
   - Price per unit (integer, e.g., 90)
   - Quantity selected (integer, e.g., 1)
   - Total cost (integer, e.g., 90)
5. **Script validates**: total_cost == price_per_unit × quantity_selected
6. **Choose action**: [a] Annotate, [s] Skip, [q] Quit
7. **Repeat** for next image

**Progress is saved automatically** after each annotation.

### Step 5: Validate Annotations

After completing all 20 annotations:

```bash
python scripts/annotate_pierre_shop.py --mode validate \
  --annotations datasets/annotated/pierre_shop/annotations.jsonl
```

Expected results:
- ✅ 100% schema compliance
- ✅ All 22 images have `extraction_succeeded: true` (after manual input)
- ✅ Math checks pass (total_cost == price × quantity)
- ✅ Field accuracy ≥ 90%

### Step 6: Identify Test Split Images

Manually review the 22 screenshots and identify images where:
- **Left panel** (item list) shows a DIFFERENT item highlighted than what's displayed in the **right panel** (detail view)
- These are critical test cases - they verify the model reads the right panel, not the left panel

Create `datasets/splits/manual_test_images.txt` with filenames (one per line):
```
IMG_7708.jpg
IMG_7715.jpg
...
```

**Why this matters**: Without these test cases, a model could achieve high accuracy by reading the wrong panel.

### Step 7: Generate Train/Val/Test Splits

**NOT YET IMPLEMENTED** - Need to create `scripts/generate_splits.py`:

```bash
python scripts/generate_splits.py \
  --annotations datasets/annotated/pierre_shop/annotations.jsonl \
  --train 0.65 --val 0.20 --test 0.15 \
  --output-dir datasets/splits/ \
  --manual-test-images datasets/splits/manual_test_images.txt
```

Expected output:
- `datasets/splits/pierre_shop_train.txt` (~14 image hashes)
- `datasets/splits/pierre_shop_val.txt` (~4 image hashes)
- `datasets/splits/pierre_shop_test.txt` (~3 image hashes, includes manual test cases)

## Annotation Schema

Each annotation in `datasets/annotated/pierre_shop/annotations.jsonl`:

```json
{
  "image_hash": "9f8c3386092a9253923838c7feb986606a25f75cad02bc32ec8e421b9efb486c",
  "original_file_name": "IMG_7708.jpg",
  "screen_type": "pierre_shop",
  "image_path": "datasets/raw/pierre_shop/IMG_7708.jpg",
  "resolution": [1600, 1200],
  "expected_extraction": {
    "name": "Bean Starter",
    "description": "Plant these in the spring. Takes 10 days to mature, but keeps producing after that. Grows on a trellis.",
    "price_per_unit": 90,
    "quantity_selected": 1,
    "total_cost": 90
  },
  "created_at": "2026-03-31T07:46:47.358947+00:00",
  "annotated_by": "human",
  "extraction_succeeded": true,
  "version": "1.0"
}
```

## Files

**Data**:
- `datasets/raw/pierre_shop/` - 22 original screenshots
- `datasets/annotated/pierre_shop/annotations.jsonl` - Ground truth annotations (20 need manual input)
- `annotation_viewer.html` - HTML viewer for browsing images (open on host)

**Scripts**:
- `scripts/serve_annotation_viewer.py` - HTTP server for viewing annotations in browser
- `scripts/annotate_pierre_shop.py` - Auto-generate and validate annotations
- `scripts/interactive_annotate.py` - Interactive annotation (terminal prompts + HTML viewer)
- `scripts/generate_annotation_viewer.py` - Generate HTML viewer (already run)
- `scripts/generate_splits.py` - **NOT YET CREATED** - Generate train/val/test splits

**Configuration**:
- `configs/annotation_schema.json` - JSON Schema for validation
- `datasets/assets/templates/pierre_panel_layout.json` - Template matching layout (bug fixed)

## Troubleshooting

### HTTP Server Issues

**Problem**: "Port 8888 is already in use"

**Solution**: Use a different port:
```bash
python scripts/serve_annotation_viewer.py --port 8889
```
Then open `http://localhost:8889/annotation_viewer.html` in your browser.

**Problem**: Images don't load in the browser

**Solutions**:
1. Verify the HTTP server is running (check the terminal)
2. Ensure you're accessing via `http://localhost:8888` (NOT by opening the file directly)
3. Check browser console (F12) for 404 errors
4. Verify images exist in `datasets/raw/pierre_shop/`

**Problem**: Can't access `http://localhost:8888` from host browser

**Solutions**:
1. Verify port 8888 is forwarded in `.devcontainer/devcontainer.json` (it should be)
2. Check VS Code "Ports" panel - port 8888 should be listed and forwarded
3. Try `http://127.0.0.1:8888/annotation_viewer.html` instead

### GUI Display Issues

**Problem**: No image viewer in devcontainer, Wayland configured but no GUI apps installed.

**Solution**: Use the HTTP server + browser approach (see workflow above). This is the recommended approach for 20 images.

**Alternative (not recommended)**: Install image viewer in Dockerfile and rebuild:
```dockerfile
# Add to Dockerfile
RUN apt-get update && apt-get install -y eog
```

### Template Matching Failures

**Problem**: 20/22 images failed template matching with confidence 0.68-0.82 (threshold is 0.85).

**Why**: Template extracted from PC screenshot (1_pierres_top.jpg), but most new images are from iPad (different rendering).

**Solutions**:
1. ✅ **Current approach**: Manual annotation (what we're doing)
2. Lower threshold to ~0.75 in `crop_pierres_detail_panel.py` (risky - may match wrong regions)
3. Extract new template from iPad screenshot (future improvement)

### PaddlePaddle Version

**CRITICAL**: Must use `paddlepaddle==3.2.0`. Version 3.3.0 has OneDNN PIR bug.

Error if wrong version:
```
NotImplementedError: (Unimplemented) ConvertPirAttribute2RuntimeAttribute not support [pir::ArrayAttribute<pir::DoubleAttribute>]
```

Fix: `uv add paddlepaddle==3.2.0`

## Next Steps (After Annotations Complete)

1. **Create `scripts/generate_splits.py`** - Split generator with manual test image support
2. **Identify test images** - Find left≠right panel cases
3. **Generate splits** - 65% train, 20% val, 15% test
4. **Update IMPLEMENTATION_STATUS.md** - Mark annotation phase complete
5. **Begin VLM orchestrator work** - Next major phase (see docs/plan.md Step 7)

## References

- Overall plan: `docs/plan.md`
- Data collection strategy: `docs/data-collection-plan.md`
- Implementation status: `docs/IMPLEMENTATION_STATUS.md`
- Wayland GUI setup: `docs/getting-guis-to-work-with-devcontainers-wayland.md`
