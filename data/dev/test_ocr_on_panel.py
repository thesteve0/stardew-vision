"""
Test PaddleOCR on the extracted Pierre's shop detail panel.

Usage:
    python scripts/test_ocr_on_panel.py
"""

from paddleocr import PaddleOCR
import cv2
import os

# Disable OneDNN optimizations that seem to be causing issues
os.environ['FLAGS_use_mkldnn'] = '0'

# Initialize PaddleOCR with CPU-only and minimal preprocessing
ocr = PaddleOCR(
    lang='en',
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    use_textline_orientation=False
)

# Load the extracted panel
panel_path = 'datasets/assets/templates/pierres_detail_panel_corner.png'
img = cv2.imread(panel_path)

if img is None:
    print(f"Error: Could not load {panel_path}")
    exit(1)

print(f"Panel image loaded: {img.shape[1]}x{img.shape[0]} pixels")
print("\nRunning PaddleOCR...\n")

# Run OCR using the predict API
result = ocr.predict(panel_path)

# Display results
print("=" * 80)
print("OCR Results")
print("=" * 80)

if result and result[0]:
    for idx, line in enumerate(result[0]):
        bbox, (text, confidence) = line
        # bbox is [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
        x_coords = [point[0] for point in bbox]
        y_coords = [point[1] for point in bbox]
        x_min, x_max = int(min(x_coords)), int(max(x_coords))
        y_min, y_max = int(min(y_coords)), int(max(y_coords))

        print(f"\n[{idx+1}] Text: '{text}'")
        print(f"    Confidence: {confidence:.3f}")
        print(f"    Position: x={x_min}-{x_max}, y={y_min}-{y_max}")
        print(f"    Size: {x_max-x_min}×{y_max-y_min} pixels")
else:
    print("No text detected!")

print("\n" + "=" * 80)
print(f"Total text regions detected: {len(result[0]) if result and result[0] else 0}")
print("=" * 80)
