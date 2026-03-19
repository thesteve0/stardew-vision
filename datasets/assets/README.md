# Assets Directory

This directory contains all source assets for the Stardew Vision project, extracted directly from the local Stardew Valley game installation.

## Quick Start - Which Files to Use

### For Data Generation Scripts

Use these paths (they point to game-extracted data):
- **Item manifest**: `item_manifest.json` → symlink to `item_manifest_game.json`
- **Sprites**: `sprites/` → symlink to `sprites_game/`

These use the authoritative data from your local game installation (Stardew Valley v1.6.15).

## Directory Structure

```
datasets/assets/
├── item_manifest.json          → symlink to item_manifest_game.json (USE THIS)
├── sprites/                    → symlink to sprites_game/ (USE THIS)
│
├── item_manifest_game.json     ✓ Item data from game (v1.6.15, 807 items)
├── sprites_game/               ✓ Sprites from game (807 files, 16×16 RGBA)
│   ├── sprite_0.png
│   ├── sprite_334.png (Copper Bar)
│   └── ... (807 total)
│
├── game_files/                 # Raw game data files
│   ├── Data_Objects.json       # SMAPI export of object data
│   ├── springobjects.png       # Full sprite sheet (384×624)
│   ├── springobjects.xnb       # Original XNB file
│   ├── Cursors*.xnb            # UI sprite files (3 files)
│   └── Objects.xnb             # Original object data XNB
│
├── ui_frames/                  # UI reference assets
│   ├── chest_ui_reference.png  # In-game chest UI screenshot
│   └── README.md               # UI documentation
│
├── sprite_layout_notes.md      # Sprite documentation
├── README.md                   # This file
└── metadata.md                 # Complete provenance documentation
```

## Data Source

**All data extracted from local Stardew Valley installation**:
- **Version**: 1.6.15.24356
- **Platform**: Steam (Flatpak)
- **Extraction method**: SMAPI + xnbcli
- **Files**: `item_manifest_game.json`, `sprites_game/`

## Item Manifest Format

The `item_manifest_game.json` file contains:

```json
{
  "334": {
    "name": "Copper Bar",
    "display_name": "Copper Bar",
    "type": "Basic",
    "category": -15,
    "description": "A bar of pure copper.",
    "sprite_index": 334,
    "sprite_file": "sprites/sprite_334.png",
    "price": 60,
    "edibility": -300
  },
  ...
}
```

### Key Fields
- `name`: Internal item name (from game data)
- `display_name`: Localized display name
- `type`: Item type (Basic, Minerals, Arch, Fish, Cooking, Seeds, Litter, etc.)
- `category`: Numeric category ID
- `sprite_index`: Position in springobjects.png sprite sheet
- `sprite_file`: Path to individual sprite PNG (relative to assets directory)
- `price`: Base sell price in gold
- `edibility`: Energy/health value (-300 = not edible)

## Sprite Information

### Individual Sprites (`sprites_game/`)
- **Count**: 807 sprites
- **Format**: PNG, 16×16 pixels, RGBA
- **Naming**: `sprite_{item_id}.png`
- **Source**: Extracted from game's springobjects.png using SpriteIndex field
- **Accuracy**: Exact match to what appears in-game

### Full Sprite Sheet (`game_files/springobjects.png`)
- **Dimensions**: 384×624 pixels
- **Grid**: 24 columns × 39 rows = 936 positions
- **Each sprite**: 16×16 pixels
- **Format**: PNG, RGBA
- **Source**: Unpacked from `springobjects.xnb` using xnbcli

### SpriteIndex Mapping

Items are mapped to sprites using the `SpriteIndex` field:
- Item 334 (Copper Bar) → SpriteIndex 334 → Position (col=14, row=13) in sprite sheet
- Calculation: `row = 334 // 24 = 13`, `col = 334 % 24 = 14`
- This ensures 100% accurate sprite-to-item mapping

## Usage in Scripts

