# Quick Screenshot Collection Guide

Use this checklist while playing Stardew Valley to collect the needed UI reference screenshots.

## Quick Checklist

### Essential (6 screenshots) - DO THESE FIRST

1. [ ] **chest_empty_treasure_3x9.png**
   - Open an empty 3×9 treasure chest
   - Screenshot the entire chest UI

2. [ ] **chest_empty_storage_3x12.png**
   - Open an empty 3×12 storage chest (larger chest)
   - Screenshot the entire chest UI

3. [ ] **chest_partial_treasure.png**
   - Put 3-5 items in a treasure chest (Wood, Stone, Copper Bar, Coal, Iron Bar)
   - Scatter them across the grid (not all in first row)
   - Screenshot

4. [ ] **chest_partial_storage.png**
   - Put 5-10 items in a storage chest
   - Scatter across the grid
   - Screenshot

5. [ ] **chest_full_treasure.png**
   - Fill all 27 slots of a treasure chest
   - Screenshot

6. [ ] **chest_full_storage.png**
   - Fill all 36 slots of a storage chest
   - Screenshot

### Recommended (4 screenshots) - DO IF TIME ALLOWS

7. [ ] **chest_with_empty_inventory.png**
   - Open chest with empty player inventory visible
   - Shows full UI layout

8. [ ] **chest_with_partial_inventory.png**
   - Open chest with items in both chest and inventory
   - Shows both grids populated

9. [ ] **inventory_empty_closeup.png**
   - Focus on empty inventory grid

10. [ ] **inventory_partial_closeup.png**
    - Focus on inventory with items

### Optional (2-4 screenshots) - BONUS

11. [ ] **chest_stacked_items.png**
    - Items with quantity numbers (×5, ×10, ×99)

12. [ ] **chest_special_[type].png**
    - Any special chest types (Junimo, colored)

---

## Screenshot Settings

**Format:** PNG (lossless)
**Resolution:** Your native game resolution (don't scale)
**What to capture:** Full chest UI, including frame and buttons
**What to avoid:**
- Mouse cursor in frame
- Tooltips/hover effects
- Dark lighting (screenshot in daylight or well-lit area)

---

## How to Take Screenshots

**Steam:** Press F12
**Windows:** Win+PrintScreen or Win+Shift+S
**Mac:** Cmd+Shift+3 or Cmd+Shift+4
**Linux:** PrintScreen or Shift+PrintScreen

---

## Recommended Items for Testing

Use these common items for partial chest screenshots:
- Wood (388)
- Stone (390)
- Copper Bar (334)
- Iron Bar (335)
- Gold Bar (336)
- Coal (382)
- Diamond (72)

---

## After Collection

1. Rename files according to naming convention (see filenames above)
2. Move to `/workspaces/stardew-vision/datasets/assets/ui_frames/`
3. Run verification: `python scripts/verify_ui_screenshots.py`
4. Update README.md checklist

---

## File Naming Examples

```
chest_empty_treasure_3x9.png      ← Empty 3×9 chest
chest_partial_storage.png         ← Partial 3×12 chest
chest_full_treasure.png           ← Full 3×9 chest
chest_with_empty_inventory.png    ← Chest + inventory view
inventory_empty_closeup.png       ← Just inventory
chest_stacked_items.png           ← Items with quantities
```

---

## Quick Tips

- **Empty chests:** Just open a new chest you haven't used
- **Partial chests:** Randomly place a few items, don't fill rows
- **Full chests:** Fill every single slot (tedious but needed once)
- **Lighting:** Screenshot during daytime or in well-lit building
- **No rush:** Take your time to get clean screenshots without cursor

---

**Target:** Minimum 6 screenshots (essential) | Recommended 10 screenshots (essential + inventory)
