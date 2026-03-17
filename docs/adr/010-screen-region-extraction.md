# ADR-010: Screen Region Extraction Layer

**Date**: 2026-03-17
**Status**: Accepted
**Deciders**: Project team

## Context

ADR-009 defines an agent/tool-calling pipeline where the orchestrator VLM dispatches tool calls to specialized extraction agents. This ADR defines the implementation of those extraction agents: how to locate the correct UI region within a screenshot and extract structured text from it.

The extraction layer must:
- Run entirely on CPU (GPU reserved for orchestrator VLM)
- Handle screenshots at multiple resolutions (1080p, 1440p, 4K, iPad Retina)
- Reliably locate the target UI panel within a full-screen screenshot
- Extract specific text fields (name, description, price, quantity, total) with high accuracy
- Return structured JSON matching the per-screen-type schema in `configs/output_schema.json`

## Decision

**OpenCV template matching** for UI region location; **EasyOCR** for text extraction; both CPU-only.

### Approach

#### Step 1: Region Location via OpenCV Template Matching

Each screen type has a known visual anchor — a UI chrome element (border, icon, or label) that appears at a fixed position relative to the panel content. Template matching finds this anchor at any resolution and computes the crop coordinates.

**Pierre's shop detail panel**:
- Anchor: the shop panel's right-column frame (the wood-grain border that surrounds the item detail area)
- Template: a small crop of the panel corner, stored at `datasets/assets/templates/pierres_detail_panel_corner.png`
- OpenCV `matchTemplate` with `TM_CCOEFF_NORMED`; match threshold 0.85
- Panel coordinates relative to match: fixed offsets (measured once at 100% UI scale, scaled by detected match scale)

**Resolution handling**: Stardew Valley UI scales proportionally with the game window. Template matching finds the panel at any resolution because it searches the full image for the template pattern. The match location gives the top-left corner; panel dimensions scale proportionally to the UI scale detected from match size.

#### Step 2: Text Extraction via EasyOCR

After cropping the panel region, EasyOCR runs on the cropped image to extract text.

**Why EasyOCR over Tesseract**:
- Better accuracy on small, pixel-rendered game text (Stardew Valley uses a bitmap font)
- Simpler API for bounding-box-aware extraction (field positions within panel are known)
- No preprocessing pipeline needed (Tesseract often requires binarization + deskew for clean results)
- CPU inference is fast enough (< 500ms per crop on a modern CPU)

**Field extraction strategy for Pierre's shop panel**:

The panel layout is consistent:
```
[Item Name]           <- top of panel, large text
[Item Description]    <- multi-line text below name
[Price: G NNN]        <- price line
[Quantity: NN]        <- quantity selector
[Total: G NNN]        <- total cost line
```

EasyOCR returns bounding boxes + text for all detected text regions. A lightweight parser maps bounding box Y-positions to field slots (name at top, price/quantity/total in lower third).

**Parsed output schema** (Pierre's shop):
```json
{
  "name": "Parsnip",
  "description": "A spring tuber closely related to the carrot.",
  "price_per_unit": 20,
  "quantity_selected": 5,
  "total_cost": 100
}
```

### Implementation Files

- `src/stardew_vision/tools/crop_pierres_detail_panel.py` — OpenCV crop + EasyOCR + parser
- `src/stardew_vision/tools/crop_tv_dialog.py` — Phase 2
- `src/stardew_vision/tools/crop_inventory_tooltip.py` — Phase 3
- `src/stardew_vision/tools/__init__.py` — tool registry
- `datasets/assets/templates/` — anchor templates for each screen type

### Validation Strategy

Each extraction tool has a unit test:
- Input: a known Pierre's shop screenshot (stored in `tests/fixtures/`)
- Expected output: the ground truth extraction for that screenshot
- Pass criterion: all fields match (exact for integers, fuzzy >= 90 for strings)

## Alternatives Considered

| Option | Why not selected |
|--------|-----------------|
| **Hardcoded pixel coordinates** | Fails at different resolutions; brittle to any UI change |
| **VLM for text extraction** | GPU-intensive for a task that OCR handles deterministically; slower iteration |
| **Tesseract OCR** | Requires more preprocessing for game fonts; EasyOCR handles bitmap fonts better out-of-the-box |
| **ML-based object detection for regions** | Over-engineered for pixel-perfect game UI; template matching is simpler and more reliable |
| **pytesseract + PIL** | Valid alternative but EasyOCR's bounding box API better fits the field-slotting strategy |

## Why OpenCV Template Matching Works Here

Stardew Valley's UI is **pixel-perfect and consistent**:
- All UI elements are rendered from the same asset files (no antialiasing, no font variation)
- UI scale is a discrete multiplier (75%, 100%, 125%, 150%) — not arbitrary
- Panel layouts are fixed within a game version (no dynamic reflow)

These properties make template matching highly reliable. The main failure mode is a UI skin change from a game update or mod — acceptable for MVP (targeting vanilla Stardew Valley 1.6).

## Consequences

**Gets easier**:
- No GPU needed for extraction — keeps GPU free for orchestrator
- Deterministic and testable in isolation (no model inference variance)
- Fast iteration: changing the parser is a code edit, not a retraining run
- Easy to add new screen types: write one new tool function + anchor template

**Gets harder**:
- Template matching is brittle to UI skin changes (game updates, mods)
- Must measure and store anchor templates for each screen type manually
- Resolution handling requires careful scaling logic
- EasyOCR may struggle with very small text at low UI scales

**Risks**:

| Risk | Likelihood | Mitigation |
|------|-----------|-----------|
| Game update changes panel layout | Low (Stardew updates are infrequent) | Document game version assumption; update templates on update |
| Template match fails at unusual resolution | Low | Test at 1080p, 1440p, 4K, iPad Retina before release |
| EasyOCR misreads price (e.g., "20G" as "206") | Medium | Post-process: strip non-numeric characters from price fields |
| Panel partially off-screen (small window) | Low | Validate crop bounds; return error if panel not fully visible |

**We are committing to**:
- OpenCV template matching as the region location strategy for MVP
- EasyOCR as the OCR engine
- Pierre's shop detail panel as the first extraction target
- Storing anchor templates in `datasets/assets/templates/` (committed to git — small PNG files)
- Unit tests for each extraction tool with fixture screenshots

## Target Regions: Pierre's Shop Detail Panel

The MVP reads the **right-column detail panel** visible when a player hovers over or selects an item for purchase at Pierre's General Store.

Panel contents read aloud:
1. Item name (e.g., "Parsnip Seeds")
2. Item description (e.g., "Plant these in the spring...")
3. Price per unit (e.g., "20 gold each")
4. Quantity selected (e.g., "5 selected")
5. Total cost (e.g., "100 gold total")

Narration template:
```
You are looking at [name]. [description]. It costs [price_per_unit] gold each.
You have selected [quantity_selected]. Total cost: [total_cost] gold.
```

## References

- [ADR-009](009-agent-tool-calling-architecture.md): Agent pipeline — this ADR implements the extraction agents
- [ADR-003](003-tts-selection.md): TTS — narration template output goes to MeloTTS
- [ADR-005](005-serving-strategy.md): Serving — extraction agents called as local library functions, not via API
- `configs/output_schema.json`: Per-screen-type JSON schemas
