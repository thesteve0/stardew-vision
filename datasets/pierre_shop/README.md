# Pierre's General Store Dataset

## Overview
Ground truth annotations for Pierre's General Store detail panel screenshots.

## Contents
- **images/**: 22 screenshots (1600×1200) from Pierre's shop
- **annotations.jsonl**: Ground truth annotations with item details
- **quality_report.json**: Validation report from annotation process

## Annotation Schema
Each record includes:
- `image_hash`: SHA256 hash for unique identification
- `original_file_name`: Original filename
- `screen_type`: "pierre_shop"
- `image_path`: Relative path to image
- `resolution`: [width, height] in pixels
- `expected_extraction`: Ground truth data
  - `name`: Item name
  - `description`: Item description
  - `price_per_unit`: Price in gold
  - `quantity_selected`: Number of items
  - `total_cost`: Total cost
  - `energy`: Energy restoration (e.g., "+13" or "")
  - `health`: Health restoration (e.g., "+5" or "")
- `annotated_by`: "auto", "human", "human_verified"
- `created_at`: ISO 8601 timestamp
- `version`: Schema version

## Stats
- Total images: 22
- Annotated: Check quality_report.json for current status
- Resolution: 1600×1200 (iPad screenshots)

## Next Steps
- Generate train/val/test splits (65%/20%/15%)
- Manual test image selection (where left panel ≠ right panel)
- Train VLM orchestrator

## See Also
- Annotation schema: `configs/annotation_schema.json`
- Annotation scripts: `scripts/annotate_pierre_shop.py`, `scripts/interactive_annotate.py`
