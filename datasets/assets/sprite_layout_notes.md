# Stardew Valley Sprite Layout Documentation

**Last updated**: 2026-03-05
**Data source**: Local Stardew Valley installation v1.6.15.24356
**Extraction method**: SMAPI + xnbcli

## Overview

We have extracted **807 individual item sprites** from Stardew Valley using the SpriteIndex field from the game's object data. Each sprite is a 16×16 pixel PNG file with RGBA color.

## Data Source

**All sprites extracted from local game installation**:
- **Game version**: 1.6.15.24356
- **Sprite sheet**: `game_files/springobjects.png` (384×624 pixels)
- **Object data**: `game_files/Data_Objects.json` (SMAPI export)
- **Extraction script**: `scripts/build_manifest_from_game.py`

## Sprite Organization

### Individual Sprite Files

**Location**: `sprites_game/` (or via symlink: `sprites/`)

**Naming convention**: `sprite_{item_id}.png` where `{item_id}` is the Stardew Valley item ID

**Format**: 16×16 pixel PNG, RGBA, non-interlaced

**Count**: 807 sprites (one per item)

**Extraction method**:
1. Read item's `SpriteIndex` field from Objects data
2. Calculate position: `row = SpriteIndex // 24`, `col = SpriteIndex % 24`
3. Extract 16×16 region from sprite sheet at `(col * 16, row * 16)`
4. Save as `sprite_{item_id}.png`

### Sprite Sheet Layout

**File**: `game_files/springobjects.png`

**Dimensions**: 384×624 pixels

**Grid structure**:
- **Columns**: 24 (384 pixels / 16 pixels per sprite = 24)
- **Rows**: 39 (624 pixels / 16 pixels per sprite = 39)
- **Total positions**: 936 (24 × 39)
- **Sprite size**: 16×16 pixels each
- **Coordinate system**: Top-left origin (0, 0), increments of 16 pixels

**Format**: PNG, RGBA, non-interlaced

### SpriteIndex Mapping

Each item in the Objects data has a `SpriteIndex` field that specifies which sprite in the sheet corresponds to that item.

**Example**:
- Item ID 334 (Copper Bar) has `SpriteIndex: 334`
- Position calculation:
  - Row: `334 // 24 = 13`
  - Col: `334 % 24 = 14`
  - X coordinate: `14 * 16 = 224` pixels
  - Y coordinate: `13 * 16 = 208` pixels
- Extract 16×16 region from (224, 208) to (240, 224)

This ensures **100% accurate sprite-to-item mapping** directly from the game data.

## Sprite Extraction Example

```python
from PIL import Image

# Load the full sprite sheet
sprite_sheet = Image.open('game_files/springobjects.png')  # 384×624

# Item info from manifest
item_id = '334'
sprite_index = 334  # From Objects data

# Calculate position
sheet_columns = 24
sprite_size = 16

row = sprite_index // sheet_columns  # 13
col = sprite_index % sheet_columns   # 14

x = col * sprite_size  # 224
y = row * sprite_size  # 208

# Extract sprite
sprite = sprite_sheet.crop((x, y, x + sprite_size, y + sprite_size))
sprite.save(f'sprite_{item_id}.png')  # 16×16 RGBA
```

## Scaling for Synthetic Data Generation

In-game display typically shows items at **64×64 pixels** (4× scale from base 16×16).

### Recommended Scaling Method

```python
from PIL import Image

# Load original sprite
sprite = Image.open('sprites/sprite_334.png')  # 16×16

# Scale to in-game display size (64×64)
scaled = sprite.resize((64, 64), Image.NEAREST)

# Save if needed
scaled.save('sprite_334_scaled.png')
```

**Important**: Always use `Image.NEAREST` (nearest-neighbor interpolation) to preserve the pixel-art appearance. Other methods like `BILINEAR` or `BICUBIC` will blur the sprites.

### Scaling Factors

| Original | Scale Factor | Display Size | Use Case |
|----------|--------------|--------------|----------|
| 16×16 | 1× | 16×16 | Original game sprites |
| 16×16 | 4× | 64×64 | Standard in-game display |
| 16×16 | 8× | 128×128 | High-resolution displays |

## Common Items Reference

For quick reference during synthetic data generation:

