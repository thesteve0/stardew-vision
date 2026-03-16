# Overlay Collection Guide

---

## ✅ UPDATE (2026-03-06): Assets Already Extracted!

**Quality stars and font assets have been extracted directly from game files.**

- ✅ **Quality stars:** All 6 sprites extracted from `Cursors.xnb` (silver, gold, iridium at 100%/125% UI scales)
- ✅ **Font assets:** SmallFont.png + SmallFont.json extracted from `SmallFont.xnb`
- 📄 **See:** [datasets/assets/EXTRACTION_SUMMARY.md](../datasets/assets/EXTRACTION_SUMMARY.md) for complete details

**You do NOT need to manually collect these assets via screenshots.**

The guide below documents the original planned manual collection workflow. It is preserved for reference, but the extraction method (using game files) is faster, more accurate, and already complete.

---

## Purpose

This guide explains how to collect reference screenshots of **quality stars** and **quantity text** overlays from Stardew Valley. These overlays will be used in synthetic data generation to create realistic training images.

See [ADR-007](adr/007-overlay-detection-strategy.md) for the architectural rationale.

---

## Overview

In Stardew Valley, items in chests/inventory can have two types of overlays:

1. **Quantity text**: White number with black outline in bottom-right corner (when quantity > 1)
2. **Quality stars**: Small star icon in bottom-left corner indicating quality level

**What we need to collect:**
- Quality star sprites (silver, gold, iridium) at multiple UI scales
- Reference screenshots showing quantity text (numbers 2-999) for font matching
- Positioning/alignment measurements for overlay placement

---

## Directory Structure

```
datasets/assets/
├── quality_stars/           # Quality star sprites
│   ├── README.md           # Documentation and measurements
│   ├── silver_star_100.png # Silver star at 100% UI scale
│   ├── silver_star_125.png # Silver star at 125% UI scale
│   ├── gold_star_100.png
│   ├── gold_star_125.png
│   ├── iridium_star_100.png
│   └── iridium_star_125.png
│
├── quantity_overlays/       # Quantity text reference screenshots
│   ├── README.md           # Font documentation
│   ├── quantity_refs_100.png  # Numbers 2, 5, 10, 50, 99, 999 at 100% UI scale
│   ├── quantity_refs_125.png  # Same numbers at 125% UI scale
│   └── font_specs.md       # Font name, size, outline specs
│
└── overlay_examples/        # Combined examples for validation
    ├── both_overlays_100.png  # Item with both quantity + quality
    ├── both_overlays_125.png
    └── measurements.md     # Positioning data
```

---

## Collection Checklist

### Phase 1: Quality Stars (Priority 1 - Essential)

**Goal:** Extract or screenshot quality star sprites at common UI scales

- [ ] **Silver star sprites**
  - [ ] `silver_star_100.png` - Silver star at 100% UI scale
  - [ ] `silver_star_125.png` - Silver star at 125% UI scale

- [ ] **Gold star sprites**
  - [ ] `gold_star_100.png` - Gold star at 100% UI scale
  - [ ] `gold_star_125.png` - Gold star at 125% UI scale

- [ ] **Iridium star sprites**
  - [ ] `iridium_star_100.png` - Iridium star at 100% UI scale
  - [ ] `iridium_star_125.png` - Iridium star at 125% UI scale

**How to collect:**
1. Obtain items with different quality levels (silver/gold/iridium)
2. Place ONE quality item in an otherwise empty chest cell
3. Set UI scale in game settings to 100%
4. Take a closeup screenshot showing the cell with quality star clearly visible
5. Repeat at 125% UI scale
6. Crop the star sprite from screenshots (approximately 4×4 to 8×8 pixels depending on scale)

**Tips:**
- Use a dark background (empty chest cell) for easier star visibility
- Ensure the star is fully visible and not partially transparent
- Save as PNG to preserve transparency/alpha channel

### Phase 2: Quantity Text (Priority 1 - Essential)

