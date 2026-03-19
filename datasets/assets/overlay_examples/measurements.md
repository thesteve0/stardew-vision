# Overlay Positioning Measurements

## Purpose

This document records precise positioning measurements for quality stars and quantity text overlays within Stardew Valley chest cells.

## Measurement Approach

Measurements are taken from:
1. Reference screenshots at known UI scales (100%, 125%)
2. Empty chest cells (to identify cell boundaries)
3. Cells with single overlays (quality only or quantity only)
4. Cells with both overlays (to verify no overlap/interference)

## Cell Dimensions

First, establish the base cell size at 100% UI scale:

| UI Scale | Cell Width | Cell Height | Inner Margin | Notes |
|----------|------------|-------------|--------------|-------|
| 100%     | ? px       | ? px        | ? px         | To be measured |
| 125%     | ? px       | ? px        | ? px         | Should be 1.25× of 100% |

**Measurement method:**
1. Open empty chest screenshot in image editor
2. Identify cell boundaries (grid lines or empty cell backgrounds)
3. Measure width and height of a single cell
4. Measure inner margin (padding between cell border and item sprite area)

## Quality Star Positioning

### Bottom-Left Anchor

Quality stars are positioned in the bottom-left quadrant of the cell.

| UI Scale | Horizontal Offset (from left) | Vertical Offset (from bottom) | Star Size |
|----------|-------------------------------|------------------------------|-----------|
| 100%     | ? px                          | ? px                         | ? × ? px  |
| 125%     | ? px                          | ? px                         | ? × ? px  |

**Measurement method:**
1. Open screenshot with quality star visible
2. Identify cell boundaries
3. Measure distance from left edge of cell to left edge of star
4. Measure distance from bottom edge of cell to bottom edge of star
5. Measure star sprite dimensions

### Relative Positioning (percentage of cell size)

Convert absolute pixels to percentages for scalability:

```
Horizontal offset (%) = (horizontal_px / cell_width) × 100
Vertical offset (%) = (vertical_px / cell_height) × 100
```

| UI Scale | H Offset (%) | V Offset (%) | Notes |
|----------|--------------|--------------|-------|
| 100%     | ? %          | ? %          | To be calculated |
| 125%     | ? %          | ? %          | Should match 100% if scaling is proportional |

**Expected:** Percentages should be consistent across UI scales if positioning scales proportionally.

## Quantity Text Positioning

### Bottom-Right Anchor

Quantity text is positioned in the bottom-right quadrant of the cell.

| UI Scale | Horizontal Offset (from right) | Vertical Offset (from bottom) | Text Height |
|----------|--------------------------------|-----------------------------|-------------|
| 100%     | ? px                           | ? px                        | ? px        |
| 125%     | ? px                           | ? px                        | ? px        |

**Measurement method:**
1. Open screenshot with quantity text visible
2. Identify cell boundaries
3. Measure distance from right edge of cell to right edge of text
4. Measure distance from bottom edge of cell to bottom edge of text (baseline)
5. Measure text height (from baseline to top of tallest character)

### Text Width Variation

Quantity text is right-aligned, so width varies by number of digits:

| Quantity | Digits | Text Width (100%) | Text Width (125%) | Notes |
|----------|--------|-------------------|-------------------|-------|
| 2        | 1      | ? px              | ? px              | Narrowest |
| 10       | 2      | ? px              | ? px              | Common case |
| 99       | 2      | ? px              | ? px              | Max 2-digit |
| 100      | 3      | ? px              | ? px              | Min 3-digit |
| 999      | 3      | ? px              | ? px              | Widest |

### Relative Positioning (percentage of cell size)

| UI Scale | H Offset (%) | V Offset (%) | Notes |
|----------|--------------|--------------|-------|
| 100%     | ? %          | ? %          | To be calculated |
| 125%     | ? %          | ? %          | Should match 100% if proportional |

## Overlay Interaction

### When Both Overlays Present

Test cases with both quality star AND quantity text on the same item:

- [ ] Screenshot collected: Item with both overlays at 100%
- [ ] Screenshot collected: Item with both overlays at 125%

**Verify:**
- [ ] No visual overlap between star and text
- [ ] Both overlays fully visible
- [ ] Positioning remains consistent (not adjusted to avoid collision)

**Observed behavior:** [TBD - document after collection]

### Layering Order (Z-index)

From bottom to top:
1. Cell background (chest UI frame)
2. Item sprite (base 16×16 sprite, scaled)
3. Quality star (if present)
4. Quantity text (if present, topmost)

**Verification:** [TBD - confirm from screenshots]

## Example Measurements Template

### Example Cell #1: Quality Star Only

**Screenshot:** `overlay_examples/quality_only_100.png`
**Item:** Copper Bar (silver quality)
**UI Scale:** 100%

```
Cell boundaries:
  Top-left: (X, Y)
  Dimensions: W × H px

Quality star:
  Top-left: (X, Y)
  Dimensions: W × H px
  Offset from cell left: ? px
  Offset from cell bottom: ? px
  Relative offset: (?%, ?%)
```

### Example Cell #2: Quantity Only

**Screenshot:** `overlay_examples/quantity_only_100.png`
**Item:** Wood ×50
**UI Scale:** 100%

```
Cell boundaries:
  Top-left: (X, Y)
  Dimensions: W × H px

Quantity text:
  Text: "50"
  Top-left: (X, Y)
  Dimensions: W × H px
  Offset from cell right: ? px
  Offset from cell bottom: ? px
  Relative offset: (?%, ?%)
```

### Example Cell #3: Both Overlays

**Screenshot:** `overlay_examples/both_overlays_100.png`
**Item:** Copper Bar ×5 (silver quality)
**UI Scale:** 100%

```
Cell boundaries:
  Top-left: (X, Y)
  Dimensions: W × H px

Quality star:
  Offset from cell left: ? px
  Offset from cell bottom: ? px

Quantity text:
  Text: "5"
  Offset from cell right: ? px
  Offset from cell bottom: ? px

Overlap check:
  Distance between star right edge and text left edge: ? px
  Visual overlap: Yes / No
```

## Measurement Workflow

1. **Collect screenshots** (see [overlay-collection-guide.md](../../../docs/overlay-collection-guide.md))
2. **Open in image editor** (GIMP, Photoshop, Krita, etc.)
3. **Enable pixel grid** for precise measurements
4. **Identify cell boundaries** from empty cells or grid lines
5. **Measure absolute positions** in pixels
6. **Calculate relative positions** as percentages
7. **Document findings** in this file
8. **Verify consistency** across UI scales

## Tools for Measurement

Recommended image editors:
- **GIMP** (free): Use ruler tool, enable pixel grid
- **Photoshop**: Use guides and ruler tool
- **Krita** (free): Use measurement tool
- **Preview (Mac)**: Use inspector tool with dimensions

## Validation

Before using measurements in synthetic data generation:

- [ ] Measurements taken at 100% UI scale
- [ ] Measurements taken at 125% UI scale
- [ ] Proportional scaling verified (125% = 1.25× of 100%)
- [ ] Quality star positioning documented
- [ ] Quantity text positioning documented
- [ ] Both overlays tested for overlap
- [ ] Relative percentages calculated
- [ ] Layering order confirmed

## Notes

- Measurements are approximate — game rendering may vary slightly by platform
- Focus on consistency across UI scales rather than sub-pixel precision
- If measurements differ slightly between screenshots, use average values
- Document any unexpected behaviors (e.g., positioning changes based on item size)
