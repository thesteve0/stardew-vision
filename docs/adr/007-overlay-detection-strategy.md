# ADR-007: Overlay Detection Strategy for Stack Counts and Quality Indicators

**Date**: 2026-03-05
**Status**: Accepted
**Deciders**: Project team

## Context

Stardew Valley dynamically overlays visual indicators on item sprites that significantly alter the pixel data:

1. **Stack count overlay**: White numerical digit in the bottom-right quadrant when a player has multiple instances of an item
2. **Quality star overlay**: Distinct star icon in the bottom-left quadrant indicating item quality (Silver, Gold, or Iridium)

These overlays obscure portions of the original 16×16 pixel sprite, which creates two challenges:

1. **Item identification**: The overlays alter the visual appearance, potentially causing false positives/negatives if relying on pure template matching
2. **Information extraction**: The overlays themselves convey critical information (stack size, quality level) that must be detected and communicated to visually impaired users

## Decision

**Extend the VLM's structured output schema to include quality detection**, leveraging the VLM's natural ability to understand visual context and overlays.

### Updated Output Schema

```json
{
  "cells": [
    {
      "row": 0,
      "col": 0,
      "item": "Copper Bar",
      "quantity": 5,
      "quality": "normal"
    },
    {
      "row": 0,
      "col": 1,
      "item": "Ancient Sword",
      "quantity": 1,
      "quality": "gold"
    },
    {
      "row": 0,
      "col": 2,
      "item": "empty",
      "quantity": 0,
      "quality": null
    }
  ]
}
```

**Quality values**: `"normal"` (no star), `"silver"`, `"gold"`, `"iridium"`, or `null` (for empty cells)

### Updated Annotation Schema

Add `quality` field to the annotation JSONL:

```json
{
  "row": 0,
  "col": 0,
  "occupied": true,
  "item_id": 334,
  "item_name": "Copper Bar",
  "item_category": "Resources",
  "quantity": 5,
  "quality": "normal"
}
```

### Synthetic Data Generation Requirements

`scripts/generate_synthetic_data.py` must include overlay generation:

1. **Quantity overlay**: White text with black outline, bottom-right positioning, matching in-game font
2. **Quality star overlay**: Star sprites (silver/gold/iridium variants), bottom-left positioning
3. **Combination scenarios**: Generate diverse examples:
   - Items with no overlay (quantity=1, normal quality)
   - Quantity only (e.g., "Wood ×20, normal quality")
   - Quality only (e.g., "Ancient Sword ×1, gold quality")
   - Both overlays (e.g., "Copper Bar ×5, silver quality")

**Target distribution** (of 500 synthetic images):
- 30% no overlay
- 25% quantity only (range 2-999)
- 20% quality only (distributed across silver/gold/iridium)
- 25% both overlays

### VLM Prompting Strategy

System prompt must explicitly instruct the VLM to:
1. Identify the base item despite overlays
2. Detect and report stack count from bottom-right numerical overlay
3. Detect and report quality from bottom-left star overlay
4. Default to `quantity: 1` if no number visible
5. Default to `quality: "normal"` if no star visible

Example prompt:
```
Analyze this Stardew Valley loot box screenshot. For each cell:
- Identify the item name (ignore overlays obscuring the sprite)
- Report the stack count (white number in bottom-right; default to 1 if none)
- Report the quality (star in bottom-left: no star = "normal", silver/gold/iridium star = that quality)
Output valid JSON matching the schema.
```

### Evaluation Metrics Update

Add **Quality Accuracy** metric:

| Metric | Description | MVP Target |
|--------|-------------|-----------|
| Quality Accuracy | % of occupied cells with correct quality identification | ≥ 70% |

**Rationale for 70% target**: Quality stars are smaller visual features than the base sprite and may be harder to distinguish (especially silver vs. gold). This is lower than quantity accuracy (75%) to account for the fine-grained visual discrimination required.

## Alternatives Considered

| Option | Why not selected |
|--------|------------------|
| **Template matching for overlays** | Fragile to resolution changes, font rendering differences across platforms (PC/Switch/iPad), compression artifacts. VLMs handle this naturally. |
| **Separate classifier for quality** | Adds complexity; VLMs can detect overlays and base item in a single pass. |
| **Ignore quality, report quantity only** | Quality is important information for players (Iridium items are significantly more valuable); omitting it degrades the accessibility tool's usefulness. |
| **Post-process detection (crop overlay regions)** | Requires precise cell alignment; fails if screenshot is scaled or cropped. VLMs are robust to these variations. |

