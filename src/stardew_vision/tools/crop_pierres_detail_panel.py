"""
Pierre's General Store detail panel OCR extraction agent.

Locates the panel via multi-scale OpenCV template matching, then extracts
text fields using PaddleOCR PP-OCRv5 (CPU-only).

All crop coordinates are stored and computed as relative fractions (0.0–1.0)
so the extractor works at any resolution (1080p, 1440p, 4K).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import cv2
import numpy as np


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_TEMPLATES_DIR = Path(__file__).parents[4] / "datasets" / "assets" / "templates"
_LAYOUT_FILE = _TEMPLATES_DIR / "panel_layout.json"
_TEMPLATE_FILE = _TEMPLATES_DIR / "pierres_detail_panel_corner.png"

# Stardew Valley's discrete UI scale factors
_MATCH_SCALES = [0.75, 1.0, 1.25, 1.5]

# Confidence threshold for template matching
_MATCH_THRESHOLD = 0.85


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class PanelNotFoundError(Exception):
    """Raised when the Pierre's shop detail panel cannot be located."""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _load_ocr():
    """Lazy-load PaddleOCR to avoid import-time GPU initialisation."""
    from paddleocr import PaddleOCR

    return PaddleOCR(
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
        lang="en",
        device="cpu",
    )


def locate_panel(
    img: np.ndarray, template: np.ndarray
) -> tuple[float, float, float, float, float, float]:
    """
    Multi-scale template matching to find the panel corner in *img*.

    Returns (rel_x, rel_y, rel_w, rel_h, best_scale, confidence) where all
    spatial values are relative fractions of the image dimensions.

    Raises PanelNotFoundError if best confidence < _MATCH_THRESHOLD.
    """
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

    if best_conf < _MATCH_THRESHOLD:
        raise PanelNotFoundError(
            f"Panel not found (best confidence {best_conf:.3f} < {_MATCH_THRESHOLD}). "
            "Ensure the anchor template matches the screenshot's UI."
        )

    # The template anchors the top-left corner of the panel.
    # Use the template dimensions as the detected panel width/height baseline.
    px, py = best_loc
    rel_x = px / img_w
    rel_y = py / img_h
    rel_w = best_tw / img_w
    rel_h = best_th / img_h

    return rel_x, rel_y, rel_w, rel_h, best_scale, best_conf


def crop_panel(img: np.ndarray, rel_box: tuple[float, float, float, float]) -> np.ndarray:
    """Crop *img* using relative (x, y, w, h) fractions."""
    h, w = img.shape[:2]
    rx, ry, rw, rh = rel_box
    x0 = int(rx * w)
    y0 = int(ry * h)
    x1 = int((rx + rw) * w)
    y1 = int((ry + rh) * h)
    return img[y0:y1, x0:x1]


def run_ocr(cropped: np.ndarray) -> list[dict]:
    """
    Run PaddleOCR on a cropped panel image.

    Returns a list of dicts: {text, score, rel_y} where rel_y is the
    vertical centre of the text block as a fraction of the cropped panel height.
    """
    ocr = _load_ocr()
    panel_h = cropped.shape[0]
    result = ocr.ocr(cropped, cls=False)

    records = []
    # PaddleOCR 3.x returns a list of pages; each page is a list of lines.
    if not result:
        return records

    lines = result[0] if isinstance(result[0], list) else result
    if lines is None:
        return records

    for line in lines:
        if line is None:
            continue
        # Each line: [[x1,y1],[x2,y2],[x3,y3],[x4,y4]], (text, score)
        box, (text, score) = line
        ys = [pt[1] for pt in box]
        centre_y = (min(ys) + max(ys)) / 2
        rel_y = centre_y / panel_h if panel_h > 0 else 0.0
        records.append({"text": text, "score": float(score), "rel_y": rel_y})

    return records


