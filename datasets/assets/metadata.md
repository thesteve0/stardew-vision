# Assets Metadata

This file documents the provenance of all assets in the `datasets/assets/` directory, including extraction sources, timestamps, and processing steps.

## Data Source: Local Game Installation

All item data and sprites are extracted directly from the locally installed copy of Stardew Valley.

### Game Version
- **Stardew Valley Version**: 1.6.15.24356
- **Installation Path**: `/var/home/stpousty/.var/app/com.valvesoftware.Steam/.local/share/Steam/steamapps/common/Stardew Valley/`
- **Platform**: Steam (Flatpak)
- **Extraction Dates**: 2026-03-04 to 2026-03-05

---

## Extracted Game Files

### 1. Objects Data (SMAPI Export)

- **File**: `game_files/Data_Objects.json`
- **Extraction date**: 2026-03-05
- **Method**: SMAPI `patch export Data/Objects` command
- **File size**: 656 KB
- **Format**: JSON object (807 items)
- **Contents**: Complete object data including names, types, categories, sprite indices, prices, edibility, descriptions
- **Key fields**: `Name`, `DisplayName`, `Type`, `Category`, `SpriteIndex`, `Price`, `Edibility`, `Description`

**Extraction process**:
1. Installed SMAPI (Stardew Valley mod loader) on host machine
2. Installed Content Patcher mod
3. Launched Stardew Valley via SMAPI
4. Executed `patch export Data/Objects` in SMAPI console
5. Copied exported file from `<game>/patch export/Data/Objects.json` to devcontainer

### 2. Sprite Sheet

