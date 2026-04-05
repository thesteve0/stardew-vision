"""
Crop a horizontal band from a panel image and run OCR on it.

Useful for diagnosing missed text blocks by isolating a specific y-range.

Usage:
    python scripts/show_subregion_ocr.py <image_path> <y_start> <y_end>

Example:
    python scripts/show_subregion_ocr.py datasets/debug_crops/pierre_shop/IMG_7720.jpg 110 175
"""

import sys
from pathlib import Path

import cv2

from stardew_vision.tools.crop_pierres_detail_panel import _load_ocr

if len(sys.argv) < 4:
    sys.exit("Usage: python scripts/show_subregion_ocr.py <image_path> <y_start> <y_end>")

img_path = Path(sys.argv[1])
y_start = int(sys.argv[2])
y_end = int(sys.argv[3])

img = cv2.imread(str(img_path))
if img is None:
    sys.exit(f"ERROR: could not read image: {img_path}")

subregion = img[y_start:y_end, :, :]

out_path = Path("/tmp") / f"subregion_{img_path.stem}_{y_start}_{y_end}.png"
cv2.imwrite(str(out_path), subregion)
print(f"Subregion saved to: {out_path}  (size: {subregion.shape[1]}x{subregion.shape[0]}px)")

ocr = _load_ocr()
result = ocr.predict(subregion)
page = result[0]

print(f"\n{'y_px':>6}  {'score':>5}  text")
print("-" * 40)
if not page['rec_texts']:
    print("  (no text detected)")
else:
    for text, score, poly in zip(page['rec_texts'], page['rec_scores'], page['rec_polys']):
        ys = [pt[1] for pt in poly]
        centre_y = (min(ys) + max(ys)) / 2
        print(f"{centre_y:6.1f}  {score:.3f}  {text!r}")