def parse_pierre_fields(ocr_results: list[dict]) -> dict:
    """
    Assign OCR text blocks to Pierre's shop fields by relative Y position.

    Panel layout (approximate relative Y within the cropped detail panel):
      0.00 – 0.20  → item name
      0.20 – 0.55  → description (may span multiple lines)
      0.55 – 1.00  → price / quantity / total rows
    """
    sorted_results = sorted(ocr_results, key=lambda r: r["rel_y"])

    name_parts: list[str] = []
    desc_parts: list[str] = []
    price_texts: list[tuple[float, str]] = []

    price_pattern = re.compile(r"(\d[\d,]*)\s*[Gg]?$")

    for rec in sorted_results:
        text = rec["text"].strip()
        y = rec["rel_y"]

        if y < 0.20:
            name_parts.append(text)
        elif y < 0.55:
            desc_parts.append(text)
        else:
            price_texts.append((y, text))

    name = " ".join(name_parts).strip()
    description = " ".join(desc_parts).strip()

    # Extract numeric price values from the lower zone
    prices: list[tuple[float, int]] = []
    for y, text in price_texts:
        m = price_pattern.search(text)
        if m:
            val = int(m.group(1).replace(",", ""))
            prices.append((y, val))

    # Assign price fields by position
    # Expected order (top to bottom in lower panel): price_per_unit, quantity, total
    price_per_unit = 0
    quantity_selected = 0
    total_cost = 0

    # Quantity is usually a plain integer without 'g'; prices have 'g'
    qty_pattern = re.compile(r"^\d+$")
    qty_values: list[tuple[float, int]] = []
    price_g_values: list[tuple[float, int]] = []

    for y, text in price_texts:
        text_clean = text.strip()
        if qty_pattern.match(text_clean):
            qty_values.append((y, int(text_clean)))
        else:
            m = price_pattern.search(text_clean)
            if m:
                price_g_values.append((y, int(m.group(1).replace(",", ""))))

    if qty_values:
        quantity_selected = qty_values[0][1]

    if len(price_g_values) >= 2:
        price_g_values_sorted = sorted(price_g_values, key=lambda t: t[0])
        price_per_unit = price_g_values_sorted[0][1]
        total_cost = price_g_values_sorted[-1][1]
    elif len(price_g_values) == 1:
        price_per_unit = price_g_values[0][1]

    return {
        "name": name,
        "description": description,
        "price_per_unit": price_per_unit,
        "quantity_selected": quantity_selected,
        "total_cost": total_cost,
    }


def _load_panel_layout() -> dict:
    """Load panel_layout.json to get the panel's full relative bounding box."""
    if not _LAYOUT_FILE.exists():
        raise FileNotFoundError(
            f"panel_layout.json not found at {_LAYOUT_FILE}. "
            "Run scripts/extract_anchor_template.py first."
        )
    with open(_LAYOUT_FILE) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def crop_pierres_detail_panel(image_path: str | Path, debug: bool = False) -> dict:
    """
    Locate Pierre's shop detail panel in *image_path* and extract text fields.

    Parameters
    ----------
    image_path:
        Path to a Stardew Valley screenshot.
    debug:
        If True, print all OCR boxes and their relative Y positions.

    Returns
    -------
    dict with keys: name, description, price_per_unit, quantity_selected, total_cost.

    Raises
    ------
    PanelNotFoundError
        If the template match confidence is below 0.85.
    FileNotFoundError
        If the anchor template or panel_layout.json are missing.
    """
    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"Screenshot not found: {image_path}")

    if not _TEMPLATE_FILE.exists():
        raise FileNotFoundError(
            f"Anchor template not found at {_TEMPLATE_FILE}. "
            "Run scripts/extract_anchor_template.py first."
        )

    img = cv2.imread(str(image_path))
    if img is None:
        raise ValueError(f"Could not read image: {image_path}")

    template = cv2.imread(str(_TEMPLATE_FILE))
    if template is None:
        raise ValueError(f"Could not read template: {_TEMPLATE_FILE}")

    layout = _load_panel_layout()
    panel_rel = layout.get("panel_rel")
    if panel_rel is None:
        raise KeyError("panel_layout.json missing 'panel_rel' key.")

    # Locate the anchor corner to verify and scale
    rel_x, rel_y, rel_w, rel_h, scale, conf = locate_panel(img, template)

    if debug:
        print(f"Template match: confidence={conf:.3f}, scale={scale}, corner=({rel_x:.3f},{rel_y:.3f})")

    # Use the stored panel_rel dimensions scaled by the detected UI scale
    full_panel_rel = {
        "x": panel_rel["x"] * scale,
        "y": panel_rel["y"] * scale,
        "w": panel_rel["w"] * scale,
        "h": panel_rel["h"] * scale,
    }
    # Offset to the panel position detected via template match
    # The template covers the top-left corner; panel_rel is relative to the corner origin
    full_rel_box = (
        rel_x + full_panel_rel["x"] - full_panel_rel["x"],  # anchor IS the panel origin
        rel_y + full_panel_rel["y"] - full_panel_rel["y"],
        full_panel_rel["w"],
        full_panel_rel["h"],
    )
    # Simpler: the detected (rel_x, rel_y) is the panel top-left corner;
    # panel_rel["w"] and ["h"] give the full panel extent.
    full_rel_box = (rel_x, rel_y, full_panel_rel["w"], full_panel_rel["h"])

    panel_crop = crop_panel(img, full_rel_box)
    ocr_results = run_ocr(panel_crop)

    if debug:
        print("OCR results (sorted by rel_y):")
        for r in sorted(ocr_results, key=lambda x: x["rel_y"]):
            print(f"  rel_y={r['rel_y']:.3f}  score={r['score']:.3f}  text={r['text']!r}")

    return parse_pierre_fields(ocr_results)
