"""
TV dialog OCR extraction tool.

Crops the dialog text box from a Stardew Valley TV screen screenshot
and extracts the dialog text using PaddleOCR.

The dialog box is at a fixed position (defined in tv_dialog_layout.json),
so no template matching is needed -- just crop and OCR.

Ported from stardew-vision-training/tools-code/crop_tv_dialog.py.
"""

from __future__ import annotations

from pathlib import Path

from stardew_ocr_tools.common import (
    crop_regions,
    decode_image_b64,
    load_image_from_path,
    load_layout,
    run_ocr,
)

_LAYOUT_FILE = "tv_dialog_layout.json"


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class DialogNotFoundError(Exception):
    """Raised when the TV dialog box cannot be located or OCR returns no text."""


def parse_tv_dialog_fields(ocr_results: list[dict]) -> dict:
    """Parse OCR results from a TV dialog box into structured fields."""
    dialog_text = " ".join(
        rec["text"].strip() for rec in ocr_results if rec["text"].strip()
    )

    return {
        "screen_type": "tv_dialog",
        "dialog_text": dialog_text,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def crop_tv_dialog(image_b64: str, debug: bool = False) -> dict:
    """
    Extract dialog text from a TV screen screenshot.

    Parameters
    ----------
    image_b64:
        Base64-encoded PNG or JPEG screenshot.
    debug:
        If True, include ``ocr_raw`` in the returned dict.

    Returns
    -------
    dict with keys: screen_type, dialog_text.
    When debug=True, also includes: ocr_raw (list[dict]).

    Raises
    ------
    DialogNotFoundError
        If OCR returns no text from the dialog region.
    """
    img = decode_image_b64(image_b64)
    layout = load_layout(_LAYOUT_FILE)

    cropped = crop_regions(img, layout)
    dialog_crop = cropped["dialog_box"]

    ocr_results = run_ocr(dialog_crop)

    if not ocr_results:
        raise DialogNotFoundError(
            "OCR returned no text from the dialog region. "
            "The dialog box may not be visible in this screenshot."
        )

    fields = parse_tv_dialog_fields(ocr_results)

    if debug:
        fields["ocr_raw"] = sorted(ocr_results, key=lambda r: r["rel_y"])

    return fields


def crop_tv_dialog_from_path(image_path: str | Path, debug: bool = False) -> dict:
    """Convenience wrapper that reads an image file from disk."""
    image_b64 = load_image_from_path(image_path)
    return crop_tv_dialog(image_b64, debug=debug)
