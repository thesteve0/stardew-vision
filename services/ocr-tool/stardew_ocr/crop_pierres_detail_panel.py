"""
Pierre's General Store detail panel OCR extraction agent.

Locates the panel via multi-scale OpenCV template matching, then extracts
text fields using PaddleOCR PP-OCRv5 (CPU-only).

All crop coordinates are stored and computed as relative fractions (0.0–1.0)
so the extractor works at any resolution (1080p, 1440p, 4K).
"""

from __future__ import annotations

# CRITICAL: Set PaddleX/PaddleOCR environment variables BEFORE any imports
# that could trigger PaddleX initialization (which happens on paddleocr import)
import os
os.environ.setdefault('PADDLEX_HOME', '/tmp/.paddlex')
os.environ.setdefault('PADDLEX_CACHE_DIR', '/tmp/.paddlex/cache')
os.environ.setdefault('PADDLE_HUB_HOME', '/tmp/.paddlex/hub')
os.environ.setdefault('PADDLE_OCR_BASE_DIR', '/tmp/.paddleocr')

import base64
import json
import re
from pathlib import Path

import cv2
import numpy as np


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

# Templates are baked into container image at /app/assets/templates
# Self-contained within the ocr-tool service
import os
_TEMPLATES_DIR = Path(os.getenv("TEMPLATES_DIR", "/app/assets/templates"))
_LAYOUT_FILE = _TEMPLATES_DIR / "pierre_panel_layout.json"
_TEMPLATE_FILE = _TEMPLATES_DIR / "pierres_detail_panel_corner.png"

# Stardew Valley's discrete UI scale factors
_MATCH_SCALES = [1.0, 1.25, 1.5]

# Confidence threshold for template matching
_MATCH_THRESHOLD = 0.65


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class PanelNotFoundError(Exception):
    """Raised when the Pierre's shop detail panel cannot be located."""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

# Cache the OCR instance to avoid reloading models from disk on every request
# Models take ~30s to load into memory, so we keep the instance alive
_OCR_INSTANCE = None


