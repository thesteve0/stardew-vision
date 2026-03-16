# UI Screenshot Collection - Implementation Summary

## Overview

This document summarizes the implementation of the UI reference screenshot collection infrastructure for the Stardew Vision project.

## Purpose

Before implementing synthetic data generation, we need comprehensive UI reference screenshots to ensure our generated images accurately match the in-game chest/inventory appearance. This includes understanding:
- Cell positions and dimensions
- Grid spacing and layout
- Border styling and colors
- Empty vs occupied cell appearance
- Different chest types (3×9 treasure vs 3×12 storage)

## What Was Implemented

### 1. Documentation Structure

**File: `datasets/assets/ui_frames/README.md`**
- Comprehensive screenshot checklist (Essential, Recommended, Optional)
- Collection status tracking with checkboxes
- Screenshot catalog template for documenting each image
- Measurement data sections for extracting grid specifications
- Collection guidelines and best practices
- File naming conventions
- Reference for synthetic generation approach

**File: `datasets/assets/ui_frames/COLLECTION_GUIDE.md`**
- Quick reference guide for use while playing
- Condensed checklist of what to capture
- Screenshot tips and recommended items
- File naming examples
- Post-collection steps

### 2. Verification Script

**File: `scripts/verify_ui_screenshots.py`**
- Automated verification of collected screenshots
- Checks for required, recommended, and optional screenshots
- Validates PNG format and resolution
- Extracts metadata (dimensions, color mode, file size)
- Provides clear status report and summary
- Exit codes for CI/automation (0 = success, 1 = missing essential screenshots)

**Usage:**
```bash
python scripts/verify_ui_screenshots.py
```

### 3. Directory Structure

```
datasets/assets/ui_frames/
├── README.md                           # Comprehensive documentation
├── COLLECTION_GUIDE.md                 # Quick reference for collection
├── chest_ui_reference.png              # Existing reference (2560×1440)
├── chest_empty_treasure_3x9.png        # To be collected
├── chest_empty_storage_3x12.png        # To be collected
├── chest_partial_treasure.png          # To be collected
├── chest_partial_storage.png           # To be collected
├── chest_full_treasure.png             # To be collected
├── chest_full_storage.png              # To be collected
└── (additional screenshots...)          # To be collected
```

## Screenshot Collection Requirements

### Essential (Priority 1) - 6 Screenshots

These are **required** before synthetic data generation can begin:

1. `chest_empty_treasure_3x9.png` - Empty 3×9 treasure chest
2. `chest_empty_storage_3x12.png` - Empty 3×12 storage chest
3. `chest_partial_treasure.png` - Partially filled treasure chest (3-5 items)
4. `chest_partial_storage.png` - Partially filled storage chest (5-10 items)
5. `chest_full_treasure.png` - Full 27-slot treasure chest
6. `chest_full_storage.png` - Full 36-slot storage chest

### Recommended (Priority 2) - 4 Screenshots

Include these for flexibility with player inventory:

7. `chest_with_empty_inventory.png` - Chest + empty player inventory
8. `chest_with_partial_inventory.png` - Chest + inventory with items
9. `inventory_empty_closeup.png` - Empty inventory grid only
10. `inventory_partial_closeup.png` - Inventory with items

### Optional (Priority 3) - 2-4 Screenshots

Useful for robustness testing:

11. `chest_stacked_items.png` - Items with quantity numbers
12. `chest_context_[location].png` - Different locations
13. `chest_zoom_[level].png` - Different zoom levels
14. `chest_special_[type].png` - Special chest types

**Total recommended:** 10 screenshots (6 essential + 4 inventory)

## Collection Workflow

### Step 1: In-Game Collection

1. Launch Stardew Valley
2. Prepare chests with desired states (empty, partial, full)
3. Take screenshots using:
   - Steam: F12
   - Windows: Win+PrintScreen
   - Mac: Cmd+Shift+3
   - Linux: PrintScreen
4. Capture full UI (don't crop)
5. Avoid cursor, tooltips, dark lighting

### Step 2: File Management

1. Rename files according to naming convention
2. Move to `datasets/assets/ui_frames/`
3. Verify PNG format and reasonable resolution

### Step 3: Verification

```bash
# Run verification script
python scripts/verify_ui_screenshots.py

# Check output for:
# - File presence and validity
# - Resolution and format
# - Overall completion status
```

### Step 4: Documentation

1. Update `README.md` checklist (mark collected items)
2. Fill in screenshot catalog entries
3. Extract and document measurements:
   - Cell dimensions
   - Grid spacing
   - Background colors
   - Layout positions
4. Update measurement data section

### Step 5: Proceed to Synthetic Generation

Once essential screenshots are collected and documented, proceed to:
- Implement `scripts/generate_synthetic_data.py`
- Use measurements to create accurate grid templates
- Composite item sprites onto grid backgrounds
- Validate synthetic images against reference screenshots

## Key Features of Implementation

### Verification Script Features

- **Priority-based checking:** Separates essential, recommended, and optional screenshots
- **Metadata extraction:** Automatically extracts resolution, color mode, file size
- **Clear reporting:** Visual status indicators (✓/✗) and formatted output
- **Validation:** Checks for PNG format, minimum resolution, file accessibility
- **Exit codes:** Returns 0 if all essential screenshots present, 1 otherwise
- **Additional detection:** Identifies unexpected PNG files in directory

### Documentation Features

- **Comprehensive checklists:** Track collection progress
- **Measurement templates:** Pre-formatted sections for documenting grid specs
- **Collection guidelines:** Best practices for screenshot quality
- **Naming conventions:** Consistent, descriptive filenames
- **Quick reference guide:** Separate condensed guide for in-game use
- **Reference linking:** Connection to sprite_layout_notes.md and other docs

## Next Steps

1. **Manual collection:** User needs to play Stardew Valley and capture screenshots
2. **Verification:** Run `verify_ui_screenshots.py` after collection
3. **Measurement extraction:** Document cell sizes, spacing, colors in README.md
4. **Implementation:** Use measurements in synthetic data generation script
5. **Validation:** Compare synthetic output to reference screenshots

## Integration with Project Plan

This implementation aligns with:
- **docs/plan.md Phase 1.1:** Data Collection - "Screenshot real chest UIs"
- **ADR-002:** VLM output is structured JSON, so we need accurate cell positions
- **docs/data-collection-plan.md:** Synthetic data generation requires UI templates

## Files Modified/Created

### Created
- `datasets/assets/ui_frames/COLLECTION_GUIDE.md` - Quick reference
- `scripts/verify_ui_screenshots.py` - Verification script
- `docs/ui-screenshot-collection.md` - This summary

### Updated
- `datasets/assets/ui_frames/README.md` - Enhanced with comprehensive plan

## Success Criteria

**Minimum viable:** 6 essential screenshots collected and verified
**Recommended:** 10 screenshots (essential + inventory references)
**Complete:** All screenshots including optional variations

The verification script provides clear status on progress toward these goals.

## Notes

- Screenshots are **not committed to git** (too large, host volume)
- Only documentation and verification script are in version control
- `chest_ui_reference.png` (existing) is already in `ui_frames/` directory
- Measurements will be extracted manually or semi-automatically from screenshots
- This infrastructure enables accurate synthetic data generation in next phase

---

**Status:** Infrastructure complete, ready for screenshot collection
**Next action:** User needs to launch Stardew Valley and collect screenshots
**Verification:** Run `python scripts/verify_ui_screenshots.py` to check progress
