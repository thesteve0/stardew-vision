"""
Show raw PaddleOCR output for a cropped panel image.

Usage:
    python scripts/show_raw_ocr.py datasets/debug_crops/pierre_shop/IMG_7720.jpg
"""

import sys
from pathlib import Path

import cv2

from stardew_vision.tools.crop_pierres_detail_panel import _load_ocr

if len(sys.argv) < 2:
    sys.exit("Usage: python scripts/show_raw_ocr.py <image_path>")

img_path = Path(sys.argv[1])
if not img_path.exists():
    sys.exit(f"ERROR: file not found: {img_path}")

img = cv2.imread(str(img_path))
if img is None:
    sys.exit(f"ERROR: could not read image: {img_path}")

img = cv2.resize(img, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
panel_h = img.shape[0]
ocr = _load_ocr()
result = ocr.predict(img)
page = result[0]

print(f"\n{'y_px':>6}  {'rel_y':>5}  {'score':>5}  text")
print("-" * 50)
for text, score, poly in zip(page['rec_texts'], page['rec_scores'], page['rec_polys']):
    ys = [pt[1] for pt in poly]
    centre_y = (min(ys) + max(ys)) / 2
    rel_y = centre_y / panel_h
    print(f"{centre_y:6.1f}  {rel_y:.3f}  {score:.3f}  {text!r}")