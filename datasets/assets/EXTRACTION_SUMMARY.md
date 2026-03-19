# Asset Extraction Summary

**Date:** 2026-03-06
**Status:** ✅ Complete - Quality stars and font assets extracted from game files

## What Was Extracted

### Quality Stars (from Cursors.xnb)

All quality star sprites extracted from the game's `LooseSprites/Cursors.xnb` file:

| Asset | Source Coordinates | Size | File |
|-------|-------------------|------|------|
| Silver star (100%) | Rectangle(338, 400, 8, 8) | 8×8 px | `quality_stars/silver_star_100.png` |
| Silver star (125%) | Scaled from above | 10×10 px | `quality_stars/silver_star_125.png` |
| Gold star (100%) | Rectangle(346, 400, 8, 8) | 8×8 px | `quality_stars/gold_star_100.png` |
| Gold star (125%) | Scaled from above | 10×10 px | `quality_stars/gold_star_125.png` |
| Iridium star (100%) | Rectangle(346, 392, 8, 8) | 8×8 px | `quality_stars/iridium_star_100.png` |
| Iridium star (125%) | Scaled from above | 10×10 px | `quality_stars/iridium_star_125.png` |

**Features:**
- ✅ RGBA format (transparency preserved)
- ✅ Pixel-perfect extraction from game source
- ✅ Two UI scales supported (100%, 125%)
- ✅ Ready for use in synthetic data generation

### Font Assets (from SmallFont.xnb)

Stardew Valley's native font used for quantity text overlays:

| Asset | Description | Size | File |
|-------|-------------|------|------|
| Font sprite atlas | Bitmap font texture with all characters | 256×260 px | `quantity_overlays/SmallFont.png` |
| Glyph coordinate data | JSON mapping characters to sprite positions | 104 KB | `quantity_overlays/SmallFont.json` |

**Features:**
- ✅ SpriteFont format (Microsoft XNA Framework)
- ✅ Full ASCII character set + special characters
- ✅ Variable-width (proportional) font
- ✅ Glyph coordinate data for accurate rendering

## Extraction Method

### Tools Used

1. **xnbcli** (Node.js): XNB file unpacker
   - Repository: https://github.com/LeonBlade/xnbcli
   - Unpacked `.xnb` → `.png` + `.json`

2. **Custom Python script** (`scripts/extract_quality_stars.py`):
   - Cropped quality stars from Cursors.png using game source code coordinates
   - Generated 125% scaled versions using nearest-neighbor interpolation

### File Locations

```
datasets/assets/
├── game_files/
│   ├── Cursors.xnb                    # Original game file
│   ├── SmallFont.xnb                  # Original game file
│   └── unpacked/
│       ├── Cursors.png                # Unpacked sprite sheet (704×2256)
│       ├── Cursors.json               # Metadata
│       ├── SmallFont.png              # Unpacked font atlas (256×260)
│       └── SmallFont.json             # Glyph coordinates
│
├── quality_stars/
│   ├── README.md                      # ✅ Updated with extraction info
│   ├── silver_star_100.png            # ✅ Extracted (8×8)
│   ├── silver_star_125.png            # ✅ Extracted (10×10)
│   ├── gold_star_100.png              # ✅ Extracted (8×8)
│   ├── gold_star_125.png              # ✅ Extracted (10×10)
│   ├── iridium_star_100.png           # ✅ Extracted (8×8)
│   └── iridium_star_125.png           # ✅ Extracted (10×10)
│
└── quantity_overlays/
    ├── README.md                      # ✅ Updated with font info
    ├── SmallFont.png                  # ✅ Copied from unpacked/
    └── SmallFont.json                 # ✅ Copied from unpacked/
```

## Next Steps

### Remaining Data Collection Tasks

Per `docs/data-collection-plan.md` Phase A:

- [ ] Collect UI frame assets (chest background grids)
  - Empty chest UI frames at multiple UI scales
  - Dual-grid screenshots (chest + inventory)
  - See: `docs/ui-screenshot-collection.md`

- [ ] Document positioning measurements
  - Quality star positioning within cell (bottom-left offset)
  - Quantity text positioning within cell (bottom-right offset)
  - See: `datasets/assets/overlay_examples/measurements.md`

### Synthetic Data Generation (Week 1, Phase B)

With quality stars and fonts extracted, you can now implement:

1. **`scripts/generate_synthetic_data.py`**
   - Load item sprites from `sprites_game/`
   - Composite quality stars from `quality_stars/`
   - Render quantity text using `SmallFont.png` + `SmallFont.json`
   - Generate diverse overlay combinations per ADR-007:
     - 30% no overlay
     - 25% quantity only
     - 20% quality only
     - 25% both overlays

2. **Font Rendering Implementation**

Instead of using a substitute font, use the extracted SmallFont directly:

```python
# Pseudo-code
def render_quantity_text(quantity, ui_scale=100):
    atlas = load_image("SmallFont.png")
    glyphs = load_json("SmallFont.json")
    
    # Look up glyph coordinates for each digit in str(quantity)
    # Composite glyphs from atlas
    # Add black outline (render offset or stroke filter)
    # Scale based on ui_scale
    
    return rendered_text_image
```

## References

- **ADR-007:** Overlay detection strategy
- **Data collection plan:** `docs/data-collection-plan.md`
- **Overlay collection guide:** `docs/overlay-collection-guide.md`
- **XNB extraction tool:** https://github.com/LeonBlade/xnbcli
- **Quality star coordinates source:** Stardew Valley game source code (Game1.mouseCursors rendering)

## Success Criteria

✅ All quality stars extracted (6 files)
✅ Font assets extracted (2 files)
✅ Documentation updated (READMEs)
✅ Ready for synthetic data generation implementation

**Estimated time saved:** ~1-2 hours vs. manual screenshot collection and cropping
