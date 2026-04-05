"""
Show raw PaddleOCR output on the extracted panel.
"""

from paddleocr import PaddleOCR
import pprint

# Initialize PaddleOCR
ocr = PaddleOCR(
    lang='en',
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    use_textline_orientation=False
)

# Run OCR
panel_path = 'datasets/assets/templates/pierres_detail_panel_corner.png'
result = ocr.predict(panel_path)

# Print raw result
print("\n" + "=" * 80)
print("RAW PADDLEOCR OUTPUT:")
print("=" * 80)
pprint.pprint(result, width=120)
