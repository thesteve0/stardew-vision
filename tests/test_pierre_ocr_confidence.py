"""Regression tests for low-confidence background OCR in the unified service.

Run with the OCR service dependencies and its package on PYTHONPATH.
"""

import copy
import unittest
from unittest.mock import patch

import numpy as np

from stardew_ocr_tools.crop_pierres_detail_panel import (
    crop_pierres_detail_panel,
    parse_pierre_fields,
)


# Reproduced from debug=True on tests/fixtures/pierre_shop_001.png.
FIXTURE_OCR = [
    {"text": "Parsnip Seeds", "score": 0.9974854, "rel_y": 0.0373016},
    {"text": "Plant these in the spring.", "score": 0.9945222, "rel_y": 0.0701058},
    {"text": "Takes 4 days to mature.", "score": 0.9939421, "rel_y": 0.1013228},
    {"text": "20", "score": 0.9997009, "rel_y": 0.1394180},
    {"text": "2", "score": 0.1224076, "rel_y": 0.5362434},
    {"text": "x60: 1200", "score": 0.9980224, "rel_y": 0.9423280},
]


class PierreConfidenceTests(unittest.TestCase):
    def test_fixture_background_digit_is_rejected(self):
        records = copy.deepcopy(FIXTURE_OCR)
        self.assertEqual(parse_pierre_fields(records), {
            "name": "Parsnip Seeds",
            "description": "Plant these in the spring. Takes 4 days to mature.",
            "price_per_unit": 20,
            "quantity_selected": 60,
            "total_cost": 1200,
            "energy": "",
            "health": "",
        })
        self.assertEqual(records, FIXTURE_OCR)

    def test_confident_description_numbers_are_preserved(self):
        records = copy.deepcopy(FIXTURE_OCR)
        records[4]["score"] = 0.95
        self.assertTrue(parse_pierre_fields(records)["description"].endswith(". 2"))

    def test_confidence_boundary_and_empty_input(self):
        for score, expected in [(0.499, False), (0.5, True)]:
            records = copy.deepcopy(FIXTURE_OCR)
            records[4]["score"] = score
            self.assertEqual(parse_pierre_fields(records)["description"].endswith(". 2"), expected)
        self.assertEqual(parse_pierre_fields([])["description"], "")

    def test_weak_quantity_record_cannot_override_real_total(self):
        records = FIXTURE_OCR + [{"text": "x2: 99", "score": 0.1, "rel_y": 0.5}]
        fields = parse_pierre_fields(records)
        self.assertEqual((fields["quantity_selected"], fields["total_cost"]), (60, 1200))

    def test_debug_retains_rejected_record(self):
        module = "stardew_ocr_tools.crop_pierres_detail_panel"
        image = np.zeros((10, 10, 3), dtype=np.uint8)
        with patch(module + ".decode_image_b64", return_value=image), \
             patch(module + ".cv2.imread", return_value=image), \
             patch(module + ".locate_panel", return_value=(0, 0, 1, 1, 1, 1)), \
             patch(module + ".run_ocr_panel", return_value=FIXTURE_OCR):
            debug = crop_pierres_detail_panel("unused", debug=True)
            normal = crop_pierres_detail_panel("unused")
        self.assertEqual(debug["ocr_raw"], FIXTURE_OCR)
        self.assertNotIn("ocr_raw", normal)
        self.assertEqual(debug["description"], normal["description"])
        self.assertFalse(debug["description"].endswith(". 2"))


if __name__ == "__main__":
    unittest.main()
