# Data Collection Plan

This document tracks the strategy and todo lists for building the Stardew Vision dataset. The architecture uses an agent/tool-calling pipeline (ADR-009): the orchestrator VLM classifies screen types and dispatches extraction agents. Data collection therefore focuses on (1) Pierre's shop screenshots for extraction evaluation and (2) screen-type diversity screenshots for orchestrator classifier training.

See [ADR-006](adr/006-feature-store-strategy.md) for how this data will eventually be managed in Feast. For now, everything lives in the `datasets/` directory.

---

## Track 1: Pierre's Shop Screenshots

**Goal**: Screenshots of Pierre's General Store with various items selected, annotated with expected extracted field values. Used to evaluate OCR extraction accuracy (ADR-010) and as positive training examples for the orchestrator.

**Target**: 50-100 annotated screenshots covering different items, prices, and quantity selections.

### Phase A: Screenshot Collection

- [ ] Collect Pierre's shop screenshots with different items selected
  - Take screenshots at 1080p, 1440p, and iPad Retina resolutions
  - Vary the selected item (seeds, furniture, backpack, recipes)
  - Vary the quantity selected (1, 5, 10, max)
  - Save to `datasets/raw/pierre_shop/` with naming: `pierre_{YYYYMMDD}_{NNN}.png`
- [ ] Ensure the right-column detail panel is fully visible in each screenshot
  - Panel must show: item name, description, price, quantity selector, total
  - Full-screen screenshots are preferred (no cropping required from user)
- [ ] Collect at least 10 screenshots per resolution variant:
  - `pierre_1080p_NNN.png` — 1920×1080
  - `pierre_1440p_NNN.png` — 2560×1440
  - `pierre_ipad_NNN.png` — 2048×2732 (iPad Retina)

### Phase B: Anchor Template Extraction

- [ ] From collected screenshots, extract the anchor template for OpenCV template matching
  - Crop a small (30×30 px at 100% UI scale) corner of the shop detail panel frame
  - Save to `datasets/assets/templates/pierres_detail_panel_corner.png`
  - Test template match on several screenshots to verify reliability
  - Document match threshold and scaling behavior in `datasets/assets/templates/README.md`
- [ ] Measure panel layout at each resolution
  - Record pixel offsets from template match to each field region
  - Document in `datasets/assets/templates/pierres_detail_panel_layout.md`

### Phase C: Annotation

Every Pierre's shop screenshot gets a JSONL annotation with expected extraction output:

```json
{
  "image_id": "550e8400-e29b-41d4-a716-446655440001",
  "image_path": "raw/pierre_shop/pierre_1080p_001.png",
  "source": "real",
  "screen_type": "pierre_shop",
  "resolution": "1920x1080",
  "created_at": "2026-03-17T14:30:00Z",
  "expected_extraction": {
    "name": "Parsnip Seeds",
    "description": "Plant these in the spring. Takes 4 days to mature.",
    "price_per_unit": 20,
    "quantity_selected": 5,
    "total_cost": 100
  },
  "annotated_by": "human",
  "annotation_version": "2.0"
}
```

- [ ] Annotate all collected screenshots by hand (record exact text from the screenshot)
- [ ] Verify integer fields (price, quantity, total) by reading directly from screenshot
- [ ] Save annotations to `datasets/annotated/pierre_shop/`
- [ ] Run extraction tool on all annotated screenshots; compare to ground truth
  - Field match criterion: exact for integers; rapidfuzz ratio >= 90 for strings
  - Log results to MLFlow under experiment `pierre-shop-extraction`

### Phase D: Splits

- [ ] Hold out 15% of Pierre's shop screenshots as a fixed test set
  - `datasets/splits/pierre_shop_test.txt`
  - Never retrained on; used only for final evaluation
- [ ] Remaining 85% split 82/18 into train/val:
  - `datasets/splits/pierre_shop_train.txt`
  - `datasets/splits/pierre_shop_val.txt`

---

## Track 2: Screen-Type Diversity Screenshots

**Goal**: Screenshots covering multiple Stardew Valley UI screen types, labeled with `screen_type`. Used to train the orchestrator VLM to correctly classify and dispatch tool calls.

**Target**: Minimum 50 labeled screenshots per screen type for the orchestrator training set. Priority order: Pierre's shop (MVP), TV dialog (Phase 2), inventory tooltip (Phase 3), other (negative examples).

### Screen Types

| Screen Type | Label | Phase | Description |
|---|---|---|---|
| Pierre's shop detail panel | `pierre_shop` | 1 — MVP | Right-column item detail while shopping |
| TV program dialog | `tv_dialog` | 2 | Text on the in-game television screen |
| Inventory item tooltip | `inventory_tooltip` | 3 | Tooltip popup when hovering over an item |
| Crafting menu | `crafting_menu` | Post-MVP | Crafting recipe detail panel |
| Other / unknown | `other` | All | All other screens — orchestrator should not call any tool |

### Phase A: Collection

