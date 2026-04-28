"""
Shared utilities for Stardew Vision OCR extraction tools.

Provides lazy-loaded PaddleOCR, image decoding, region cropping,
and layout JSON loading used by all screen-type extraction tools.

Ported from stardew-vision-training/tools-code/common.py with
import paths updated for the stardew_ocr_tools package.
"""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path

import cv2
import numpy as np

# Assets directory — sprites, manifest, templates
_ASSETS_DIR = Path(
    os.getenv(
        "ASSETS_DIR",
        str(Path(__file__).resolve().parent.parent / "assets"),
    )
)

# Templates directory — layout JSONs live here
_TEMPLATES_DIR = Path(
    os.getenv(
        "TEMPLATES_DIR",
        str(_ASSETS_DIR / "templates"),
    )
)

_SPRITES_DIR = _ASSETS_DIR / "sprites"
_MANIFEST_PATH = _ASSETS_DIR / "item_manifest.json"

# ---------------------------------------------------------------------------
# PaddleOCR lazy loading
# ---------------------------------------------------------------------------

_OCR_INSTANCE = None


def load_ocr():
    """Lazy-load PaddleOCR PP-OCRv5 (CPU-only).

    The instance is cached module-level to avoid the ~30s model reload
    penalty between calls.
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


# ---------------------------------------------------------------------------
# Image helpers
# ---------------------------------------------------------------------------


def strip_letterbox(image: np.ndarray, threshold: float = 10.0) -> np.ndarray:
    """Remove black letterbox borders from a screenshot.

    Scans rows and columns for near-black regions (mean pixel value below
    *threshold*) and crops to the content area. Safe to call on images
    without borders -- returns the original array unchanged.
    """
    row_means = image.mean(axis=(1, 2))
    col_means = image.mean(axis=(0, 2))

    non_black_rows = np.where(row_means > threshold)[0]
    non_black_cols = np.where(col_means > threshold)[0]

    if len(non_black_rows) == 0 or len(non_black_cols) == 0:
        return image

    top = non_black_rows[0]
    bottom = non_black_rows[-1] + 1
    left = non_black_cols[0]
    right = non_black_cols[-1] + 1

    if top == 0 and bottom == image.shape[0] and left == 0 and right == image.shape[1]:
        return image

    return image[top:bottom, left:right].copy()


def decode_image_b64(image_b64: str) -> np.ndarray:
    """Decode a base64-encoded image to a BGR numpy array.

    Automatically strips black letterbox borders so that downstream
    layout coordinates (relative 0.0-1.0) align with actual game content.
    """
    img_bytes = base64.b64decode(image_b64)
    img_array = np.frombuffer(img_bytes, dtype=np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image from base64 data.")
    return strip_letterbox(img)


def load_image_from_path(image_path: str | Path) -> str:
    """Read an image file and return its base64-encoded contents."""
    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"Screenshot not found: {image_path}")
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


# ---------------------------------------------------------------------------
# Layout JSON
# ---------------------------------------------------------------------------


def load_layout(layout_filename: str) -> dict:
    """Load a layout JSON file from the templates directory.

    Parameters
    ----------
    layout_filename:
        Filename (not full path), e.g. "tv_dialog_layout.json".

    Returns
    -------
    Parsed layout dict with screen_type, extracted_from_resolution, and regions.
    """
    layout_path = _TEMPLATES_DIR / layout_filename
    if not layout_path.exists():
        raise FileNotFoundError(
            f"Layout file not found at {layout_path}. "
            f"Expected in templates directory: {_TEMPLATES_DIR}"
        )
    with open(layout_path) as f:
        layout = json.load(f)

    required = ["screen_type", "extracted_from_resolution", "regions"]
    for key in required:
        if key not in layout:
            raise KeyError(f"Layout JSON missing required key '{key}': {layout_path}")

    return layout


# ---------------------------------------------------------------------------
# Region cropping
# ---------------------------------------------------------------------------


def crop_region(image: np.ndarray, region: dict) -> np.ndarray:
    """Crop a region from an image using relative coordinates.

    Parameters
    ----------
    image:
        Source image (BGR numpy array).
    region:
        Dict with keys x, y, w, h (all floats 0.0-1.0).
    """
    img_h, img_w = image.shape[:2]

    x_px = int(region["x"] * img_w)
    y_px = int(region["y"] * img_h)
    w_px = int(region["w"] * img_w)
    h_px = int(region["h"] * img_h)

    # Clamp to image bounds
    x_px = max(0, min(x_px, img_w - 1))
    y_px = max(0, min(y_px, img_h - 1))
    w_px = min(w_px, img_w - x_px)
    h_px = min(h_px, img_h - y_px)

    return image[y_px : y_px + h_px, x_px : x_px + w_px]


def crop_regions(image: np.ndarray, layout: dict) -> dict[str, np.ndarray]:
    """Crop all regions defined in a layout, respecting parent relationships.

    Regions with a "parent" key are cropped from the parent's cropped image
    rather than from the full image.
    """
    regions = layout["regions"]
    cropped = {}

    # Pass 1: regions without a parent
    for name, region in regions.items():
        if "parent" not in region:
            cropped[name] = crop_region(image, region)

    # Pass 2: regions with a parent
    for name, region in regions.items():
        if "parent" in region:
            parent_name = region["parent"]
            if parent_name not in cropped:
                raise KeyError(
                    f"Region '{name}' references parent '{parent_name}' "
                    f"which was not found or has not been cropped yet."
                )
            cropped[name] = crop_region(cropped[parent_name], region)

    return cropped


# ---------------------------------------------------------------------------
# OCR runner
# ---------------------------------------------------------------------------


def run_ocr(
    cropped: np.ndarray,
    upscale: float = 2.0,
    min_confidence: float = 0.5,
) -> list[dict]:
    """Run PaddleOCR on a cropped image region.

    Parameters
    ----------
    cropped:
        Cropped image (BGR numpy array).
    upscale:
        Scale factor before OCR (default 2x improves accuracy on game text).
    min_confidence:
        Minimum OCR confidence score (0.0-1.0).

    Returns
    -------
    List of dicts: {text, score, rel_x, rel_y} sorted in reading order.
    """
    ocr = load_ocr()
    upscaled = cv2.resize(
        cropped, None, fx=upscale, fy=upscale, interpolation=cv2.INTER_CUBIC
    )
    panel_h = upscaled.shape[0]
    panel_w = upscaled.shape[1]
    result = ocr.predict(upscaled)

    records = []
    if not result or not result[0]:
        return records

    page = result[0]
    if not isinstance(page, dict):
        return records

    texts = page.get("rec_texts", [])
    scores = page.get("rec_scores", [])
    polys = page.get("rec_polys", [])

    for text, score, poly in zip(texts, scores, polys):
        if poly is None:
            continue
        if score < min_confidence:
            continue
        ys = [pt[1] for pt in poly]
        xs = [pt[0] for pt in poly]
        centre_y = (min(ys) + max(ys)) / 2
        centre_x = (min(xs) + max(xs)) / 2
        rel_y = centre_y / panel_h if panel_h > 0 else 0.0
        rel_x = centre_x / panel_w if panel_w > 0 else 0.0
        records.append({
            "text": text,
            "score": float(score),
            "rel_x": rel_x,
            "rel_y": rel_y,
        })

    records = sort_reading_order(records)
    return records


# ---------------------------------------------------------------------------
# Fish sprite & manifest loading
# ---------------------------------------------------------------------------

_FISH_NAMES: dict[str, str] | None = None
_FISH_SPRITES: dict[str, np.ndarray] | None = None


def load_manifest_fish() -> dict[str, str]:
    """Load item manifest and return fish lookup: item_id -> fish name."""
    global _FISH_NAMES
    if _FISH_NAMES is None:
        if not _MANIFEST_PATH.exists():
            raise FileNotFoundError(f"Item manifest not found: {_MANIFEST_PATH}")
        with open(_MANIFEST_PATH) as f:
            data = json.load(f)
        _FISH_NAMES = {}
        for item_id, item in data.items():
            if isinstance(item, dict) and item.get("type") == "Fish":
                name = item.get("name")
                if name is not None:
                    _FISH_NAMES[item_id] = name
    return _FISH_NAMES


def load_fish_sprites() -> dict[str, np.ndarray]:
    """Load all fish sprite images (16x16 RGBA). Cached after first call."""
    global _FISH_SPRITES
    if _FISH_SPRITES is None:
        if not _MANIFEST_PATH.exists():
            raise FileNotFoundError(f"Item manifest not found: {_MANIFEST_PATH}")
        with open(_MANIFEST_PATH) as f:
            data = json.load(f)
        _FISH_SPRITES = {}
        for item_id, item in data.items():
            if isinstance(item, dict) and item.get("type") == "Fish":
                sprite_file = item.get("sprite_file")
                if sprite_file is None:
                    continue
                path = _ASSETS_DIR / sprite_file
                if path.exists():
                    img = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
                    if img is not None:
                        _FISH_SPRITES[item_id] = img
    return _FISH_SPRITES


def sort_reading_order(
    records: list[dict], line_threshold: float = 0.03
) -> list[dict]:
    """Sort OCR records into reading order (top-to-bottom, left-to-right).

    Text blocks whose rel_y values are within *line_threshold* of each other
    are considered to be on the same line and sorted left-to-right by rel_x.
    """
    if not records:
        return records

    by_y = sorted(records, key=lambda r: r["rel_y"])

    lines: list[list[dict]] = []
    current_line: list[dict] = [by_y[0]]

    for rec in by_y[1:]:
        if abs(rec["rel_y"] - current_line[0]["rel_y"]) <= line_threshold:
            current_line.append(rec)
        else:
            lines.append(current_line)
            current_line = [rec]
    lines.append(current_line)

    result = []
    for line in lines:
        result.extend(sorted(line, key=lambda r: r["rel_x"]))

    return result