| Item ID | Name | Type | SpriteIndex | Notes |
|---------|------|------|-------------|-------|
| 334 | Copper Bar | Basic | 334 | Orange-brown bar |
| 335 | Iron Bar | Basic | 335 | Gray bar |
| 336 | Gold Bar | Basic | 336 | Yellow bar |
| 337 | Iridium Bar | Basic | 337 | Purple bar |
| 338 | Refined Quartz | Basic | 338 | White crystal |
| 382 | Coal | Basic | 382 | Black lump |
| 388 | Wood | Basic | 388 | Brown log |
| 390 | Stone | Basic | 390 | Gray stone |
| 66 | Amethyst | Minerals | 66 | Purple gem |
| 68 | Topaz | Minerals | 68 | Orange gem |
| 72 | Diamond | Minerals | 72 | Blue-white gem |
| 74 | Prismatic Shard | Minerals | 74 | Rainbow crystal |

## Sprite Characteristics

### File Properties
- **Format**: PNG (Portable Network Graphics)
- **Color mode**: RGBA (Red, Green, Blue, Alpha)
- **Bit depth**: 8-bit per channel (32-bit total)
- **Dimensions**: 16×16 pixels (all sprites)
- **Compression**: PNG default (lossless)
- **Interlacing**: None

### Visual Characteristics
- **Style**: Pixel art
- **Palette**: Limited colors per sprite (pixel art style)
- **Transparency**: Many sprites use alpha channel for transparent backgrounds
- **Details**: Fine details at 16×16 resolution require careful viewing

## Item Categories

The sprites represent items from various categories:

- **Basic**: Resources, bars, materials
- **Minerals**: Gems, ores, geodes, artifacts
- **Arch**: Archaeological artifacts
- **Fish**: Various fish species
- **Cooking**: Prepared food items
- **Seeds**: Crop seeds
- **Litter**: Debris, weeds, stones
- **Crafting**: Craftable items
- And more (807 items total)

## Verification Commands

```bash
# Check sprite count
ls sprites_game/*.png | wc -l
# Expected: 807

# Verify sprite format
file sprites_game/sprite_334.png
# Expected: PNG image data, 16 x 16, 8-bit/color RGBA, non-interlaced

# Check sprite dimensions using Python
python3 -c "from PIL import Image; img = Image.open('sprites_game/sprite_334.png'); print(f'{img.size}, {img.mode}')"
# Expected: (16, 16), RGBA

# Verify sprite sheet dimensions
file game_files/springobjects.png
# Expected: PNG image data, 384 x 624, 8-bit/color RGBA
```

## Technical Notes

### Why Individual Sprites?

Instead of using the full sprite sheet and calculating positions at runtime, we pre-extract individual sprites because:

1. **Simplicity**: Easier to work with in data generation scripts
2. **Accuracy**: SpriteIndex ensures correct sprite-to-item mapping
3. **Portability**: Can share individual sprites without the full sheet
4. **Performance**: No need to crop sprites during training

### Sprite Sheet Grid Alignment

The sprite sheet uses a perfect 16-pixel grid:
- No padding between sprites
- No margins around edges
- Sprites are tightly packed in a 24-column grid
- Some positions may be unused (sheet has 936 positions, but only ~807 items use them)

### Alpha Channel Usage

Many sprites use transparency:
- Background areas are fully transparent (alpha = 0)
- Item pixels are fully opaque (alpha = 255)
- Some sprites may have semi-transparent edges for anti-aliasing

## Sources and Tools

### Extraction Tools
- **SMAPI**: [smapi.io](https://smapi.io/) - For exporting Objects data
- **Content Patcher**: [Nexus Mods](https://www.nexusmods.com/stardewvalley/mods/1915) - SMAPI mod for data export
- **xnbcli**: [LeonBlade/xnbcli](https://github.com/LeonBlade/xnbcli) - For unpacking XNB sprite sheet

### Documentation
- **Stardew Valley Wiki**: [stardewvalleywiki.com](https://stardewvalleywiki.com/) - General game info
- **Stardew Modding Wiki**: [stardewmodding.wiki.gg](https://stardewmodding.wiki.gg/) - Modding reference

### Game Content
- Stardew Valley by ConcernedApe
- Sprites extracted from legally owned copy (Steam)
- Used for educational purposes and accessibility tool development

---

**Note**: This documentation reflects the sprite data as extracted from Stardew Valley v1.6.15.24356. If the game is updated, some sprite indices or appearances may change. Re-extract using `scripts/build_manifest_from_game.py` to update.
