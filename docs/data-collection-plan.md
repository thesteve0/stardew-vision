# Data Collection Plan

This document tracks the todo lists for building the Stardew Vision dataset. There are two parallel tracks: synthetic data generation (fast, perfect ground truth, unblocks everything) and community-sourced real screenshots (slower, needed for an honest test set).

See [ADR-006](adr/006-feature-store-strategy.md) for how this data will eventually be managed in Feast. For now, everything lives in the `datasets/` directory.

---

## Track 1: Synthetic Data Generation

**Goal**: 500 labeled synthetic images by end of Week 1. These unblock baseline evaluation and the first fine-tuning run.

**Script**: `scripts/generate_synthetic_data.py`

### Phase A: Asset Acquisition

- [ ] Download the Stardew Valley `springobjects.png` sprite sheet
  - Source: Stardew Valley Wiki (CC-BY-NC-SA fan content)
  - Alternative: extract from a local game installation (`Content/Maps/springobjects.xnb` → PNG via `unxnb`)
  - Save to `datasets/assets/springobjects.png`
- [ ] Download or compile the Stardew Valley item manifest
  - Maps item IDs (integers) to item names and categories
  - Source: `Data/ObjectInformation.xnb` from game, or the community-maintained JSON at stardewvalleywiki.com
  - Save to `datasets/assets/item_manifest.json`
  - Format: `{"334": {"name": "Copper Bar", "category": "Resources", "sprite_row": 5, "sprite_col": 2}, ...}`
- [ ] Document sprite sheet layout
  - Stardew Valley sprites are 16×16 pixels, arranged in a 24-column grid in `springobjects.png`
  - Verify sprite coordinates for at least 10 common items before automating
  - Document findings in `datasets/assets/sprite_layout_notes.md`
- [ ] Collect UI frame assets (the chest/inventory background grid)
  - The loot box frame is a UI element, not a sprite sheet element
  - Options: screenshot the empty chest UI, or recreate from known dimensions
  - Save candidate frames to `datasets/assets/ui_frames/`
- [ ] Collect dual-grid UI frames (chest + player inventory visible)
  - Screenshot the chest UI with player inventory visible (typical in-game view)
  - Document dual-grid layout: chest grid above, player inventory grid below
  - Test various UI scales (75%, 100%, 125%, 150%) and resolutions
  - Save to `datasets/assets/ui_frames/dual_grid/` with naming: `dual_grid_{resolution}_{scale}.png`
- [x] Extract or create quality star sprites (silver, gold, iridium) ✅ **COMPLETED 2026-03-06**
  - **Method:** Extracted directly from game files (`Cursors.xnb` → `Cursors.png`)
  - **Source coordinates:** Silver (338,400), Gold (346,400), Iridium (346,392) - from game source code
  - **Size:** Exactly 8×8 pixels at 100% UI scale (confirmed)
  - **Files created:**
    - `datasets/assets/quality_stars/silver_star_100.png` (8×8)
    - `datasets/assets/quality_stars/silver_star_125.png` (10×10)
    - `datasets/assets/quality_stars/gold_star_100.png` (8×8)
    - `datasets/assets/quality_stars/gold_star_125.png` (10×10)
    - `datasets/assets/quality_stars/iridium_star_100.png` (8×8)
    - `datasets/assets/quality_stars/iridium_star_125.png` (10×10)
  - **Extraction script:** `scripts/extract_quality_stars.py`
  - **Documentation:** See [Asset Extraction Summary](../../datasets/assets/EXTRACTION_SUMMARY.md)
  - [ ] Document exact positioning rules (bottom-left corner of cell, specific pixel offset) - still TODO
- [x] Document in-game quantity text rendering ✅ **COMPLETED 2026-03-06**
  - **Method:** Extracted font directly from game files (`SmallFont.xnb`)
  - **Font type:** SpriteFont (Microsoft XNA Framework bitmap font)
  - **Font atlas:** `datasets/assets/quantity_overlays/SmallFont.png` (256×260 px)
  - **Glyph data:** `datasets/assets/quantity_overlays/SmallFont.json` (character → pixel coordinates)
  - **Style:** White text with black outline (confirmed from game rendering)
  - **Positioning:** Bottom-right corner of cell (to be measured)
  - **Documentation:** See `datasets/assets/quantity_overlays/README.md`
  - [ ] Positioning measurements still TODO (see `datasets/assets/overlay_examples/measurements.md`)