- [ ] For each screen type, collect at least 50 screenshots:
  - Vary items/content within the screen type (e.g., different items in Pierre's shop)
  - Vary resolution where possible (1080p, 1440p, iPad)
  - Save to `datasets/raw/{screen_type}/`
- [ ] Collect 30+ "other" screenshots (map view, combat, dialogue, chest grid) as negative examples
  - The orchestrator must learn to output `no_match` or remain silent for unrecognized screens

### Phase B: Annotation

Every diversity screenshot gets a screen-type label annotation:

```json
{
  "image_id": "550e8400-e29b-41d4-a716-446655440002",
  "image_path": "raw/tv_dialog/tv_001.png",
  "source": "real",
  "screen_type": "tv_dialog",
  "resolution": "1920x1080",
  "created_at": "2026-03-17T15:00:00Z",
  "annotated_by": "human",
  "annotation_version": "2.0"
}
```

- [ ] Annotate all diversity screenshots with the correct `screen_type` label
- [ ] Save to `datasets/annotated/screen_type/`
- [ ] Verify label distribution: no screen type should dominate the training set

### Phase C: Orchestrator Training Splits

- [ ] Create orchestrator training/val/test splits (stratified by screen type):
  - `datasets/splits/orchestrator_train.txt`
  - `datasets/splits/orchestrator_val.txt`
  - `datasets/splits/orchestrator_test.txt`
  - Hold out 15% per class as fixed test set

### Phase D: Community Outreach (post-MVP)

Once the core pipeline is working, expand the dataset with community submissions:

- [ ] Create submission guide explaining what screenshots are useful
- [ ] Post to r/StardewValley with the accessibility mission
- [ ] Collect submissions via Google Form with consent checkbox
- [ ] Model-assisted annotation: run zero-shot orchestrator on submissions; human reviews labels

---

## Annotation Schema

### Pierre's Shop Annotation (Track 1)

```json
{
  "image_id": "uuid4",
  "image_path": "raw/pierre_shop/pierre_1080p_001.png",
  "source": "real",
  "screen_type": "pierre_shop",
  "resolution": "1920x1080",
  "created_at": "ISO 8601 timestamp",
  "expected_extraction": {
    "name": "string",
    "description": "string",
    "price_per_unit": "integer",
    "quantity_selected": "integer",
    "total_cost": "integer"
  },
  "annotated_by": "human | model_assisted | synthetic",
  "annotation_version": "2.0"
}
```

### Screen-Type Label Annotation (Track 2)

```json
{
  "image_id": "uuid4",
  "image_path": "raw/{screen_type}/filename.png",
  "source": "real",
  "screen_type": "pierre_shop | tv_dialog | inventory_tooltip | crafting_menu | other",
  "resolution": "string",
  "created_at": "ISO 8601 timestamp",
  "annotated_by": "human | model_assisted",
  "annotation_version": "2.0"
}
```

Note: `image_id` is UUID4 (for future Feast entity key). `created_at` is ISO 8601. These fields are required from day 1 for Feast compatibility even if Feast is not used yet.

---

## Dataset Directory Structure

```
datasets/
├── assets/
│   ├── templates/                     # OpenCV anchor templates
│   │   ├── pierres_detail_panel_corner.png
│   │   ├── pierres_detail_panel_layout.md
│   │   └── README.md
│   └── ...
├── raw/
│   ├── pierre_shop/                   # Pierre's shop screenshots
│   ├── tv_dialog/                     # TV screen screenshots
│   ├── inventory_tooltip/             # Tooltip screenshots
│   └── other/                         # Negative examples
├── annotated/
│   ├── pierre_shop/                   # Track 1 annotations (with expected_extraction)
│   └── screen_type/                   # Track 2 annotations (screen_type label only)
├── splits/
│   ├── pierre_shop_train.txt
│   ├── pierre_shop_val.txt
│   ├── pierre_shop_test.txt
│   ├── orchestrator_train.txt
│   ├── orchestrator_val.txt
│   └── orchestrator_test.txt
└── README.md                          # Dataset card (mirrors HuggingFace)
```

Note: `datasets/` is a host-volume-mounted directory. It is in `.gitignore` — data is not committed to the GitHub repo. The dataset is published separately to HuggingFace Hub.

---

## Success Criteria

| Milestone | Target | Unblocks |
|-----------|--------|----------|
| 20 Pierre's shop screenshots annotated | Phase 1 start | OCR extraction development and testing |
| Anchor template extracted and verified | Phase 1 | `crop_pierres_detail_panel.py` implementation |
| 50 Pierre's shop screenshots annotated | Phase 1 complete | Reliable extraction accuracy measurement |
| 50+ screenshots per screen type (Pierre's + 2 others) | Phase 2 start | Orchestrator classifier training |
| Orchestrator: screen classification accuracy >= 95% | Phase 2 | Full end-to-end pipeline |
| 50 TV dialog screenshots annotated | Phase 2 complete | TV narration feature |
