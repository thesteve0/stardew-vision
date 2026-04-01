# Session Handoff - 2026-03-31

## CRITICAL: What to Do Next Session

**NO MATTER WHAT, THIS IS THE NEXT TASK**: Annotate the 20 Pierre's shop screenshots manually.

This is the ONLY blocker preventing progress to the VLM orchestrator work. Everything is ready to go - the user just needs to run the annotation workflow.

## Current State Summary

### Completed in This Session ✅
1. Fixed `pierre_panel_layout.json` malformed JSON (removed leading "2")
2. Downgraded PaddlePaddle to 3.2.0 (was 3.3.0 with OneDNN bug)
3. Created directory structure (`datasets/raw/pierre_shop/`, etc.)
4. Changed schema from `image_id` (UUID) to `image_hash` (SHA256) + added `original_file_name`
5. Created `configs/annotation_schema.json`
6. Created `scripts/annotate_pierre_shop.py` (auto-generate and validate modes)
7. Auto-generated 22 annotations (2 succeeded, 20 failed template matching)
8. Created `scripts/interactive_annotate.py` for manual annotation
9. Discovered GUI display doesn't work in devcontainer (no image viewer installed)
10. Created `scripts/generate_annotation_viewer.py` and generated `annotation_viewer.html`

### Ready to Use 🎯
- `annotation_viewer.html` - HTML page with all 20 images that need annotation
- `scripts/interactive_annotate.py` - Terminal prompts for the 5 fields per image
- Workflow documented in `docs/ANNOTATION_WORKFLOW.md`

### What User Needs to Do

**Step 1**: Open HTML viewer on HOST (not in container)
```bash
# On the host machine
firefox /path/to/stardew-vision/annotation_viewer.html
```

**Step 2**: Run interactive script in devcontainer
```bash
python scripts/interactive_annotate.py
```

**Step 3**: For each of 20 images:
- Terminal shows: image number, filename, resolution
- User scrolls to that image in the HTML viewer
- User reads the RIGHT PANEL (orange detail view)
- User enters 5 fields in terminal:
  - Item name
  - Item description
  - Price per unit (integer)
  - Quantity selected (integer)
  - Total cost (integer)
- Script validates math, saves annotation
- Repeat for next image

**Estimated time**: 20 images × 2-3 minutes = 40-60 minutes

## Why GUI Display Doesn't Work

**Root cause**: No image viewer program installed in the devcontainer.

**What we tried**:
1. opencv-python (`cv2.imshow`) - bundled Qt only has xcb (X11) plugin, not wayland
2. matplotlib - uses `agg` backend (non-interactive), GTK3/Tk backends not available (PyGObject and tkinter not installed)
3. PIL.Image.show() - no default viewer (xdg-open, eog, feh all missing)

**Wayland is configured correctly**:
- Socket mounted: `/run/user/1000/wayland-0` → `/tmp/wayland-0`
- Environment vars set: `WAYLAND_DISPLAY=wayland-0`, `XDG_RUNTIME_DIR=/tmp`, `QT_QPA_PLATFORM=wayland`
- The infrastructure works - just no GUI apps installed