### Phase B: Script Development

- [ ] Write `scripts/generate_synthetic_data.py`
  - [ ] Function: load item manifest and sprite sheet
  - [ ] Function: extract a single item sprite (16×16 px) given item ID
  - [ ] Function: scale sprite to match in-game display size (~64×64 px at standard zoom)
  - [ ] Function: composite a grid of sprites onto a UI frame background
  - [ ] Function: add item quantity text overlay (font: white with black outline, matching in-game style)
    - Positioned in bottom-right quadrant of cell
    - Range: 2-999 (quantity 1 = no overlay)
  - [ ] Function: add quality star overlay (silver, gold, or iridium sprite)
    - Positioned in bottom-left quadrant of cell
    - Normal quality = no star overlay
  - [ ] Function: generate diverse overlay combinations per ADR-007
    - 30% no overlay (quantity=1, quality=normal)
    - 25% quantity only (quantity 2-999, quality=normal)
    - 20% quality only (quantity=1, quality=silver/gold/iridium)
    - 25% both overlays (quantity 2-999 AND quality silver/gold/iridium)
  - [ ] Function: randomly assign items to cells (with configurable empty cell probability ~0.2)
  - [ ] Function: generate dual-grid screenshots (chest + inventory) per ADR-008
    - Support variable grid sizes: 3×12 (36 slots) and 3×24 (72 slots)
    - Generate at multiple resolutions:
      - iPad Retina: 2048×2732 (4:3 aspect)
      - 1080p: 1920×1080 (16:9)
      - 1440p: 2560×1440 (16:9)
      - 4K: 3840×2160 (16:9)
    - Generate at UI scale variations: 75%, 100%, 125%
    - Populate inventory grid with random items (visual distractor for VLM)
    - Add `grid_type` field to annotation: `"chest_only"` or `"chest_with_inventory"`
  - [ ] Function: output image + JSONL annotation in standard schema (see below)
  - [ ] CLI: `python scripts/generate_synthetic_data.py --count 500 --output datasets/ --grid-sizes "3x12,3x24" --resolutions "2048x2732,1920x1080,2560x1440" --ui-scales "75,100,125" --dual-grid-probability 0.6`
- [ ] Write `scripts/validate_dataset.py`
  - [ ] Check every annotation file has a corresponding image
  - [ ] Check every image has a corresponding annotation
  - [ ] Validate annotation JSONL against the JSON schema
  - [ ] Report class distribution (which items appear how often)
  - [ ] Check for duplicate images (hash-based)
  - [ ] CLI: `python scripts/validate_dataset.py datasets/`

### Annotation Schema

Every annotation file follows this exact JSONL format (one JSON object per line = one image):

```json
{
  "image_id": "550e8400-e29b-41d4-a716-446655440000",
  "image_path": "raw/synth_00001.png",
  "source": "synthetic",
  "loot_type": "treasure_chest",
  "grid": {"rows": 3, "cols": 12},
  "grid_type": "chest_with_inventory",
  "resolution": "1920x1080",
  "ui_scale": 100,
  "created_at": "2026-03-10T14:30:00Z",
  "cells": [
    {
      "row": 0, "col": 0,
      "occupied": true,
      "item_id": 334,
      "item_name": "Copper Bar",
      "item_category": "Resources",
      "quantity": 5,
      "quality": "silver"
    },
    {
      "row": 0, "col": 1,
      "occupied": false,
      "item_id": null,
      "item_name": "empty",
      "item_category": null,
      "quantity": 0,
      "quality": null
    }
  ],
  "annotated_by": "synthetic_script",
  "annotation_version": "1.1"
}
```

Note: `image_id` is a UUID4 (for future Feast entity key). `created_at` is ISO 8601. These fields are required from day 1 for Feast compatibility even if Feast is not used yet.

**Quality field values**: `"normal"` (no star), `"silver"`, `"gold"`, `"iridium"`, or `null` (empty cells only). See [ADR-007](adr/007-overlay-detection-strategy.md) for rationale.

