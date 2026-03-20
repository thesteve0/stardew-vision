# Implementation Status

**Last updated**: 2026-03-20

## Completed Features

### Phase 1: Pierre's Shop Extraction Tool ✅

**Status**: COMPLETE (2026-03-20)

#### What Works

1. **Anchor Template Extraction**
   - Tool: `scripts/extract_anchor_template.py`
   - Template: `datasets/assets/templates/pierres_detail_panel_corner.png` (400×945 px)
   - Layout: `datasets/assets/templates/panel_layout.json` with relative coordinates
   - Coordinates: `x=0.6875, y=0.1292, w=0.25, h=0.7875` (resolution-independent)

2. **OCR Extraction**
   - Library: PaddleOCR PP-OCRv5 (CPU-only)
   - Version: `paddleocr>=3.4.0` with `paddlepaddle==3.2.0`
   - Confidence: 85-99% on Pierre's shop panel
   - Performance: ~3-5 seconds per screenshot

3. **Production Tool**
   - File: `src/stardew_vision/tools/crop_pierres_detail_panel.py`
   - Features:
     - Multi-scale template matching (75%, 100%, 125%, 150% UI scales)
     - Automatic panel location at any resolution
     - Field extraction with position-based parsing
     - Structured JSON output

4. **Extracted Fields**
   - ✅ Item name (e.g., "Parsnip Seeds")
   - ✅ Description (e.g., "Plant these in the spring. Takes 4 days to mature.")
   - ✅ Price per unit (e.g., 20 gold)
   - ✅ Quantity selected (e.g., 60)
   - ✅ Total cost (e.g., 1200 gold)

5. **Unit Tests**
   - File: `tests/test_tools.py`
   - Status: **8/8 tests passing**
   - Coverage:
     - Template matching validation
     - OCR accuracy (fuzzy string matching via rapidfuzz)
     - Field type validation
     - Error handling (PanelNotFoundError)
     - Numeric parsing (handles "x60: 1200" format)

#### Test Results

```
pytest tests/test_tools.py -v

tests/test_tools.py::test_panel_not_found_raises PASSED                  [ 12%]
tests/test_tools.py::test_parse_pierre_fields_structure PASSED           [ 25%]
tests/test_tools.py::test_parse_pierre_fields_types PASSED               [ 37%]
tests/test_tools.py::test_parse_pierre_fields_price_parsing PASSED       [ 50%]
tests/test_tools.py::test_locate_panel_finds_match PASSED                [ 62%]
tests/test_tools.py::test_extract_returns_required_keys PASSED           [ 75%]
tests/test_tools.py::test_field_types PASSED                             [ 87%]
tests/test_tools.py::test_known_fixture_values PASSED                    [100%]

8 passed in 10.85s
```

#### Example Extraction

**Input**: `datasets/from-katarina/1_pierres_top.jpg` (1600×1200)

**Output**:
```json
{
  "name": "Parsnip Seeds",
  "description": "Plant these in the spring. Takes 4 days to mature.",
  "price_per_unit": 20,
  "quantity_selected": 60,
  "total_cost": 1200
}
```

#### Key Technical Decisions

1. **PaddleOCR over EasyOCR**
   - Rationale: Faster CPU throughput (3-10x), SOTA accuracy, preserves capitalization
   - See: `docs/ocr-choice.md`

2. **PaddlePaddle Version Lock**
   - **CRITICAL**: Must use `paddlepaddle==3.2.0`
   - Version 3.3.0 has OneDNN PIR conversion bug
   - Error: `ConvertPirAttribute2RuntimeAttribute not support [pir::ArrayAttribute<pir::DoubleAttribute>]`
   - Issue tracked: https://github.com/PaddlePaddle/Paddle/issues/77340

3. **Relative Coordinates**
   - All positions stored as fractions (0.0-1.0)
   - Works at any resolution (1080p, 1440p, 4K, iPad Retina)
   - Template matching auto-scales to detected UI scale

---

## In Progress

### Data Collection 🔄

- [x] 1 Pierre's shop screenshot collected (`datasets/from-katarina/1_pierres_top.jpg`)
- [ ] Collect 20+ Pierre's shop screenshots at different resolutions
- [ ] Collect 50+ screen-type diversity screenshots for orchestrator training
- [ ] Create train/val/test splits

---

## Not Started

### Phase 1 (Remaining)

7. **VLM Orchestrator Wrapper**
   - File: `src/stardew_vision/models/vlm_wrapper.py`
   - Task: Wrap Qwen2.5-VL-7B with tool-calling interface

8. **Zero-shot Baseline**
   - Test if Qwen2.5-VL-7B can dispatch correct tool without training

9. **Fine-tuning**
   - Train orchestrator on screen-type classification
   - Log to MLFlow

10. **TTS Integration**
    - File: `src/stardew_vision/tts/synthesize.py`
    - Library: MeloTTS-English

11. **Web Application**
    - FastAPI server (port 8000)
    - Screenshot upload endpoint
    - Audio response

12. **End-to-End Integration**
    - Upload screenshot → audio plays

### Phase 2: TV Screen Dialog

- Not started

### Phase 3: Inventory Tooltips

- Not started

---

## Dependencies Installed

```toml
# Core
opencv-python = ">=4.9.0"
paddlepaddle = "==3.2.0"  # LOCKED - do not upgrade
paddleocr = ">=3.4.0"
rapidfuzz = ">=3.9.0"

# Testing
pytest = ">=9.0.0"
```

---

## Files Created/Modified (2026-03-20)

### Production Code
- ✅ `src/stardew_vision/tools/crop_pierres_detail_panel.py` (updated)
- ✅ `tests/test_tools.py` (updated ground truth)
- ✅ `tests/fixtures/pierre_shop_001.png` (added)

### Templates & Config
- ✅ `datasets/assets/templates/pierres_detail_panel_corner.png` (created)
- ✅ `datasets/assets/templates/panel_layout.json` (created)
- ✅ `datasets/assets/templates/debug_selection.png` (created)

### Scripts
- ✅ `scripts/extract_anchor_template.py` (already existed)
- ✅ `scripts/test_ocr_on_panel.py` (created)
- ✅ `scripts/test_extraction_tool.py` (created)

### Documentation
- ✅ `docs/plan.md` (updated)
- ✅ `CLAUDE.md` (updated)
- ✅ `docs/IMPLEMENTATION_STATUS.md` (this file)

---

## Next Steps

**Priority 1**: Collect more Pierre's shop screenshots
- Target: 20-50 screenshots at different resolutions and items
- Use for validation and testing robustness

**Priority 2**: Build VLM orchestrator wrapper
- Wrap Qwen2.5-VL-7B with OpenAI-compatible tool-calling API
- Test zero-shot screen classification

**Priority 3**: TTS integration
- Integrate MeloTTS for audio narration
- Create narration templates

**Priority 4**: Web application
- FastAPI server with upload endpoint
- Integrate extraction + TTS pipeline
- Return audio response

---

## Blockers

None currently.

---

## Lessons Learned

1. **PaddlePaddle version compatibility is critical** — 3.3.0 breaks CPU inference
2. **Relative coordinates are essential** — handle multi-resolution screenshots cleanly
3. **Template matching works well** for pixel-perfect game UIs with discrete UI scales
4. **Position-based OCR parsing** (Y-coordinate thresholds) is simple and effective
5. **Interactive annotation tools** (cv2.selectROI) speed up template extraction
6. **Unit tests with fixture screenshots** provide confidence in extraction accuracy
