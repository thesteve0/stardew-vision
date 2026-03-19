# Quantity Text Overlay References

## Collection Status

- [x] Font sprite sheet extracted ✅ (SmallFont.png from game files)
- [x] Font glyph data extracted ✅ (SmallFont.json with character coordinates)
- [x] Font specifications documented ✅ (see below)
- [ ] Positioning measurements documented (see `overlay_examples/measurements.md`)

## Collection Info

- **Game version:** 1.6.x
- **UI scale:** 100% (reference)
- **Platform:** PC
- **Date collected:** 2026-03-06
- **Extraction method:** Direct XNB unpacking from SmallFont.xnb
- **Font type:** SpriteFont (bitmap font with glyph atlas)

## Required Numbers to Capture

Ensure the following quantities are visible in reference screenshots:

- [ ] 2 (single digit, small)
- [ ] 5
- [ ] 10 (two digits, common)
- [ ] 20
- [ ] 50
- [ ] 99 (two digits, max common)
- [ ] 100 (three digits, start)
- [ ] 500 (three digits, common)
- [ ] 999 (three digits, max)

**Why these specific numbers?**
- Cover all digit counts (1-digit, 2-digit, 3-digit)
- Include common values players encounter
- Test font rendering at different widths

## Font Specifications

### Extracted Game Font

- **Font name:** SmallFont (Stardew Valley native bitmap font)
- **Font type:** SpriteFont (Microsoft XNA Framework)
- **Font file:** `SmallFont.png` (256×260 px sprite atlas)
- **Glyph data:** `SmallFont.json` (character coordinates + metrics)
- **Font family:** Custom pixel font (game-specific)
- **Style:** Monochrome bitmap (pre-rendered)
- **Anti-aliasing:** None (crisp pixel rendering)

### Visual Characteristics

- **Base color:** White (#FFFFFF) in font atlas
- **Rendering:** Typically rendered with white fill + black outline in-game
- **Outline style:** 1px hard edge (drawn separately by game engine)
- **Pixel-aligned:** Yes (no subpixel rendering)

### Font Texture Details

- **Texture dimensions:** 256×260 pixels
- **Format:** RGBA PNG (includes transparency for glyph shapes)
- **Glyph count:** Full ASCII set + special characters
- **Character size:** Variable width (proportional font, not monospace)

### Usage in Synthetic Data Generation

Instead of finding a font substitute, **use the extracted SmallFont.png directly**:
- Load `SmallFont.png` as texture atlas
- Parse `SmallFont.json` for character → pixel coordinates mapping
- Render quantity text by compositing glyphs from atlas
- Add black outline via rendering offset trick or stroke filter

## Positioning Rules

### Within Cell (Relative to 64×64 cell at 100% UI scale)

- **Anchor point:** Bottom-right corner of cell
- **Horizontal offset:** ~2-5 pixels from right edge
- **Vertical offset:** ~2-3 pixels from bottom edge
- **Alignment:** Right-aligned text (numbers expand leftward)
- **Layering order:** Topmost layer (above item sprite and quality star)

### Scaling Behavior

Text size and positioning scale proportionally with UI scale:
- 100% UI scale: base font size (e.g., 8px)
- 125% UI scale: 1.25× font size (e.g., 10px)
- Offsets also scale proportionally

## Text Rendering Details

### Outline Implementation

The black outline ensures text is readable against any background color:

```
Method 1: Stroke/outline
- 1px black stroke around white fill

Method 2: Shadow copies
- Render black text at offsets (±1px in 4 or 8 directions)
- Render white text on top

Method 3: Exact game extraction
- Use game's text rendering engine if accessible
```

**Document actual method used:** [TBD]

### Width Variation

| Quantity | Expected Width (100%) | Notes |
|----------|----------------------|-------|
| 2        | ~6px                 | Single narrow digit |
| 10       | ~12px                | Two digits |
| 99       | ~12px                | Two wide digits |
| 100      | ~18px                | Three digits |
| 999      | ~18px                | Three wide digits |

**Actual measurements:** [TBD - measure from screenshots]

## Files

```
quantity_overlays/
├── README.md                # This file (documentation)
├── SmallFont.png            # ✅ Extracted font sprite atlas (256×260 px)
├── SmallFont.json           # ✅ Glyph coordinate data
└── font_specs.md            # Detailed font rendering specs (to be created if needed)
```

## Collection Instructions

See [docs/overlay-collection-guide.md](../../../docs/overlay-collection-guide.md) for detailed collection workflow.

**Quick steps:**
1. Prepare items with stack sizes: 2, 5, 10, 50, 99, 100, 500, 999
2. Place in adjacent chest cells
3. Set UI scale to 100%, take screenshot
4. Repeat at 125% UI scale
5. Document font characteristics
6. Measure positioning offsets

## Validation Checklist

Before using font in synthetic data generation:

- [x] Font sprite atlas extracted ✅ (SmallFont.png)
- [x] Glyph coordinate data extracted ✅ (SmallFont.json)
- [x] Font type identified ✅ (SpriteFont bitmap font)
- [x] Rendering method documented ✅ (glyph compositing from atlas)
- [ ] Positioning offsets measured (see `overlay_examples/measurements.md`)
- [ ] Outline rendering method implemented (black stroke + white fill)
- [ ] Test render matches in-game quantity text appearance
- [ ] Tested at multiple UI scales (100%, 125%)

## Implementation Notes

When implementing in `scripts/generate_synthetic_data.py`:

```python
# Pseudo-code for quantity text rendering
def render_quantity_text(quantity, cell_bounds, ui_scale=100):
    if quantity <= 1:
        return None  # No text for quantity 1

    font_size = 8 * (ui_scale / 100)
    font = load_font("PressStart2P", font_size)  # Or extracted game font

    text = str(quantity)

    # Render black outline (8 directions or stroke method)
    outline = render_text(text, font, color=BLACK, outline=True)

    # Render white fill on top
    fill = render_text(text, font, color=WHITE)

    # Position at bottom-right of cell
    x_offset = 3 * (ui_scale / 100)
    y_offset = 2 * (ui_scale / 100)
    position = (cell_bounds.right - text_width - x_offset,
                cell_bounds.bottom - text_height - y_offset)

    return composite(outline, fill, position)
```

## Notes

- Quantity text is easier to collect than quality stars (larger, more visible)
- Font matching is critical for authentic appearance
- If exact game font unavailable, prioritize visual similarity over exact match
- Document any platform differences (PC vs. Switch text rendering)