## Consequences

**Gets easier**:
- VLMs naturally handle overlays better than template matching — this validates the VLM choice in ADR-001
- Structured output (ADR-002) makes it easy to add the `quality` field without changing the architecture
- Synthetic data generation provides perfect ground truth for both quantity and quality overlays
- Debugging is straightforward (can inspect JSON to see if quantity/quality detection failed independently)

**Gets harder**:
- Synthetic data generation script becomes more complex (must render overlays authentically)
- Annotation of real screenshots requires human reviewers to identify quality (may need to zoom in on small star icons)
- Evaluation surface area increases (now tracking 3 attributes per cell: item, quantity, quality)
- SmolVLM2's 81-token image compression may struggle with fine-grained quality star detection — this is a testable hypothesis

**Risks**:
- **Quality stars are small** (roughly 4×4 pixels) — VLMs may struggle, especially SmolVLM2 with aggressive compression
- **Silver vs. gold star distinction** is subtle (both are bright stars, differentiated mainly by hue)
- If quality accuracy is below 70% on real screenshots, may need to add a fallback (e.g., "quality unclear" option)

**We are committing to**:
- Rendering authentic overlays in synthetic data (font, positioning, transparency matching in-game appearance)
- Updating the VLM system prompt to explicitly request quality detection
- Tracking quality accuracy as a first-class metric alongside item and quantity accuracy
- Testing whether SmolVLM2's compression loses quality star detail (if so, this becomes a key differentiator vs. Qwen2.5-VL in the talk)

## Implementation Checklist

- [x] Update `configs/output_schema.json` to include `quality` field ✅
- [x] Update annotation schema in `docs/data-collection-plan.md` ✅
- [x] Add quality star sprites to `datasets/assets/` ✅ (extracted from game files - see [Asset Extraction Summary](../../datasets/assets/EXTRACTION_SUMMARY.md))
- [x] Extract quantity text font assets ✅ (SmallFont.png + SmallFont.json from game files)
- [ ] Update `scripts/generate_synthetic_data.py` to render quality stars and quantity text
- [ ] Update VLM system prompt in `src/stardew_vision/models/vlm_wrapper.py`
- [ ] Add Quality Accuracy metric to `src/stardew_vision/models/evaluate.py`
- [x] Update evaluation rubric in `docs/plan.md` with the new metric ✅
- [ ] Update description template in webapp to narrate quality (e.g., "gold-quality Ancient Sword")
- [ ] Test both VLMs on quality detection; document SmolVLM2 performance

## Asset Extraction Details

Quality stars and font assets have been extracted directly from Stardew Valley game files:

**Quality Stars:**
- Source: `Content/LooseSprites/Cursors.xnb` → `Cursors.png`
- Coordinates: Silver (338,400), Gold (346,400), Iridium (346,392)
- Size: 8×8 pixels at 100% UI scale
- Location: `datasets/assets/quality_stars/`
- Extraction script: `scripts/extract_quality_stars.py`

**Quantity Text Font:**
- Source: `Content/Fonts/SmallFont.xnb` → `SmallFont.png`
- Format: SpriteFont bitmap font atlas (256×260 px)
- Includes: Glyph coordinate data (`SmallFont.json`)
- Location: `datasets/assets/quantity_overlays/`

See [datasets/assets/EXTRACTION_SUMMARY.md](../../datasets/assets/EXTRACTION_SUMMARY.md) for complete extraction details and next steps.

## References

- [ADR-001](001-vlm-selection.md): VLM selection — overlays validate the choice of VLMs over template matching
- [ADR-002](002-vlm-role-architecture.md): Structured output architecture — flexible enough to add quality field
- [Asset Extraction Summary](../../datasets/assets/EXTRACTION_SUMMARY.md): Quality stars and font extraction from game files (2026-03-06)
- [Overlay Collection Guide](../overlay-collection-guide.md): Originally planned manual collection workflow (superseded by direct extraction)
- [Data Collection Plan](../data-collection-plan.md): Phase A asset acquisition status