def _load_ocr():
    """Lazy-load PaddleOCR to avoid import-time GPU initialisation.

    The OCR instance is cached in a module-level variable so models are loaded
    into memory once and reused across requests.
    """
    global _OCR_INSTANCE
    if _OCR_INSTANCE is None:
        from paddleocr import PaddleOCR
        _OCR_INSTANCE = PaddleOCR(
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            lang="en",
        )
    return _OCR_INSTANCE


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
    upscaled = cv2.resize(cropped, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
    panel_h = upscaled.shape[0]
    result = ocr.predict(upscaled)

    records = []
    # PaddleOCR 3.x returns a list with one dict containing 'rec_texts', 'rec_scores', 'rec_polys'
    if not result or not result[0]:
        return records

    page = result[0]
    if not isinstance(page, dict):
        return records

    texts = page.get('rec_texts', [])
    scores = page.get('rec_scores', [])
    polys = page.get('rec_polys', [])

    for text, score, poly in zip(texts, scores, polys):
        if poly is None:
            continue
        ys = [pt[1] for pt in poly]
        centre_y = (min(ys) + max(ys)) / 2
        rel_y = centre_y / panel_h if panel_h > 0 else 0.0
        records.append({"text": text, "score": float(score), "rel_y": rel_y})

    return records


def parse_pierre_fields(ocr_results: list[dict]) -> dict:
    """
    Extract Pierre's shop fields from OCR results.

    Strategy:
    - Name: topmost text block(s) (rel_y < 0.05)
    - Qty/total: detected by pattern "×N: total" regardless of position
    - Middle zone: everything between name and qty/total line
      - Price: a standalone number in the middle zone
      - Description: all remaining middle-zone text joined in reading order
    """
    sorted_results = sorted(ocr_results, key=lambda r: r["rel_y"])

    qty_total_pattern = re.compile(r"[x×](\d+):\s*(\d[\d,]*)")
    # Price line: leading digits, optional G/g suffix, optional single trailing digit
    # from the gold coin icon (OCR renders it as "0"), e.g. "100 0" or "30g" or "90 "
    price_pattern = re.compile(r"^([\d,]+)\s*(?:[Gg]|\d)?\s*$")
    energy_pattern = re.compile(r"\+(\d+)\s*[Ee]nergy")
    health_pattern = re.compile(r"\+(\d+)\s*[Hh]ealth")
    # Single stray characters are icon rendering artifacts, not text
    icon_artifact_pattern = re.compile(r"^[+HhEe]$")

    # First pass: find the qty/total line and its y position
    quantity_selected = 0
    total_cost = 0
    qty_total_y = 1.0
    for rec in sorted_results:
        m = qty_total_pattern.search(rec["text"])
        if m:
            quantity_selected = int(m.group(1))
            total_cost = int(m.group(2).replace(",", ""))
            qty_total_y = rec["rel_y"]
            break

    # Second pass: bucket remaining text into name vs middle zone
    name_parts: list[str] = []
    middle: list[tuple[float, str]] = []

    for rec in sorted_results:
        if qty_total_pattern.search(rec["text"]):
            continue
        text = rec["text"].strip()
        y = rec["rel_y"]
        if y < 0.05:
            name_parts.append(text)
        elif y < qty_total_y:
            middle.append((y, text))

    # Split middle zone into price, energy, health, and description
    price_per_unit = 0
    energy = ""
    health = ""
    desc_parts: list[str] = []

    for y, text in middle:
        if icon_artifact_pattern.match(text):
            continue
        energy_match = energy_pattern.search(text)
        if energy_match:
            energy = f"+{energy_match.group(1)}"
            continue
        health_match = health_pattern.search(text)
        if health_match:
            health = f"+{health_match.group(1)}"
            continue
        price_match = price_pattern.match(text)
        if price_match and price_per_unit == 0:
            price_per_unit = int(price_match.group(1).replace(",", ""))
        else:
            desc_parts.append(text)

    # Cross-validate total_cost using price × qty.
    # The gold coin icon next to the total can OCR as "0" and merge onto the
    # number (e.g. "30" + icon → "300"). If dropping the trailing digit gives
    # the expected product, correct it.
    if price_per_unit > 0 and quantity_selected > 0:
        expected = price_per_unit * quantity_selected
        if total_cost != expected:
            total_str = str(total_cost)
            if len(total_str) > 1:
                candidate = int(total_str[:-1])
                if candidate == expected:
                    total_cost = candidate

    return {
        "name": " ".join(name_parts).strip(),
        "description": " ".join(desc_parts).strip(),
        "price_per_unit": price_per_unit,
        "quantity_selected": quantity_selected,
        "total_cost": total_cost,
        "energy": energy,
        "health": health,
    }


def _load_panel_layout() -> dict:
    """Load pierre_panel_layout.json to get the panel's full relative bounding box."""
    if not _LAYOUT_FILE.exists():
        raise FileNotFoundError(
            f"pierre_panel_layout.json not found at {_LAYOUT_FILE}. "
            "Run scripts/extract_anchor_template.py first."
        )
    with open(_LAYOUT_FILE) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def crop_pierres_detail_panel(image_b64: str, debug: bool = False) -> dict:
    """
    Locate Pierre's shop detail panel in a base64-encoded screenshot and extract
    text fields.

    This is the production interface. The coordinating VLM receives the image,
    classifies the screen type, and emits a tool call. The webapp dispatch layer
    holds the original base64 image and passes it here — no shared filesystem
    required between pods.

    Parameters
    ----------
    image_b64:
        Base64-encoded PNG or JPEG screenshot bytes.
    debug:
        If True, include ``ocr_raw`` in the returned dict — a list of
        ``{text, score, rel_y}`` dicts in reading order (sorted by rel_y).
        Use this when the VLM needs to reason about raw OCR output to
        diagnose or correct extraction failures.

    Returns
    -------
    dict with keys: name, description, price_per_unit, quantity_selected,
    total_cost, energy, health.
    When debug=True, also includes: ocr_raw (list[dict]).

    Raises
    ------
    PanelNotFoundError
        If the template match confidence is below _MATCH_THRESHOLD.
    FileNotFoundError
        If the anchor template or pierre_panel_layout.json are missing.
    ValueError
        If the base64 data cannot be decoded to a valid image.
    """
    if not _TEMPLATE_FILE.exists():
        raise FileNotFoundError(
            f"Anchor template not found at {_TEMPLATE_FILE}. "
            "Run scripts/extract_anchor_template.py first."
        )

    img_bytes = base64.b64decode(image_b64)
    img_array = np.frombuffer(img_bytes, dtype=np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image from base64 data.")

    template = cv2.imread(str(_TEMPLATE_FILE))
    if template is None:
        raise ValueError(f"Could not read template: {_TEMPLATE_FILE}")

    layout = _load_panel_layout()
    panel_rel = layout.get("panel_rel")
    if panel_rel is None:
        raise KeyError("pierre_panel_layout.json missing 'panel_rel' key.")

    rel_x, rel_y, rel_w, rel_h, scale, conf = locate_panel(img, template)

    scaled_w = panel_rel["w"] * scale
    scaled_h = panel_rel["h"] * scale
    full_rel_box = (rel_x, rel_y, scaled_w, scaled_h)

    panel_crop = crop_panel(img, full_rel_box)
    ocr_results = run_ocr(panel_crop)

    fields = parse_pierre_fields(ocr_results)

    if debug:
        fields["ocr_raw"] = sorted(ocr_results, key=lambda r: r["rel_y"])

    return fields


def crop_pierres_detail_panel_from_path(image_path: str | Path, debug: bool = False) -> dict:
    """
    Convenience wrapper for local development and testing.

    Reads *image_path* from disk, encodes it to base64, and calls
    crop_pierres_detail_panel(). Prefer this in scripts and tests; use
    crop_pierres_detail_panel() directly in production (webapp dispatch layer).
    """
    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"Screenshot not found: {image_path}")
    with open(image_path, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode("utf-8")
    return crop_pierres_detail_panel(image_b64, debug=debug)
