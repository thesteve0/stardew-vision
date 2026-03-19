# UI Measurement Template

Use this template to record measurements extracted from collected screenshots. Copy the relevant sections to the README.md file once measurements are complete.

## How to Measure

### Using Python/PIL

```python
from PIL import Image

# Open screenshot
img = Image.open("datasets/assets/ui_frames/chest_empty_treasure_3x9.png")

# Get dimensions
width, height = img.size
print(f"Image dimensions: {width}×{height}")

# Get pixel color at specific position
pixel_color = img.getpixel((x, y))
print(f"Color at ({x}, {y}): RGB{pixel_color}")
```

### Using Image Viewer

- Open screenshot in image viewer (GIMP, Preview, etc.)
- Use ruler/measurement tool to measure pixel distances
- Hover over colors to get RGB values
- Note positions of grid corners and cells

---

## Treasure Chest (3×9) Measurements

**Screenshot:** `chest_empty_treasure_3x9.png`

### Image Properties
- **Total image size:** _____ × _____ pixels
- **Color mode:** RGB / RGBA

### Grid Layout
- **Number of rows:** 3
- **Number of columns:** 9
- **Total slots:** 27

### Cell Dimensions
- **Cell width:** _____ pixels
- **Cell height:** _____ pixels
- **Cell aspect ratio:** 1:1 (square) or _____

### Grid Spacing
- **Horizontal spacing between cells:** _____ pixels
- **Vertical spacing between cells:** _____ pixels
- **Border/separator thickness:** _____ pixels

### Grid Position
- **Grid top-left corner:** (_____, _____) pixels from image origin
- **Grid bottom-right corner:** (_____, _____) pixels from image origin
- **Total grid width:** _____ pixels (including borders)
- **Total grid height:** _____ pixels (including borders)

### Colors (RGB values)
- **Grid background:** RGB(_____, _____, _____) or #______
- **Cell background:** RGB(_____, _____, _____) or #______
- **Cell border/separator:** RGB(_____, _____, _____) or #______
- **UI frame color:** RGB(_____, _____, _____) or #______

### UI Chrome
- **Frame padding (top):** _____ pixels
- **Frame padding (bottom):** _____ pixels
- **Frame padding (left):** _____ pixels
- **Frame padding (right):** _____ pixels

### Cell Position Formula

First cell (row 0, col 0):
```
x_start = _____
y_start = _____
```

Any cell (row r, col c):
```python
cell_x = x_start + c * (cell_width + horizontal_spacing)
cell_y = y_start + r * (cell_height + vertical_spacing)
```

---

## Storage Chest (3×12) Measurements

**Screenshot:** `chest_empty_storage_3x12.png`

### Image Properties
- **Total image size:** _____ × _____ pixels
- **Color mode:** RGB / RGBA

### Grid Layout
- **Number of rows:** 3
- **Number of columns:** 12
- **Total slots:** 36

### Cell Dimensions
- **Cell width:** _____ pixels
- **Cell height:** _____ pixels
- **Cell aspect ratio:** 1:1 (square) or _____

### Grid Spacing
- **Horizontal spacing between cells:** _____ pixels
- **Vertical spacing between cells:** _____ pixels
- **Border/separator thickness:** _____ pixels

### Grid Position
- **Grid top-left corner:** (_____, _____) pixels from image origin
- **Grid bottom-right corner:** (_____, _____) pixels from image origin
- **Total grid width:** _____ pixels (including borders)
- **Total grid height:** _____ pixels (including borders)

### Colors (RGB values)
- **Grid background:** RGB(_____, _____, _____) or #______
- **Cell background:** RGB(_____, _____, _____) or #______
- **Cell border/separator:** RGB(_____, _____, _____) or #______
- **UI frame color:** RGB(_____, _____, _____) or #______

### Cell Position Formula

First cell (row 0, col 0):
```
x_start = _____
y_start = _____
```

Any cell (row r, col c):
```python
cell_x = x_start + c * (cell_width + horizontal_spacing)
cell_y = y_start + r * (cell_height + vertical_spacing)
```

---

## Player Inventory Measurements

**Screenshot:** `inventory_empty_closeup.png` or `chest_with_empty_inventory.png`

### Image Properties
- **Total image size:** _____ × _____ pixels
- **Color mode:** RGB / RGBA

### Grid Layout
- **Number of rows:** _____ (usually 3-4)
- **Number of columns:** _____ (usually 12)
- **Total slots:** _____

### Cell Dimensions
- **Cell width:** _____ pixels
- **Cell height:** _____ pixels
- **Cell aspect ratio:** 1:1 (square) or _____

### Grid Spacing
- **Horizontal spacing between cells:** _____ pixels
- **Vertical spacing between cells:** _____ pixels
- **Border/separator thickness:** _____ pixels

### Grid Position (in full UI screenshot)
- **Grid top-left corner:** (_____, _____) pixels from image origin
- **Vertical offset from chest grid:** _____ pixels

### Colors (RGB values)
- **Grid background:** RGB(_____, _____, _____) or #______
- **Cell background:** RGB(_____, _____, _____) or #______
- **Cell border/separator:** RGB(_____, _____, _____) or #______

---

## Item Rendering Observations

**Screenshot:** `chest_partial_treasure.png` or `chest_partial_storage.png`

### Item Sprite Positioning
- **Item sprite size:** _____ × _____ pixels
- **Item position within cell:**
  - Centered
  - Top-left at offset (_____, _____)
  - Other: _____

### Quantity Text Overlay
- **Font/size:** _____
- **Text color:** RGB(_____, _____, _____) or #______
- **Text position:**
  - Bottom-right corner
  - Offset from cell corner: (_____, _____)
  - Other: _____
- **Text background:** Yes / No
  - If yes, color: RGB(_____, _____, _____) or #______

### Stacking Indicators
- **Format:** "×5", "99", other: _____
- **Maximum quantity shown:** _____ (e.g., ×99, ×999)

---

## Validation Checklist

After completing measurements:

- [ ] Measurements from treasure chest (3×9)
- [ ] Measurements from storage chest (3×12)
- [ ] Cell dimensions are consistent across both chest types
- [ ] Grid spacing is consistent
- [ ] Color values extracted
- [ ] Item sprite positioning documented
- [ ] Quantity text format documented
- [ ] Position formulas verified with sample calculations
- [ ] Measurements added to main README.md

---

## Sample Calculation Verification

### Test: Calculate position of cell at row 1, col 5 in treasure chest

**Given measurements:**
- x_start = _____
- y_start = _____
- cell_width = _____
- cell_height = _____
- horizontal_spacing = _____
- vertical_spacing = _____

**Calculation:**
```
cell_x = x_start + 5 * (cell_width + horizontal_spacing)
cell_x = _____ + 5 * (_____ + _____)
cell_x = _____

cell_y = y_start + 1 * (cell_height + vertical_spacing)
cell_y = _____ + 1 * (_____ + _____)
cell_y = _____
```

**Verify:**
- Open partial chest screenshot in image viewer
- Navigate to cell at row 1, col 5 (6th cell in 2nd row)
- Check if calculated position matches actual cell position
- [ ] Position verified ✓

---

## Notes

- All measurements are in pixels at the original screenshot resolution
- If screenshots are taken at different resolutions, note the scale factor
- Colors may vary slightly due to lighting/environment in screenshot
- Cell borders may be drawn differently (separators vs cell outlines)
- Verify measurements against multiple screenshots for accuracy
