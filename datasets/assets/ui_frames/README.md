# UI Frame Assets - Screenshot Collection

This directory contains UI reference screenshots used for synthetic data generation. These screenshots provide the visual templates for creating accurate chest/inventory grid backgrounds.

## Purpose

Before implementing synthetic data generation, we need comprehensive UI reference screenshots to ensure our generated images accurately match the in-game appearance, including:
- Cell position calculation
- Background grid rendering
- Border/frame styling
- Empty vs occupied cell appearance
- Different chest type dimensions (3×9 treasure chests vs 3×12 storage chests)

---

## Screenshot Collection Status

### Priority 1: Essential Grid References (REQUIRED)

These are critical for synthetic data generation:

- [ ] **chest_empty_treasure_3x9.png** - Empty 3×9 treasure chest
  - Purpose: See pure grid layout without items
  - Shows: Cell borders, background color, exact spacing

- [ ] **chest_empty_storage_3x12.png** - Empty 3×12 storage chest
  - Purpose: Understand larger chest grid layout
  - Shows: Different grid dimensions

- [ ] **chest_partial_treasure.png** - Partially filled treasure chest
  - Purpose: See how items sit within cells
  - Contents: 3-5 items scattered across grid (e.g., Wood, Stone, Copper Bar)
  - Shows: Item positioning, quantity text overlay

- [ ] **chest_partial_storage.png** - Partially filled storage chest
  - Purpose: Verify item rendering in larger chest
  - Contents: 5-10 items scattered across grid

- [ ] **chest_full_treasure.png** - Full 3×9 treasure chest
  - Purpose: See how filled cells look when adjacent
  - Contents: All 27 slots filled

- [ ] **chest_full_storage.png** - Full 3×12 storage chest
  - Purpose: See maximum capacity layout
  - Contents: All 36 slots filled

### Priority 2: Inventory References (RECOMMENDED)

Include these for flexibility if we decide to show player inventory:

- [ ] **chest_with_empty_inventory.png** - Chest UI with empty player inventory visible
  - Purpose: See full UI layout with both sections
  - Shows: Relative positioning of chest and inventory

- [ ] **chest_with_partial_inventory.png** - Chest UI with items in both sections
  - Purpose: See how both grids look with items
  - Contents: Items in both chest and inventory

- [ ] **inventory_empty_closeup.png** - Empty inventory grid only
  - Purpose: Dedicated view of empty inventory grid
  - Shows: Inventory cell layout and dimensions

- [ ] **inventory_partial_closeup.png** - Partial inventory with items
  - Purpose: See inventory cell details
  - Contents: Various items in inventory slots

### Priority 3: Variations (OPTIONAL)

Optional but useful for robustness:

- [ ] **chest_stacked_items.png** - Items with quantity numbers
  - Purpose: See quantity numbers clearly (×5, ×10, ×99, etc.)

- [ ] **chest_context_[location].png** - Different chest locations/contexts
  - Purpose: See if chest appearance varies by location

- [ ] **chest_zoom_[level].png** - Different zoom levels (if applicable)
  - Purpose: See if UI scaling affects layout

- [ ] **chest_special_[type].png** - Special chest types (Junimo, colored, etc.)
  - Purpose: Document any unique chest UIs

### Current Assets

