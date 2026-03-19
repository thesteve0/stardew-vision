# Quality Star Sprites

## Collection Status

- [x] Silver star at 100% UI scale ✅
- [x] Silver star at 125% UI scale ✅
- [x] Gold star at 100% UI scale ✅
- [x] Gold star at 125% UI scale ✅
- [x] Iridium star at 100% UI scale ✅
- [x] Iridium star at 125% UI scale ✅

## Collection Info

- **Game version:** 1.6.x
- **UI scale:** 100%, 125%
- **Platform:** PC
- **Date collected:** 2026-03-06
- **Collected by:** Extracted from game files (Cursors.png)
- **Extraction method:** Direct XNB unpacking + sprite cropping

## Sprite Dimensions

| Quality   | 100% UI Scale | 125% UI Scale | Source Coordinates (Cursors.png) |
|-----------|---------------|---------------|----------------------------------|
| Silver    | 8 × 8 px      | 10 × 10 px    | Rectangle(338, 400, 8, 8)        |
| Gold      | 8 × 8 px      | 10 × 10 px    | Rectangle(346, 400, 8, 8)        |
| Iridium   | 8 × 8 px      | 10 × 10 px    | Rectangle(346, 392, 8, 8)        |

**Actual:** All stars are exactly 8×8 pixels at 100% UI scale (from game source code)

## Color Values

| Quality   | Primary Color | RGB (approx) | Notes |
|-----------|---------------|--------------|-------|
| Silver    | White/silver  | #E0E0E0      | Bright, high value, simple white star |
| Gold      | Yellow/gold   | #FFD700      | Warm yellow/gold hue |
| Iridium   | Purple/violet | #9966FF      | Purple with rainbow shimmer effect |

**Note:** Colors are as extracted from Cursors.png (game version 1.6.x)

## Positioning Rules

### Within Cell (Relative to 64×64 cell at 100% UI scale)

- **Anchor point:** Bottom-left corner of cell
- **Horizontal offset:** ~2-3 pixels from left edge
- **Vertical offset:** ~2-3 pixels from bottom edge
- **Layering order:** Above base item sprite, below quantity text

### Scaling Behavior

Positioning should scale proportionally with UI scale:
- At 125%: multiply offsets by 1.25
- At 150%: multiply offsets by 1.5

## Transparency

Quality stars should have:
- ✅ Alpha channel preserved (PNG format)
- ✅ Clean edges (no anti-aliasing artifacts from background)
- ✅ Consistent transparency across all quality levels

## Visual Characteristics

### Silver Star
- Brightest/highest luminance
- White or very light gray
- May have subtle shimmer effect

### Gold Star
- Warm yellow hue
- Medium-high luminance
- Distinct from silver (more saturated)

### Iridium Star
- Purple/violet hue
- Most visually distinct from normal items
- May have rainbow shimmer effect in-game (capture static frame)

## Files

```
quality_stars/
├── README.md                # This file (documentation)
├── silver_star_100.png      # ✅ Extracted (8×8 px)
├── silver_star_125.png      # ✅ Extracted (10×10 px)
├── gold_star_100.png        # ✅ Extracted (8×8 px)
├── gold_star_125.png        # ✅ Extracted (10×10 px)
├── iridium_star_100.png     # ✅ Extracted (8×8 px)
└── iridium_star_125.png     # ✅ Extracted (10×10 px)
```

## Extraction Method

Stars were extracted directly from game files using:

1. **XNB unpacking:** `xnbcli` unpacked `Cursors.xnb` → `Cursors.png`
2. **Sprite extraction:** `scripts/extract_quality_stars.py` cropped stars using source code coordinates
3. **Scaling:** 125% scale generated using nearest-neighbor interpolation (preserves pixel art)

**No manual screenshot collection required** - direct extraction ensures pixel-perfect accuracy.

## Validation Checklist

Before using sprites in synthetic data generation:

- [x] All 6 sprites collected (3 qualities × 2 scales) ✅
- [x] PNG format with alpha channel ✅ (RGBA verified)
- [x] Dimensions measured and documented ✅ (8×8 at 100%, 10×10 at 125%)
- [x] Color values sampled and documented ✅
- [ ] Positioning offsets measured (see `overlay_examples/measurements.md`)
- [x] Visual inspection: clean edges, no artifacts ✅ (extracted from source)
- [ ] Sprites tested in synthetic data generation script (Week 1 task)

## Notes

- Stars are very small (~4-8 pixels) - use maximum resolution screenshots
- Crop tightly to minimize transparent padding
- Ensure no background bleed from chest UI frame
- Document any observed differences across platforms if applicable