**Goal:** Collect reference screenshots showing quantity numbers for font matching

- [ ] **Quantity text reference at 100% UI scale**
  - [ ] Numbers to capture: 2, 5, 10, 20, 50, 99, 100, 500, 999
  - [ ] Screenshot showing multiple stacked items with different quantities
  - [ ] Save as `quantity_refs_100.png`

- [ ] **Quantity text reference at 125% UI scale**
  - [ ] Same numbers at increased UI scale
  - [ ] Save as `quantity_refs_125.png`

**How to collect:**
1. Prepare items with varying stack sizes (2, 5, 10, 50, 99, 999)
2. Place them in adjacent chest cells
3. Take screenshot showing all quantities clearly
4. Document font characteristics:
   - Font name/type (likely pixel font or system font)
   - Font size in pixels
   - Text color (white #FFFFFF)
   - Outline/shadow color (black #000000)
   - Outline thickness

**Alternative method:**
If you have access to Stardew Valley game files:
- Extract font file from `Content/Fonts/` directory
- Document font name and size used for quantity rendering
- This is faster than screenshot-based font matching

### Phase 3: Positioning Measurements (Priority 2 - Recommended)

**Goal:** Document exact positioning rules for overlays

- [ ] **Quality star positioning**
  - [ ] Measure pixel offset from bottom-left corner of cell
  - [ ] Document horizontal offset (X pixels from left edge)
  - [ ] Document vertical offset (Y pixels from bottom edge)
  - [ ] Verify consistency across different UI scales

- [ ] **Quantity text positioning**
  - [ ] Measure pixel offset from bottom-right corner of cell
  - [ ] Document horizontal offset (X pixels from right edge)
  - [ ] Document vertical offset (Y pixels from bottom edge)
  - [ ] Verify text alignment (right-aligned, bottom-aligned, centered?)

**How to measure:**
1. Open reference screenshots in image editor (GIMP, Photoshop, etc.)
2. Identify cell boundaries (from UI frame measurements)
3. Measure distances from overlay elements to cell edges
4. Document in `datasets/assets/overlay_examples/measurements.md`

### Phase 4: Combined Examples (Priority 3 - Optional but Recommended)

**Goal:** Collect validation examples showing both overlays simultaneously

- [ ] **Both overlays present**
  - [ ] Item with quantity > 1 AND quality star (e.g., "5× silver-quality Copper Bar")
  - [ ] Screenshot at 100% UI scale
  - [ ] Screenshot at 125% UI scale

- [ ] **Overlay variations**
  - [ ] Quantity only (no quality star)
  - [ ] Quality only (quantity = 1, no number shown)
  - [ ] No overlays (quantity = 1, normal quality)

**Why this matters:**
These examples let you visually validate that synthetic data generation correctly composites overlays without visual artifacts (overlap, misalignment, incorrect layering order).

---

## Collection Workflow

### Step 1: In-Game Preparation

1. **Set up test items:**
   ```
   Silver quality items: Fish (easy to obtain silver quality)
   Gold quality items: Crops with fertilizer
   Iridium quality items: Use Stardew predictor or late-game items

   Stacked items:
   - Wood (easy to stack to 999)
   - Stone (easy to stack)
   - Fiber (easy to stack)
   ```

2. **Configure game settings:**
   - Set UI scale to 100% for first collection pass
   - Use 1920×1080 or higher resolution for clarity
   - Ensure good lighting (daytime, well-lit area)
   - No cursor visible in screenshots

3. **Prepare chest layout:**
   - Use an empty chest for clean backgrounds
   - Place quality items in isolated cells (surrounded by empty cells)
   - Place stacked items in separate section

### Step 2: Screenshot Collection

**For quality stars:**
```bash
# Screenshot naming convention:
silver_star_closeup_100.png   # Full screenshot at 100% UI scale
silver_star_closeup_125.png   # Full screenshot at 125% UI scale

# Location: Save to datasets/assets/quality_stars/raw/
```

**For quantity text:**
```bash
# Screenshot naming convention:
quantity_grid_100.png         # Multiple quantities visible at 100%
quantity_grid_125.png         # Same at 125%

# Location: Save to datasets/assets/quantity_overlays/raw/
```

**Screenshot commands:**
- **Steam**: F12 (auto-saves to Steam screenshot folder)
- **Windows**: Win+PrintScreen
- **Mac**: Cmd+Shift+3
- **Linux**: PrintScreen or Shift+PrintScreen

### Step 3: Post-Processing

1. **Crop quality star sprites:**
   - Open screenshots in image editor
   - Zoom in on quality star
   - Crop to minimal bounding box (e.g., 8×8 pixels at 100% scale)
   - Save as PNG with transparency: `silver_star_100.png`
   - Repeat for all quality levels and UI scales

2. **Annotate quantity screenshots:**
   - No cropping needed (keep full context)
   - Add measurement overlays if helpful
   - Document font characteristics in `font_specs.md`

3. **Document measurements:**
   - Open `datasets/assets/quality_stars/README.md`
   - Fill in positioning data
   - Document sprite dimensions
   - Note any scaling factors

### Step 4: Validation

**Quality stars validation:**
```bash
# Check dimensions
file datasets/assets/quality_stars/silver_star_100.png
# Expected output: PNG image data, 6 x 6 (or similar small dimensions)

# Visual inspection
# - Stars should be on transparent background
# - Colors should be distinct (silver=white, gold=yellow, iridium=purple)
# - No background artifacts or partial pixels
```

**Quantity text validation:**
```bash
# Visual inspection of reference screenshots:
# - All numbers clearly visible
# - White text with black outline
# - Positioned in bottom-right of cells
# - Consistent font across all numbers
```

### Step 5: Documentation

Create README files in each directory documenting:

**`datasets/assets/quality_stars/README.md`:**
```markdown
# Quality Star Sprites

## Collection Info
- Game version: 1.6.x
- UI scale: 100%, 125%
- Platform: PC/Mac/Linux
- Date collected: YYYY-MM-DD

## Sprite Dimensions
| Quality   | 100% UI Scale | 125% UI Scale |
|-----------|---------------|---------------|
| Silver    | 6×6 px        | 8×8 px        |
| Gold      | 6×6 px        | 8×8 px        |
| Iridium   | 6×6 px        | 8×8 px        |

## Color Values (approximate)
| Quality   | Primary Color | Notes |
|-----------|---------------|-------|
| Silver    | #E0E0E0       | Bright white/silver |
| Gold      | #FFD700       | Yellow/gold         |
| Iridium   | #9966FF       | Purple/violet       |

## Positioning Rules
- **Anchor point:** Bottom-left corner of cell
- **Horizontal offset:** 2 pixels from left edge
- **Vertical offset:** 2 pixels from bottom edge
- **Layering:** Rendered above base sprite, below quantity text
```

**`datasets/assets/quantity_overlays/font_specs.md`:**
```markdown
# Quantity Text Font Specifications

## Font Characteristics
- **Font name:** [To be determined from game files or matching]
- **Font size:** ~8px at 100% UI scale, ~10px at 125%
- **Style:** Pixel font or small system font
- **Color:** White (#FFFFFF)
- **Outline:** 1px black (#000000) outline/shadow
- **Anti-aliasing:** None (crisp pixel rendering)

## Positioning Rules
- **Anchor point:** Bottom-right corner of cell
- **Horizontal offset:** 2 pixels from right edge
- **Vertical offset:** 2 pixels from bottom edge
- **Alignment:** Right-aligned text
- **Layering:** Rendered above all other elements (topmost)

## Number Rendering
- **Range:** 2-999 (quantity 1 = no text shown)
- **Format:** Plain integer, no comma separators
- **Width:** Variable (2 = narrow, 999 = wide)
```

---

## Expected Output

After completing this guide, you should have:

```
datasets/assets/
├── quality_stars/
│   ├── README.md           ✅ Sprite dimensions, colors, positioning
│   ├── silver_star_100.png ✅ 6×6 px PNG with transparency
│   ├── silver_star_125.png ✅ 8×8 px PNG with transparency
│   ├── gold_star_100.png   ✅
│   ├── gold_star_125.png   ✅
│   ├── iridium_star_100.png ✅
│   └── iridium_star_125.png ✅
│
├── quantity_overlays/
│   ├── README.md           ✅ Collection info
│   ├── font_specs.md       ✅ Font name, size, styling
│   ├── quantity_refs_100.png ✅ Reference screenshot with numbers
│   └── quantity_refs_125.png ✅
│
└── overlay_examples/
    ├── measurements.md     ✅ Positioning data
    ├── both_overlays_100.png ✅ Validation example
    └── both_overlays_125.png ✅
```

---

## Integration with Synthetic Data Generation

Once overlays are collected, `scripts/generate_synthetic_data.py` will:

1. **Load quality star sprites** from `datasets/assets/quality_stars/`
2. **Render quantity text** using font specs from `quantity_overlays/font_specs.md`
3. **Composite overlays** onto base item sprites using positioning rules
4. **Generate diverse combinations** per ADR-007 distribution:
   - 30% no overlay
   - 25% quantity only
   - 20% quality only
   - 25% both overlays

---

## Troubleshooting

### "Quality stars are too small to crop cleanly"

**Solution:** Take screenshots at maximum resolution and maximum UI scale (150%), then scale down. This gives more pixels to work with.

**Alternative:** Extract quality star sprites from game files:
- Path: `Content/LooseSprites/Cursors.xnb` (may contain UI elements)
- Use unxnb tool to extract PNG
- Search community wikis for extracted sprite sheets

### "Font matching is difficult"

**Solution:** Instead of exact font matching, use a similar pixel font:
- Try "PressStart2P" (free pixel font)
- Try "Silkscreen" (free pixel font)
- Adjust size until visual appearance matches reference screenshots
- Document font choice in `font_specs.md`

### "Positioning varies across UI scales"

**Solution:** Document positioning as **relative offsets** (percentage of cell size) rather than absolute pixels:
```
Quality star: 3% from left edge, 3% from bottom edge
Quantity text: 5% from right edge, 3% from bottom edge
```
This scales naturally with UI scale changes.

### "Can't obtain iridium quality items easily"

**Solution:** Use Stardew Valley save editor or predictor tool to add iridium items to your inventory for screenshot purposes. This is purely for asset collection, not gameplay.

---

## Success Criteria

**Minimum viable:**
- ✅ 6 quality star sprites (silver/gold/iridium at 100% and 125%)
- ✅ Font specifications documented
- ✅ Basic positioning rules documented

**Recommended:**
- ✅ Quantity text reference screenshots at 2+ UI scales
- ✅ Detailed positioning measurements
- ✅ Combined overlay validation examples

**Complete:**
- ✅ All sprites at 3+ UI scales (75%, 100%, 125%)
- ✅ Exact font match or acceptable substitute identified
- ✅ Pixel-perfect positioning measurements
- ✅ Comprehensive validation examples

---

## Next Steps

1. **Collect overlays** using this guide
2. **Document specifications** in README files
3. **Validate sprite quality** (transparency, dimensions, colors)
4. **Proceed to synthetic data generation** using collected assets
5. **Visual comparison test:** Compare synthetic images to real screenshots

---

## References

- [ADR-007](adr/007-overlay-detection-strategy.md) - Overlay detection strategy
- [Data Collection Plan](data-collection-plan.md) - Overall data strategy (Phase A, Phase B)
- [UI Screenshot Collection](ui-screenshot-collection.md) - UI frame collection (complementary)
- [Plan](plan.md) - Week 1 implementation timeline

---

**Status:** Ready for use
**Next action:** User should launch Stardew Valley and collect quality star/quantity overlay assets
**Estimated time:** 30-60 minutes for complete collection