- [x] **chest_ui_reference.png** (Existing)
  - **Source**: [Interface In Game](https://interfaceingame.com/screenshots/stardew-valley-chest/)
  - **Resolution**: 2560×1440 pixels
  - **Type**: Populated storage chest with items
  - **Use**: Initial reference for chest UI structure

---

## Screenshot Catalog

*To be filled in as screenshots are collected*

### chest_empty_treasure_3x9.png
- **Status**: Not yet collected
- **Resolution**: TBD
- **Description**: TBD
- **Measurements**: TBD

### chest_empty_storage_3x12.png
- **Status**: Not yet collected
- **Resolution**: TBD
- **Description**: TBD
- **Measurements**: TBD

*(Continue for each screenshot)*

---

## Measurement Data

*To be extracted from collected screenshots*

### Grid Dimensions

**Treasure Chest (3×9):**
- Total slots: 27
- Rows: 3
- Columns: 9
- Cell size: ___ × ___ pixels
- Grid spacing: ___ pixels
- Border thickness: ___ pixels
- Total grid area: ___ × ___ pixels

**Storage Chest (3×12):**
- Total slots: 36
- Rows: 3
- Columns: 12
- Cell size: ___ × ___ pixels
- Grid spacing: ___ pixels
- Border thickness: ___ pixels
- Total grid area: ___ × ___ pixels

**Player Inventory:**
- Total slots: ___ (TBD)
- Rows: ___
- Columns: ___
- Cell size: ___ × ___ pixels
- Grid spacing: ___ pixels

### Color Specifications

**Background:**
- Grid background: RGB(__, __, __) or #______
- Cell border: RGB(__, __, __) or #______
- Frame color: RGB(__, __, __) or #______

**Text Overlays:**
- Quantity text color: RGB(__, __, __) or #______
- Quantity text font size: ___ pixels
- Quantity text position: ___ (e.g., bottom-right corner)

### Layout Positions

**Chest Grid:**
- Top-left corner position: (___, ___) pixels from image origin
- Grid offset from frame: ___ pixels

**Inventory Grid (if included):**
- Top-left corner position: (___, ___) pixels from image origin
- Vertical spacing from chest: ___ pixels

---

## Collection Guidelines

### Format Specifications
- **File format:** PNG (lossless, preserves UI details)
- **Resolution:** Native game resolution (don't scale or crop)
- **Compression:** PNG default compression (lossless)
- **Color mode:** RGB or RGBA (whatever game outputs)

### Capture Requirements

**What to include:**
- Full chest/inventory UI visible
- Clear cell borders
- Any UI chrome (close buttons, chest icon, labels)
- Quantity text overlays (for filled cells)

**What to avoid:**
- Don't crop - capture full UI element
- Avoid mouse cursor in frame (if possible)
- Avoid tooltips or hover effects
- Capture in a well-lit area (not in dark mines/night)

### Recommended Items for Screenshots

For partially filled chests, use recognizable, common items:
- **Wood (388)** - Easy to recognize brown logs
- **Stone (390)** - Gray stones
- **Copper Bar (334)** - Orange/copper colored
- **Iron Bar (335)** - Gray metallic
- **Gold Bar (336)** - Yellow/golden
- **Coal (382)** - Black coal
- **Diamond (72)** - Blue gem

This helps verify that our sprite positioning is correct during synthetic generation.

### Naming Convention

Use descriptive filenames following this pattern:
```
[element]_[state]_[variant].png

Examples:
chest_empty_treasure_3x9.png
chest_partial_storage.png
chest_full_treasure.png
inventory_empty_closeup.png
chest_with_partial_inventory.png
```

---

## How to Collect Screenshots

### In-Game Setup

1. **Launch Stardew Valley** and load a save file
2. **Prepare a chest** with the desired state (empty, partial, full)
3. **Open the chest** to display the UI
4. **Position the view** so the entire UI is visible
5. **Take screenshot** using game's screenshot function or OS screenshot tool
   - Steam: F12
   - Windows: Win+PrintScreen or Win+Shift+S
   - Mac: Cmd+Shift+3 or Cmd+Shift+4
   - Linux: PrintScreen or Shift+PrintScreen

### After Collection

1. **Rename files** according to naming convention
2. **Move files** to `datasets/assets/ui_frames/`
3. **Run verification script** (see below)
4. **Update catalog** in this README with measurements
5. **Update checklist** above

---

## Verification

After collecting screenshots, run the verification script to check formats and extract measurements:

```bash
python scripts/verify_ui_screenshots.py
```

This script will:
- Check that all essential screenshots are present
- Verify PNG format and resolution
- Extract basic measurements (cell size, grid dimensions)
- Generate a measurement report

---

## Synthetic Generation Reference

### Template Selection

**For treasure chest (3×9) generation:**
- Primary template: `chest_empty_treasure_3x9.png`
- Reference for item placement: `chest_partial_treasure.png`

**For storage chest (3×12) generation:**
- Primary template: `chest_empty_storage_3x12.png`
- Reference for item placement: `chest_partial_storage.png`

### Key Measurements Needed

Before implementing synthetic data generation (`scripts/generate_synthetic_data.py`), we need:

1. **Exact cell dimensions** (width, height in pixels)
2. **Grid spacing** (horizontal and vertical gaps between cells)
3. **Starting position** (top-left corner of first cell)
4. **Border thickness** (if rendering borders separately)
5. **Background colors** (RGB values for accurate reproduction)

These will be extracted from the collected screenshots and documented in the "Measurement Data" section above.

---

## Next Steps

1. **Collect essential screenshots** (Priority 1, 6 screenshots minimum)
2. **Run verification script** to extract measurements
3. **Document measurements** in this README
4. **Implement grid template** in `scripts/generate_synthetic_data.py`
5. **Test synthetic generation** against reference screenshots
6. **Iterate** to match visual fidelity

---

## Original Notes (Preserved)

### Game Asset Location

The UI frames are stored in:
- **File**: `Content/LooseSprites/Cursors.xnb` (and variants `Cursors2.xnb`, `Cursors_1_6.xnb`)
- **Contents**: Mouse cursors, menu elements, inventory UI components, chest menu buttons
- **Extraction tools**: XNB unpacking tools (see `sprite_layout_notes.md`)

### Synthetic Generation Approach Options

**Option A: Extract from Game Files (More Authentic)**
1. Unpack `Content/LooseSprites/Cursors.xnb` using StardewXnbHack or xnbcli
2. Locate the chest menu background components
3. Composite them to create an empty chest grid template

**Option B: Use Collected Screenshots (Recommended for MVP)**
1. Use collected empty chest screenshots as direct templates
2. Composite item sprites onto the exact cell positions
3. Good enough for training; authentic to real UI
4. Faster than XNB extraction

**Option C: Create Simplified Template (Fallback)**
1. Use PIL/Pillow to create a simple grid programmatically
2. Good enough for training if screenshots insufficient
3. Not pixel-perfect but adequate for VLM learning

**Current recommendation:** Option B (use collected screenshots) - provides authentic appearance without XNB complexity.

---

## Sources

- Reference screenshot: [Interface In Game](https://interfaceingame.com/screenshots/stardew-valley-chest/)
- UI assets: Game files `Content/LooseSprites/Cursors*.xnb`
- Modding documentation: [Stardew Valley Forums - GUI Sprite Sheet Modding](https://forums.stardewvalley.net/threads/help-wanted-gui-sprite-sheet-modding.32779/)