```python
import json
from pathlib import Path
from PIL import Image

# Load manifest
manifest_path = Path('datasets/assets/item_manifest.json')
with open(manifest_path) as f:
    items = json.load(f)

# Get item info
copper_bar = items['334']
print(f"{copper_bar['name']} - {copper_bar['type']}")
print(f"Price: {copper_bar['price']}g, SpriteIndex: {copper_bar['sprite_index']}")

# Load sprite
sprite_path = Path('datasets/assets') / copper_bar['sprite_file']
sprite = Image.open(sprite_path)  # 16×16 RGBA image

# Scale for in-game display (64×64)
from PIL import Image
scaled_sprite = sprite.resize((64, 64), Image.NEAREST)  # Pixel-perfect scaling
```

## Sprite Scaling for Synthetic Data

In-game display shows items at **64×64 pixels** (4× scale from base 16×16).

When generating synthetic screenshots:
```python
from PIL import Image

# Load 16×16 sprite
sprite = Image.open('datasets/assets/sprites/sprite_334.png')

# Scale to 64×64 using nearest-neighbor (preserves pixel art)
scaled = sprite.resize((64, 64), Image.NEAREST)

# Or scale by factor
scale_factor = 4
scaled = sprite.resize((sprite.width * scale_factor, sprite.height * scale_factor), Image.NEAREST)
```

**Important**: Use `Image.NEAREST` (nearest-neighbor interpolation) to preserve pixel-art appearance. Other methods (BILINEAR, BICUBIC) will blur the sprites.

## Common Items Reference

| ID | Name | Type | SpriteIndex | Price | Notes |
|----|------|------|-------------|-------|-------|
| 334 | Copper Bar | Basic | 334 | 60g | Crafting material |
| 335 | Iron Bar | Basic | 335 | 120g | Crafting material |
| 336 | Gold Bar | Basic | 336 | 250g | Crafting material |
| 337 | Iridium Bar | Basic | 337 | 1000g | Rare crafting material |
| 338 | Refined Quartz | Basic | 338 | 50g | Crafting material |
| 382 | Coal | Basic | 382 | 15g | Common resource |
| 388 | Wood | Basic | 388 | 2g | Very common resource |
| 390 | Stone | Basic | 390 | 2g | Very common resource |
| 66 | Amethyst | Minerals | 66 | 100g | Gemstone |
| 68 | Topaz | Minerals | 68 | 80g | Gemstone |
| 72 | Diamond | Minerals | 72 | 750g | Rare gemstone |
| 74 | Prismatic Shard | Minerals | 74 | 2000g | Very rare |

## Item Types Distribution

The 807 items are categorized into types:
- **Basic**: Common items, resources, crafting materials
- **Minerals**: Gems, ores, geodes
- **Arch**: Artifacts from digging
- **Fish**: All fish species
- **Cooking**: Cooked dishes and meals
- **Seeds**: Seeds for planting crops
- **Litter**: Debris and non-collectible items
- **Crafting**: Craftable items
- **asdf**: (Some special items)

## Metadata and Documentation

For complete details see:
- **[metadata.md](metadata.md)** - Complete provenance, extraction methods, timestamps
- **[sprite_layout_notes.md](sprite_layout_notes.md)** - Technical sprite details
- **[ui_frames/README.md](ui_frames/README.md)** - UI frame specifications

## Verification

All data has been verified:
- ✓ 807 items extracted from game
- ✓ 807 sprites extracted using correct SpriteIndex
- ✓ All sprites are 16×16 RGBA PNG
- ✓ Sprite-to-item mapping 100% accurate
- ✓ All metadata fields present and validated

Sample verification:
```bash
$ file datasets/assets/sprites/sprite_334.png
datasets/assets/sprites/sprite_334.png: PNG image data, 16 x 16, 8-bit/color RGBA

$ python3 -c "import json; data=json.load(open('datasets/assets/item_manifest.json')); print(data['334']['name'], data['334']['sprite_index'])"
Copper Bar 334
```

## Updating Data

If the game is updated to a newer version, re-extract the data:

1. Export new Objects data via SMAPI: `patch export Data/Objects`
2. Copy new XNB files if sprite sheet updated
3. Run extraction script: `python3 scripts/build_manifest_from_game.py`
4. Update version number in metadata.md

---

**Last updated**: 2026-03-05
**Game version**: Stardew Valley 1.6.15.24356
**Total items**: 807
**Total sprites**: 807 (16×16 RGBA PNG)
