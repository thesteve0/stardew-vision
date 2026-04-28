"""
Caught fish notification OCR extraction tool.

Two-stage extraction from the fish-caught notification in Stardew Valley:
1. Crop the notification speech bubble from the full screenshot
2. Crop the fish sprite from the notification (for sprite matching)
3. Run OCR on the notification to extract length text

The fish name is NOT available via OCR (cropped by enlarged UI) -- it must
be identified by sprite matching against datasets/assets/sprites/.

Ported from stardew-vision-training/tools-code/crop_caught_fish.py.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

import cv2
import numpy as np

logger = logging.getLogger(__name__)

from stardew_ocr_tools.common import (
    crop_regions,
    decode_image_b64,
    load_fish_sprites,
    load_image_from_path,
    load_layout,
    load_manifest_fish,
    run_ocr,
)

_LAYOUT_FILE = "caught_fish_layout.json"


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class FishNotFoundError(Exception):
    """Raised when the caught fish notification cannot be located or parsed."""


# ---------------------------------------------------------------------------
# Fish sprite matching
# ---------------------------------------------------------------------------


def _detect_frame_boundary(fish_sprite_crop: np.ndarray, gradient_threshold: int = 15) -> np.ndarray:
    """Trim variable speech-bubble edges outside the wooden frame.

    Scans inward from each edge along the center row/column, looking for
    the first sharp brightness gradient (the frame's outer edge).  This
    keeps the entire frame + interior while removing the surrounding
    speech-bubble pixels that shift with player position.
    """
    gray = cv2.cvtColor(fish_sprite_crop, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape

    mid_y = h // 2
    row_grad = np.abs(np.diff(gray[mid_y, :].astype(np.int16)))
    left = 0
    for i in range(len(row_grad)):
        if row_grad[i] > gradient_threshold:
            left = i + 1
            break
    right = w
    for i in range(len(row_grad) - 1, -1, -1):
        if row_grad[i] > gradient_threshold:
            right = i
            break

    mid_x = w // 2
    col_grad = np.abs(np.diff(gray[:, mid_x].astype(np.int16)))
    top = 0
    for i in range(len(col_grad)):
        if col_grad[i] > gradient_threshold:
            top = i + 1
            break
    bottom = h
    for i in range(len(col_grad) - 1, -1, -1):
        if col_grad[i] > gradient_threshold:
            bottom = i
            break

    return fish_sprite_crop[top:bottom, left:right]


def match_fish_sprite(
    fish_sprite_crop: np.ndarray,
    scale_range: tuple[int, int] = (6, 18),
    match_threshold: float = 0.50,
) -> dict:
    """Identify the fish by template matching against the sprite library.

    Steps:
        1. Detect the wooden frame boundary and trim variable outer edges
        2. Convert to grayscale (the game applies color shifts to sprites)
        3. Composite each sprite onto white, convert to grayscale, upscale
        4. Run cv2.matchTemplate (TM_CCOEFF_NORMED) for each
        5. Return the best match above threshold, with fish name from manifest
    """
    inner = _detect_frame_boundary(fish_sprite_crop)

    if inner.shape[2] == 4:
        inner = cv2.cvtColor(inner, cv2.COLOR_BGRA2BGR)
    inner_gray = cv2.cvtColor(inner, cv2.COLOR_BGR2GRAY)

    fish_sprites = load_fish_sprites()
    fish_names = load_manifest_fish()

    best_score = -1.0
    best_id = None

    inner_h, inner_w = inner_gray.shape[:2]

    for item_id, sprite_rgba in fish_sprites.items():
        if sprite_rgba.shape[2] == 4:
            alpha = sprite_rgba[:, :, 3:4].astype(np.float32) / 255.0
            bgr = sprite_rgba[:, :, :3].astype(np.float32)
            white_bg = np.full_like(bgr, 255.0)
            composited = (bgr * alpha + white_bg * (1.0 - alpha)).astype(np.uint8)
        else:
            composited = sprite_rgba

        comp_gray = cv2.cvtColor(composited, cv2.COLOR_BGR2GRAY)

        for scale in range(scale_range[0], scale_range[1]):
            scaled = cv2.resize(
                comp_gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_NEAREST
            )

            if scaled.shape[0] > inner_h or scaled.shape[1] > inner_w:
                continue

            result = cv2.matchTemplate(inner_gray, scaled, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(result)

            if max_val > best_score:
                best_score = max_val
                best_id = item_id

    logger.info(
        "Sprite matching: crop=%dx%d inner=%dx%d best_score=%.4f best_id=%s scales_tested=%d-%d",
        fish_sprite_crop.shape[1], fish_sprite_crop.shape[0],
        inner_w, inner_h, best_score,
        best_id, scale_range[0], scale_range[1] - 1,
    )

    if best_score < match_threshold:
        logger.warning(
            "Sprite match below threshold (%.4f < %.2f). Best candidate: %s (%s)",
            best_score, match_threshold,
            fish_names.get(best_id, "?") if best_id else "none",
            best_id,
        )
        return {
            "fish_name": None,
            "item_id": None,
            "match_score": round(float(best_score), 4),
        }

    return {
        "fish_name": fish_names.get(best_id, f"Unknown ({best_id})"),
        "item_id": best_id,
        "match_score": round(float(best_score), 4),
    }


# ---------------------------------------------------------------------------
# Field parsing
# ---------------------------------------------------------------------------

_LENGTH_PATTERN = re.compile(r"(\d+)\s*in", re.IGNORECASE)


def parse_caught_fish_fields(ocr_results: list[dict]) -> dict:
    """Parse OCR results from the caught fish notification.

    Extracts the fish length from "Length: NN in." text.
    """
    full_text = " ".join(
        rec["text"].strip() for rec in ocr_results if rec["text"].strip()
    )

    length_inches = None
    length_match = _LENGTH_PATTERN.search(full_text)
    if length_match:
        length_inches = int(length_match.group(1))

    return {
        "screen_type": "caught_fish",
        "length_inches": length_inches,
        "ocr_text": full_text,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def crop_caught_fish(image_b64: str, debug: bool = False) -> dict:
    """
    Extract information from a caught fish notification screenshot.

    Uses two-stage cropping: notification bubble from full image, then
    fish sprite from the notification. OCR runs on the notification
    to extract the fish length.

    Parameters
    ----------
    image_b64:
        Base64-encoded PNG or JPEG screenshot.
    debug:
        If True, include ``ocr_raw`` and ``sprite_match`` in the returned dict.

    Returns
    -------
    dict with keys: screen_type, fish_name, length_inches, ocr_text.

    Raises
    ------
    FishNotFoundError
        If OCR returns no text from the notification region.
    """
    img = decode_image_b64(image_b64)
    logger.info(
        "Caught fish extraction: image=%dx%d",
        img.shape[1], img.shape[0],
    )
    layout = load_layout(_LAYOUT_FILE)

    cropped = crop_regions(img, layout)
    notification_crop = cropped["notification"]
    fish_sprite_crop = cropped["fish_sprite"]
    logger.info(
        "Cropped regions: notification=%dx%d fish_sprite=%dx%d",
        notification_crop.shape[1], notification_crop.shape[0],
        fish_sprite_crop.shape[1], fish_sprite_crop.shape[0],
    )

    # 3x upscale needed for the large game-font numbers in this notification
    ocr_results = run_ocr(notification_crop, upscale=3.0)

    if not ocr_results:
        raise FishNotFoundError(
            "OCR returned no text from the notification region. "
            "The caught fish notification may not be visible in this screenshot."
        )

    fields = parse_caught_fish_fields(ocr_results)

    # Fish identification via sprite matching
    sprite_result = match_fish_sprite(fish_sprite_crop)
    fields["fish_name"] = sprite_result["fish_name"]

    if debug:
        fields["ocr_raw"] = sorted(ocr_results, key=lambda r: r["rel_y"])
        fields["sprite_match"] = sprite_result

    return fields


def crop_caught_fish_from_path(image_path: str | Path, debug: bool = False) -> dict:
    """Convenience wrapper that reads an image file from disk."""
    image_b64 = load_image_from_path(image_path)
    return crop_caught_fish(image_b64, debug=debug)