**Solution**: HTML viewer on host (doesn't require container GUI support)

## Annotation Schema Structure

```json
{
  "image_hash": "sha256_hash_of_file",
  "original_file_name": "IMG_7708.jpg",
  "screen_type": "pierre_shop",
  "image_path": "datasets/raw/pierre_shop/IMG_7708.jpg",
  "resolution": [1600, 1200],
  "expected_extraction": {
    "name": "",              // ← USER FILLS THIS
    "description": "",        // ← USER FILLS THIS
    "price_per_unit": 0,      // ← USER FILLS THIS
    "quantity_selected": 0,   // ← USER FILLS THIS
    "total_cost": 0           // ← USER FILLS THIS
  },
  "created_at": "2026-03-31T...",
  "annotated_by": "manual_required",  // → Changed to "human" after annotation
  "extraction_succeeded": false,      // → Changed to true after annotation
  "version": "1.0"
}
```

## Why Template Matching Failed

- Template extracted from PC screenshot (`1_pierres_top.jpg` at 1600×1200)
- 21 new screenshots are from iPad (different rendering/resolution)
- Template matching confidence: 0.68-0.82 (threshold is 0.85)
- Could lower threshold to ~0.75, but risky (may match wrong regions)
- Manual annotation is safer for ground truth

## After Annotation is Complete

1. Validate: `python scripts/annotate_pierre_shop.py --mode validate --annotations datasets/annotated/pierre_shop/annotations.jsonl`
2. Identify test images (left panel ≠ right panel cases)
3. Create `scripts/generate_splits.py` (not yet implemented)
4. Generate 65/20/15 train/val/test splits
5. Begin VLM orchestrator work (Phase 1 Step 7 in docs/plan.md)

## Key Files

**Documentation**:
- `docs/ANNOTATION_WORKFLOW.md` - Complete workflow guide (NEW)
- `docs/IMPLEMENTATION_STATUS.md` - Updated with current status
- `docs/plan.md` - Overall project plan
- `docs/data-collection-plan.md` - Annotation schema specification

**Data**:
- `datasets/raw/pierre_shop/` - 22 screenshots
- `datasets/annotated/pierre_shop/annotations.jsonl` - 22 annotations (20 need manual input)
- `annotation_viewer.html` - HTML viewer (open on host)

**Scripts**:
- `scripts/interactive_annotate.py` - Interactive annotation (READY TO USE)
- `scripts/annotate_pierre_shop.py` - Auto-generate and validate
- `scripts/generate_annotation_viewer.py` - Generate HTML (already run)
- `scripts/generate_splits.py` - NOT YET CREATED

**Config**:
- `configs/annotation_schema.json` - JSON Schema for validation

## Important Context

**Split ratios**: 65% train, 20% val, 15% test (user specifically requested this, NOT 70/15/15)

**Test split strategy**: User wants specific images in test set where left panel selection ≠ right panel detail view. This ensures the model reads the correct UI region.

**Framework decision**: Using Smolagents for agent/tool-calling (see `docs/agent-frameworks-compared.md`)

**Hardware constraints**: AMD Strix Halo, ROCm 7.2, FP16 only (no BF16, INT4, INT8)

## User Preferences from This Session

1. Prefers manual annotation over lowering template matching threshold
2. Wanted `image_hash` instead of `image_id` (UUID)
3. Wanted `original_file_name` field added
4. Wanted interactive annotation script (not direct JSONL editing)
5. Requested 65/20/15 split (not random - manual test image selection)

## Critical Technical Notes

**PaddlePaddle version**: MUST be 3.2.0. Version 3.3.0 has OneDNN PIR conversion bug. Already fixed in this session.

**Package management**: Always use `uv`, NEVER use `pip` (preserves ROCm PyTorch installation)

**Devcontainer user**: `stpousty-devcontainer` (UID 2112, GID 2112)

**Python path**: `PYTHONPATH=/workspaces/stardew-vision/src` (set in devcontainer.json)

## Memory/Context for Next Session

The user has been working on this project for annotation/data collection as a prerequisite for training the VLM orchestrator. The overall goal is to build an accessibility tool for visually impaired Stardew Valley players - they upload a screenshot, get audio narration of the UI panel.

The project uses a two-layer architecture:
1. **VLM Orchestrator** (Qwen2.5-VL-7B) - classifies screen type, dispatches tool calls
2. **Extraction Agents** (OpenCV + PaddleOCR, CPU-only) - crop panel, extract text, return JSON

We're currently in the data collection phase - need ground truth annotations to evaluate the extraction tool and train the orchestrator.

User is patient, technical, and prefers to understand what's happening rather than have things done automatically. They make thoughtful decisions about splits, schema changes, etc.

Next session should start by immediately asking: "Ready to annotate the 20 images? I have the workflow ready in docs/ANNOTATION_WORKFLOW.md - just need you to open annotation_viewer.html on your host and run the interactive script."
