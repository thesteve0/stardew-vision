"""
Run OCR on all pre-cropped Pierre's shop panels and write results to a CSV.

Reads crops from datasets/debug_crops/pierre_shop/, runs OCR + field parsing
on each, and writes one row per image to results.csv in the same directory.

Also joins against annotations.jsonl to include ground truth for comparison.

Usage:
    python scripts/eval_ocr_quality.py
"""

import csv
import json
import sys
from pathlib import Path

import cv2

from stardew_vision.tools.crop_pierres_detail_panel import parse_pierre_fields, run_ocr

CROPS_DIR = Path(__file__).parents[1] / "datasets" / "debug_crops" / "pierre_shop"
ANNOTATIONS = Path(__file__).parents[1] / "datasets" / "pierre_shop" / "annotations.jsonl"
OUT_CSV = CROPS_DIR / "results.csv"

# Load ground truth keyed by original_file_name
ground_truth = {}
with open(ANNOTATIONS) as f:
    for line in f:
        ann = json.loads(line)
        ground_truth[ann["original_file_name"]] = ann["expected_extraction"]

crops = sorted(CROPS_DIR.glob("*.jpg")) + sorted(CROPS_DIR.glob("*.png"))

fieldnames = [
    "filename",
    "extracted_name",
    "extracted_description",
    "extracted_price_per_unit",
    "extracted_quantity_selected",
    "extracted_total_cost",
    "extracted_energy",
    "extracted_health",
    "gt_name",
    "gt_description",
    "gt_price_per_unit",
    "gt_quantity_selected",
    "gt_total_cost",
    "gt_energy",
    "gt_health",
]

rows = []
for crop_path in crops:
    img = cv2.imread(str(crop_path))
    if img is None:
        print(f"WARNING: could not read {crop_path.name}")
        continue

    ocr_results = run_ocr(img)
    extracted = parse_pierre_fields(ocr_results)
    gt = ground_truth.get(crop_path.name, {})

    rows.append({
        "filename": crop_path.name,
        "extracted_name": extracted["name"],
        "extracted_description": extracted["description"],
        "extracted_price_per_unit": extracted["price_per_unit"],
        "extracted_quantity_selected": extracted["quantity_selected"],
        "extracted_total_cost": extracted["total_cost"],
        "extracted_energy": extracted["energy"],
        "extracted_health": extracted["health"],
        "gt_name": gt.get("name", ""),
        "gt_description": gt.get("description", ""),
        "gt_price_per_unit": gt.get("price_per_unit", ""),
        "gt_quantity_selected": gt.get("quantity_selected", ""),
        "gt_total_cost": gt.get("total_cost", ""),
        "gt_energy": gt.get("energy", ""),
        "gt_health": gt.get("health", ""),
    })
    print(f"  {crop_path.name}: {extracted['name']!r}  price={extracted['price_per_unit']}  qty={extracted['quantity_selected']}  total={extracted['total_cost']}")

with open(OUT_CSV, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print(f"\nWrote {len(rows)} rows to {OUT_CSV}")