- **File**: `game_files/springobjects.png`
- **Extraction date**: 2026-03-04
- **Source XNB**: `Content/Maps/springobjects.xnb`
- **Unpacking tool**: [xnbcli](https://github.com/LeonBlade/xnbcli) v1.0
- **File size**: 330 KB
- **Format**: PNG image
- **Dimensions**: 384×624 pixels (24 columns × 39 rows)
- **Sprite size**: 16×16 pixels per sprite
- **Total sprite positions**: 936
- **Contents**: All item sprites in a grid layout

**Extraction process**:
1. Copied `springobjects.xnb` from game installation to devcontainer
2. Cloned and installed xnbcli tool
3. Executed: `node xnbcli.js unpack springobjects.xnb`
4. Result: `springobjects.png` (384×624 pixels)

### 3. UI Cursor Sprites

- **Files**: `game_files/Cursors.xnb`, `Cursors2.xnb`, `Cursors_1_6.xnb`
- **Extraction date**: 2026-03-04
- **Source XNB**: `Content/LooseSprites/Cursors*.xnb`
- **Status**: Copied but not yet unpacked
- **Purpose**: UI elements including chest frame backgrounds (reserved for future use)

### 4. Chest UI Reference Screenshot

- **File**: `ui_frames/chest_ui_reference.png`
- **Download date**: 2026-03-04 20:14:59 UTC
- **Source URL**: https://interfaceingame.com/wp-content/uploads/stardew-valley/stardew-valley-chest.png
- **Source website**: [Interface In Game](https://interfaceingame.com/screenshots/stardew-valley-chest/)
- **File size**: 577 KB
- **Format**: PNG image
- **Dimensions**: 2560×1440 pixels, 8-bit RGB
- **Contents**: Full in-game screenshot showing populated chest inventory UI
- **Purpose**: Reference for UI layout and styling in synthetic data generation

---

## Processing: Game Data to Manifest

### Final Manifest and Sprites Generation

**Script**: `scripts/build_manifest_from_game.py`
**Execution date**: 2026-03-05 00:38 UTC

**Input files**:
- `game_files/Data_Objects.json` (SMAPI export, 807 items)
- `game_files/springobjects.png` (sprite sheet, 384×624 pixels)

**Output files**:
- `item_manifest_game.json` - Final item manifest (807 items)
- `sprites_game/*.png` - Individual sprite files (807 files, 16×16 RGBA)

**Processing algorithm**:
1. Parsed 807 items from SMAPI-exported Objects data
2. For each item, read the `SpriteIndex` field (e.g., item 334 → sprite index 334)
3. Calculated sprite position in sheet:
   - `row = SpriteIndex // 24` (24 columns per row)
   - `col = SpriteIndex % 24`
   - `x = col * 16`, `y = row * 16` (16×16 pixel sprites)
4. Cropped 16×16 sprite region from sprite sheet
5. Saved sprite as `sprites_game/sprite_{item_id}.png`
6. Created manifest entry with all item metadata

**Results**:
- ✓ 807 items successfully processed (100%)
- ✓ 807 sprites extracted (100%)
- ✓ 0 errors or skipped items
- ✓ All sprites validated as 16×16 RGBA PNG format

**Manifest structure**:
```json
{
  "item_id": {
    "name": "Internal name",
    "display_name": "Localized display name",
    "type": "Item type (Basic, Minerals, etc.)",
    "category": -15,
    "description": "Item description",
    "sprite_index": 334,
    "sprite_file": "sprites/sprite_334.png",
    "price": 60,
    "edibility": -300
  }
}
```

### Symlink Creation

**Date**: 2026-03-05 00:40 UTC

Created symlinks for convenience:
- `item_manifest.json` → `item_manifest_game.json`
- `sprites/` → `sprites_game/`

This allows scripts to use consistent paths (`item_manifest.json` and `sprites/`) that automatically point to the game-extracted data.

---

## Files Summary

### Primary Files (Use These)

| File/Directory | Type | Count | Source | Processing |
|----------------|------|-------|--------|------------|
| `item_manifest.json` | Symlink | - | → item_manifest_game.json | - |
| `item_manifest_game.json` | JSON | 1 file | Game v1.6.15 | Built from SMAPI export |
| `sprites/` | Symlink | - | → sprites_game/ | - |
| `sprites_game/` | PNG images | 807 files | Game v1.6.15 | Extracted using SpriteIndex |

### Source Files (Raw Game Data)

| File/Directory | Type | Size | Notes |
|----------------|------|------|-------|
| `game_files/Data_Objects.json` | JSON | 656 KB | SMAPI export of object data |
| `game_files/springobjects.png` | PNG | 330 KB | Full sprite sheet (384×624) |
| `game_files/springobjects.xnb` | XNB | 97 KB | Original XNB file |
| `game_files/Cursors*.xnb` | XNB | 386 KB | UI sprite files (3 files) |
| `game_files/Objects.xnb` | XNB | 24 KB | Original object data XNB |

### Supporting Files

| File/Directory | Type | Notes |
|----------------|------|-------|
| `ui_frames/chest_ui_reference.png` | PNG | UI reference screenshot |
| `ui_frames/README.md` | Markdown | UI documentation |
| `sprite_layout_notes.md` | Markdown | Sprite technical details |
| `README.md` | Markdown | Quick start guide |
| `metadata.md` | Markdown | This file |

**Total asset files**: 820+ files

---

## Data Integrity

### Item Coverage
- **Total items in manifest**: 807
- **Items with sprites**: 807 (100%)
- **Sprite source**: Directly from game's springobjects.png via SpriteIndex
- **Data completeness**: Full object data including prices, edibility, descriptions
- **Item types**: Basic, Minerals, Arch, Fish, Cooking, Seeds, Litter, and others

### Sprite Verification
- All 807 sprites extracted using correct SpriteIndex mapping
- All sprites are exactly 16×16 pixels
- All sprites use RGBA color format
- Sprites match exactly what appears in Stardew Valley v1.6.15
- Example verification: `sprites_game/sprite_334.png` (Copper Bar) at SpriteIndex 334 ✓

### Sample Items

| ID | Name | Type | SpriteIndex | Price | Edibility |
|----|------|------|-------------|-------|-----------|
| 334 | Copper Bar | Basic | 334 | 60 | -300 |
| 335 | Iron Bar | Basic | 335 | 120 | -300 |
| 336 | Gold Bar | Basic | 336 | 250 | -300 |
| 338 | Refined Quartz | Basic | 338 | 50 | -300 |
| 382 | Coal | Basic | 382 | 15 | -300 |
| 388 | Wood | Basic | 388 | 2 | -300 |
| 390 | Stone | Basic | 390 | 2 | -300 |
| 66 | Amethyst | Minerals | 66 | 100 | -300 |
| 72 | Diamond | Minerals | 72 | 750 | -300 |

---

## Attribution and Licensing

### Data Source
**Local Stardew Valley Installation** (v1.6.15.24356)
- Legally owned copy via Steam
- Data extracted from personal installation
- Used for educational and accessibility purposes

### Extraction Tools
- **SMAPI**: [smapi.io](https://smapi.io/) - Stardew Valley mod loader (for data export)
- **Content Patcher**: [Nexus Mods](https://www.nexusmods.com/stardewvalley/mods/1915) - SMAPI mod enabling `patch export`
- **xnbcli**: [LeonBlade/xnbcli](https://github.com/LeonBlade/xnbcli) - XNB unpacker (for sprite sheet extraction)

### Game Assets
- **Stardew Valley** © ConcernedApe
- Game assets extracted from legally owned copy
- Sprites and data used for educational purposes and accessibility tool development
- This project is for non-commercial use (conference talk and accessibility tool)
- Educational use under fair use principles

### Supporting Resources
- **Interface In Game**: [interfaceingame.com](https://interfaceingame.com/) - UI screenshot for reference

---

## Notes

### Data Quality
- The extraction process was fully automated and lossless
- No manual editing or modification of sprites was performed
- The manifest preserves all original game data
- Sprite-to-item mapping is guaranteed correct via SpriteIndex field
- All raw source files retained for reproducibility

### Version Consistency
- All data extracted from the same game installation (v1.6.15.24356)
- Ensures consistency between manifest and sprites
- Can be re-extracted if game updates to a newer version

### Future Maintenance
If the game is updated:
1. Re-run SMAPI export: `patch export Data/Objects`
2. Re-extract sprite sheet using xnbcli (if updated)
3. Re-run `scripts/build_manifest_from_game.py`
4. Update version numbers in this metadata file

---

## Reproducibility

To reproduce this extraction from your own Stardew Valley installation:

### Step 1: Install SMAPI (on host machine)
```bash
# Download SMAPI from https://smapi.io/
# Run the installer - it will find your Steam installation
# Install Content Patcher mod from Nexus Mods
```

### Step 2: Export Objects Data
```bash
# Launch Stardew Valley via SMAPI
# In the SMAPI console window:
patch export Data/Objects

# Copy from: <Stardew Valley>/patch export/Data/Objects.json
# To: /workspaces/stardew-vision/datasets/assets/game_files/Data_Objects.json
```

### Step 3: Extract Sprite Sheet
```bash
# Copy springobjects.xnb from game to devcontainer
# In devcontainer:
cd /tmp
git clone https://github.com/LeonBlade/xnbcli.git
cd xnbcli
npm install
node xnbcli.js unpack /path/to/springobjects.xnb /output/path/
```

### Step 4: Build Manifest and Extract Sprites
```bash
cd /workspaces/stardew-vision
python3 scripts/build_manifest_from_game.py
```

### Step 5: Create Symlinks
```bash
cd datasets/assets
ln -s item_manifest_game.json item_manifest.json
ln -s sprites_game sprites
```

---

**Last updated**: 2026-03-05
**Game version**: Stardew Valley 1.6.15.24356
**Extracted by**: Claude Code (Asset Acquisition Phase)
