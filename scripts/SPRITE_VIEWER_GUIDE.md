# Sprite Viewer Guide

The `view_sprites.py` script allows you to browse and view Stardew Valley item sprites by ID, name, or type.

## Requirements

For CLI viewing (matplotlib display):
```bash
pip install matplotlib pillow
```

For HTML catalog (no additional dependencies needed).

## Usage

All commands should be run from the project root directory:
```bash
cd /workspaces/stardew-vision
python3 scripts/view_sprites.py <command> [options]
```

---

## Commands

### 1. List All Types

Show all available item types and their counts:

```bash
python3 scripts/view_sprites.py types
```

Output:
```
Available item types:

  Basic                 248 items
  Litter                 92 items
  Cooking                85 items
  Fish                   83 items
  Crafting               69 items
  Minerals               53 items
  Seeds                  52 items
  ...
```

---

### 2. View Sprite by ID

Display a specific sprite by its item ID (requires matplotlib):

```bash
python3 scripts/view_sprites.py show 334
```

This opens a matplotlib window showing:
- Original 16×16 sprite
- Scaled 4× (64×64) version
- Item details (name, type, price, sprite index)

**Common Item IDs:**
- 334 - Copper Bar
- 335 - Iron Bar
- 336 - Gold Bar
- 388 - Wood
- 390 - Stone
- 72 - Diamond

---

### 3. View Sprites by Type

Display all sprites of a specific type in a grid (requires matplotlib):

```bash
python3 scripts/view_sprites.py type Basic
```

**Options:**
- `--limit N` - Limit display to N items (default: 20)

**Examples:**
```bash
# Show minerals (limit to 30)
python3 scripts/view_sprites.py type Minerals --limit 30

# Show all cooking items
python3 scripts/view_sprites.py type Cooking --limit 50

# Show fish
python3 scripts/view_sprites.py type Fish
```

**Available types:**
- Basic (248 items)
- Litter (92 items)
- Cooking (85 items)
- Fish (83 items)
- Crafting (69 items)
- Minerals (53 items)
- Seeds (52 items)
- Arch (42 items)
- Ring (31 items)
- asdf (33 items)
- Quest (18 items)
- interactive (1 item)

---

### 4. Search by Name

Search for sprites by item name (case-insensitive, partial match):

```bash
python3 scripts/view_sprites.py search copper
```

Output:
```
Found 4 items matching 'copper':

  334    - Copper Bar       (Basic)
  378    - Copper Ore       (Basic)
  ...
```

**Generate HTML for search results:**
```bash
python3 scripts/view_sprites.py search "diamond" --html
```

Creates `search_diamond.html` with matching items.

---

### 5. Generate HTML Catalog

Create a browsable HTML catalog of all sprites (or filtered by type):

**Full catalog (all 807 items):**
```bash
python3 scripts/view_sprites.py html
```

Creates `sprite_catalog.html` with all items grouped by type.

**Filter by type:**
```bash
python3 scripts/view_sprites.py html --type Basic --output basic_items.html
python3 scripts/view_sprites.py html --type Minerals --output minerals.html
python3 scripts/view_sprites.py html --type Cooking --output food.html
```

**Custom output location:**
```bash
python3 scripts/view_sprites.py html --output /tmp/sprites.html
```

---

## HTML Catalog Features

The generated HTML catalog includes:

✓ **Search bar** - Filter items by name or ID in real-time
✓ **Type grouping** - Items organized by type
✓ **Hover effects** - Cards enlarge on hover
✓ **Embedded sprites** - All sprites embedded as base64 (no external files)
✓ **Item details** - Name, ID, and price displayed

**Opening the catalog:**
```bash
# The script prints the file path
# Open in browser:
firefox sprite_catalog.html
# or
google-chrome sprite_catalog.html
# or just double-click the file
```

---

## CLI Display (matplotlib)

**Note:** CLI display requires matplotlib and PIL:
```bash
pip install matplotlib pillow
```

If not installed, the script will show an error and suggest installation.

For HTML catalog generation, no additional packages are needed (uses only stdlib + PIL which is already installed).

---

## Examples

### Find a specific item
```bash
# Search by name
python3 scripts/view_sprites.py search "prismatic"

# View by ID
python3 scripts/view_sprites.py show 74
```

### Browse items by category
```bash
# List all types
python3 scripts/view_sprites.py types

# View all gems
python3 scripts/view_sprites.py type Minerals --limit 50

# Create HTML catalog of all fish
python3 scripts/view_sprites.py html --type Fish --output fish_catalog.html
```

### Create a complete reference
```bash
# Generate full HTML catalog
python3 scripts/view_sprites.py html --output sprite_reference.html

# Open in browser
# file:///workspaces/stardew-vision/sprite_reference.html
```

---

## Tips

1. **Use HTML for browsing** - Much faster than matplotlib for viewing many items
2. **Search is fuzzy** - Partial matches work (e.g., "bar" finds "Copper Bar", "Iron Bar", etc.)
3. **Type names are case-insensitive** - `Basic`, `basic`, and `BASIC` all work
4. **HTML has search** - Use the search box in the HTML catalog to filter items dynamically

---

## Files Created

After running the commands, you'll have:

- `sprite_catalog.html` - Full catalog (807 items)
- `sprite_catalog_basic.html` - Basic items only (248 items)
- `search_*.html` - Search result catalogs (if using `--html` flag)

All HTML files are self-contained and can be opened in any web browser.

---

## Troubleshooting

**Error: "Manifest not found"**
- Make sure you're running from the project root: `/workspaces/stardew-vision`
- Check that `datasets/assets/item_manifest.json` exists

**Error: "matplotlib required"**
- Install matplotlib: `pip install matplotlib pillow`
- Or use HTML catalog instead (doesn't require matplotlib)

**Sprites not showing in HTML**
- Check that `datasets/assets/sprites/` directory exists
- Verify sprites are present: `ls datasets/assets/sprites/*.png | wc -l` (should be 807)

---

**Last updated**: 2026-03-05
**Compatible with**: Stardew Valley v1.6.15.24356
