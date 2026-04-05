"""
Evaluate template matching quality across all Pierre's shop images.

Bypasses the confidence threshold so every image produces a crop, then saves
the cropped panels to datasets/debug_crops/pierre_shop/ for visual inspection.

Usage:
    python scripts/eval_crop_quality.py
"""

import json
import sys
from pathlib import Path

import cv2
import numpy as np

from stardew_vision.tools.crop_pierres_detail_panel import _MATCH_SCALES, crop_panel

IMAGES_DIR = Path(__file__).parents[1] / "datasets" / "pierre_shop" / "images"
TEMPLATE_FILE = Path(__file__).parents[1] / "datasets" / "assets" / "templates" / "pierres_detail_panel_corner.png"
LAYOUT_FILE = Path(__file__).parents[1] / "datasets" / "assets" / "templates" / "pierre_panel_layout.json"
OUT_DIR = Path(__file__).parents[1] / "datasets" / "debug_crops" / "pierre_shop"

OUT_DIR.mkdir(parents=True, exist_ok=True)


def locate_panel_no_threshold(img: np.ndarray, template: np.ndarray):
    """Like locate_panel() but always returns the best match regardless of confidence."""
    img_h, img_w = img.shape[:2]
    tmpl_h, tmpl_w = template.shape[:2]
    img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    tmpl_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)

    best_conf = -1.0
    best_loc = (0, 0)
    best_scale = 1.0
    best_tw = tmpl_w
    best_th = tmpl_h

    for scale in _MATCH_SCALES:
        sw = max(1, int(tmpl_w * scale))
        sh = max(1, int(tmpl_h * scale))
        scaled = cv2.resize(tmpl_gray, (sw, sh), interpolation=cv2.INTER_AREA)

        if scaled.shape[0] > img_gray.shape[0] or scaled.shape[1] > img_gray.shape[1]:
            continue

        result = cv2.matchTemplate(img_gray, scaled, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if max_val > best_conf:
            best_conf = max_val
            best_loc = max_loc
            best_scale = scale
            best_tw = sw
            best_th = sh

    px, py = best_loc
    rel_x = px / img_w
    rel_y = py / img_h
    rel_w = best_tw / img_w
    rel_h = best_th / img_h

    return rel_x, rel_y, rel_w, rel_h, best_scale, best_conf


template = cv2.imread(str(TEMPLATE_FILE))
if template is None:
    sys.exit(f"ERROR: Could not read template at {TEMPLATE_FILE}")

with open(LAYOUT_FILE) as f:
    layout = json.load(f)
panel_rel = layout["panel_rel"]

images = sorted(IMAGES_DIR.glob("*.jpg")) + sorted(IMAGES_DIR.glob("*.png"))

rows = []
for img_path in images:
    img = cv2.imread(str(img_path))
    if img is None:
        rows.append((img_path.name, None, None, "UNREADABLE"))
        continue

    rel_x, rel_y, rel_w, rel_h, scale, conf = locate_panel_no_threshold(img, template)

    scaled_w = panel_rel["w"] * scale
    scaled_h = panel_rel["h"] * scale
    panel_crop = crop_panel(img, (rel_x, rel_y, scaled_w, scaled_h))

    out_path = OUT_DIR / img_path.name
    cv2.imwrite(str(out_path), panel_crop)

    passes = conf >= 0.85
    rows.append((img_path.name, conf, scale, "PASS" if passes else "FAIL"))

rows.sort(key=lambda r: r[1] if r[1] is not None else -1)

print(f"\n{'Filename':<25} {'Conf':>6}  {'Scale':>5}  {'Status'}")
print("-" * 55)
for name, conf, scale, status in rows:
    conf_str = f"{conf:.3f}" if conf is not None else "  N/A"
    scale_str = f"{scale:.2f}" if scale is not None else "  N/A"
    print(f"{name:<25} {conf_str:>6}  {scale_str:>5}  {status}")

passed = sum(1 for r in rows if r[3] == "PASS")
print(f"\n{passed}/{len(rows)} images pass the 0.85 threshold")
print(f"Cropped panels saved to: {OUT_DIR}")