**Grid type field values** (added in v1.1 per [ADR-008](adr/008-grid-detection-strategy.md)):
- `"chest_only"`: Screenshot shows only the chest grid (cropped or naturally isolated)
- `"chest_with_inventory"`: Screenshot shows both chest grid (upper) and player inventory grid (lower)

**Resolution and UI scale fields** (added in v1.1 per ADR-008): Track the generated image dimensions and in-game UI scale percentage to validate VLM robustness across platforms.

### Phase C: Generation and Validation

- [ ] Run pilot generation: `python scripts/generate_synthetic_data.py --count 10`
  - Visually inspect the 10 generated images
  - Verify sprite alignment, quantity text legibility, background correctness
- [ ] Run pilot dual-grid generation: `python scripts/generate_synthetic_data.py --count 10 --dual-grid-probability 1.0`
  - Visually inspect dual-grid layout (chest above, inventory below)
  - Verify chest grid is visually distinct from inventory grid
  - Test at multiple resolutions (iPad Retina vs. 1080p) and UI scales (75% vs. 125%)
  - Verify inventory grid is populated with random items
- [ ] Fix any visual issues found in pilot
- [ ] Run full generation: `python scripts/generate_synthetic_data.py --count 500 --dual-grid-probability 0.6`
  - Target distribution: 40% chest-only, 60% dual-grid (40% 3×12, 20% 3×24)
- [ ] Run validation: `python scripts/validate_dataset.py datasets/`
- [ ] Review class distribution report — ensure common items (Wood, Coal, Fiber) are not over-represented to the point of dominating training
- [ ] Review grid type distribution: verify 40% chest-only, 60% dual-grid split
- [ ] Review resolution/scale distribution: verify variety across platforms
- [ ] If distribution is too skewed: adjust sampling weights and regenerate
- [ ] Create initial train/val split (no test split until real screenshots arrive):
  - 85% train, 15% val (both synthetic)
  - Ensure both splits include chest-only AND dual-grid examples
  - Save split manifests to `datasets/splits/synthetic_train.txt` and `datasets/splits/synthetic_val.txt`
  - Create dual-grid-specific test set: `datasets/splits/dual_grid_test.txt` (for grid detection accuracy testing)
- [ ] Commit the generation script and validation script (not the generated images — those go in `.gitignore`)

### Phase D: Expansion (post-baseline)

- [ ] Add more item variety: ensure at least 50 distinct items appear in the 500 images
- [ ] Add loot type variety: generate chest (3×3), backpack row (12×3), and shipping bin variants
- [ ] Add visual augmentation: slight brightness variation, jpeg compression artifacts (to bridge synthetic → real domain gap)
- [ ] Increase to 1000 images before final fine-tuning run

---

## Track 2: Community-Sourced Real Screenshots

**Goal**: 100-200 real Stardew Valley screenshots of loot boxes, annotated with ground truth item labels. The test set must be **real screenshots only**.

**Timeline**: Launch outreach by end of Week 2; collect over Weeks 2-4; use model-assisted annotation to reduce human effort.

### Phase A: Submission Infrastructure

- [ ] Create a Google Form for screenshot submission
  - Fields: screenshot upload, game version, platform (PC/Switch/iPad), consent checkbox
  - Acceptance criteria communicated in the form: loot box must be fully visible, screenshot must be unedited
- [ ] Create a shared Google Drive folder for received submissions
- [ ] Write a brief, friendly submission guide (see `docs/user-submission-guide.md`)
  - ✅ Full screenshots accepted (inventory visible is fine — no cropping required)
  - ✅ Any platform/resolution supported
  - What counts: treasure chests, backpack inventory grid, shipping bin
  - What doesn't count: combat, dialogue boxes, map view, modded items
- [ ] Set up a simple naming convention for received files: `real_{submitter_hash}_{YYYYMMDD}_{NNN}.png`

### Phase B: Community Outreach

- [ ] Draft submission request post for r/StardewValley
  - Lead with the accessibility mission (a player with low vision needs better tools)
  - Request: "open a treasure chest / your backpack, take a screenshot, submit via form"
  - Offer: submitters credited in the HuggingFace dataset card if they consent
  - Keep it brief — one paragraph + submission link
- [ ] Post to r/StardewValley (check posting rules first; accessibility/community posts are generally welcome)
- [ ] Post to Stardew Valley Discord server (multiple channels: #accessibility, #community)
- [ ] Post to ConcernedApe's fan Discord if accessible
- [ ] Share in any accessibility gaming communities (AbleGamers, etc.)
- [ ] Track submissions: maintain a spreadsheet of (date, source, count, status)

### Phase C: Model-Assisted Annotation

Rather than annotating 100-200 screenshots by hand from scratch, use the zero-shot VLM output as a starting point:

- [ ] Once VLM baseline is running (Week 2), run it zero-shot on each received screenshot
- [ ] Export VLM predictions as draft JSONL annotations
- [ ] Human reviewer checks each prediction:
  - If correct: mark `annotated_by: "model_assisted_v1"` and save
  - If wrong: correct the item name/quantity, mark `annotated_by: "human_corrected"`
- [ ] Write `scripts/annotate_dataset.py` to streamline this review:
  - Display image + VLM prediction side-by-side in terminal or simple Jupyter widget
  - Allow reviewer to accept (Enter), correct (type new item name), or reject (mark as unusable)
  - Save approved annotations to `datasets/annotated/`
- [ ] Target: annotate 20 real screenshots per day during annotation sessions

### Phase D: Real-Screenshot Dataset Splits

- [ ] Once 50+ real screenshots are annotated, create the test split:
  - Test set = first 50 real screenshots (fixed; never retrained on)
  - Remaining real screenshots join the training pool
- [ ] Save split manifests: `datasets/splits/real_test.txt`, `datasets/splits/real_train.txt`
- [ ] Combine with synthetic splits for full dataset:
  - `datasets/splits/train_full.txt` = synthetic_train + real_train
  - `datasets/splits/val_full.txt` = synthetic_val
  - `datasets/splits/test_final.txt` = real_test only

### Phase E: Quality Control

- [ ] Review annotation consistency: if two people annotated the same item differently (e.g., "Copper Bar" vs "copper bar"), normalize to canonical names from the item manifest
- [ ] Flag low-quality screenshots: blurry, partially cropped, non-English game text, or modded items not in the vanilla manifest
- [ ] Track annotation statistics: how many cells per screenshot, item distribution, annotation source breakdown
- [ ] Write findings to `datasets/README.md` (this becomes the HuggingFace dataset card)

---

## Dataset Directory Structure

```
datasets/
├── assets/
│   ├── springobjects.png          # Stardew Valley sprite sheet
│   ├── item_manifest.json         # item_id → name, category, sprite coords
│   ├── sprite_layout_notes.md     # Notes on sprite extraction
│   └── ui_frames/                 # UI background frames for synthetic gen
├── raw/
│   ├── synth_00001.png            # Generated synthetic images
│   ├── synth_00002.png
│   ├── real_abc123_20260315_001.png  # Community submissions
│   └── ...
├── annotated/
│   ├── synth_00001.jsonl          # Annotation for each image
│   ├── synth_00002.jsonl
│   ├── real_abc123_20260315_001.jsonl
│   └── ...
├── splits/
│   ├── synthetic_train.txt        # Image IDs for synthetic train set
│   ├── synthetic_val.txt          # Image IDs for synthetic val set
│   ├── real_test.txt              # Image IDs for real test set (fixed)
│   ├── real_train.txt             # Image IDs for real train additions
│   ├── train_full.txt             # Combined train set
│   ├── val_full.txt               # Combined val set
│   └── test_final.txt             # Final test set (real only)
└── README.md                      # Dataset card (mirrors HuggingFace)
```

Note: `datasets/` is a host-volume-mounted directory (mounted at `/data` or local path). It is in `.gitignore` — data is not committed to the GitHub repo. The dataset is published separately to HuggingFace Hub.

---

## Success Criteria

| Milestone | Target | Unblocks |
|-----------|--------|----------|
| 500 synthetic images generated | End of Week 1 | Zero-shot baseline evaluation |
| Submission form live | End of Week 2 | Community collection |
| 20 real screenshots annotated | End of Week 3 | Real-data validation set |
| 50 real screenshots annotated | End of Week 4 | Honest test set; first real-data evaluation |
| 100 real screenshots annotated | End of Week 5 | Retrain with mixed data; final evaluation |
