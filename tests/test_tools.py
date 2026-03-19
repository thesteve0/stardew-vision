"""
Unit tests for the Pierre's shop OCR extraction tool.

Fixture screenshot goes in: tests/fixtures/pierre_shop_001.png
Ground truth values are set in GROUND_TRUTH below — update them to match
whatever the fixture screenshot actually shows.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

FIXTURES = Path(__file__).parent / "fixtures"
FIXTURE_SCREENSHOT = FIXTURES / "pierre_shop_001.png"
TEMPLATES_DIR = Path(__file__).parents[1] / "datasets" / "assets" / "templates"
TEMPLATE_FILE = TEMPLATES_DIR / "pierres_detail_panel_corner.png"
LAYOUT_FILE = TEMPLATES_DIR / "panel_layout.json"

# ---------------------------------------------------------------------------
# Ground truth — update these values to match your fixture screenshot
# ---------------------------------------------------------------------------
GROUND_TRUTH = {
    "name": "Parsnip",
    "price_per_unit": 20,
    "quantity_selected": 1,
    "total_cost": 20,
    # description checked by rapidfuzz ratio, not exact match
    "description_fragment": "parsnip",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fixture_available() -> bool:
    return FIXTURE_SCREENSHOT.exists() and TEMPLATE_FILE.exists() and LAYOUT_FILE.exists()


def _fixture_skip(reason: str = "Fixture screenshot or template not available"):
    return pytest.mark.skipif(not _fixture_available(), reason=reason)


# ---------------------------------------------------------------------------
# Tests that do NOT require a real fixture (unit-level)
# ---------------------------------------------------------------------------


def test_panel_not_found_raises(tmp_path):
    """Passing a solid-colour image should raise PanelNotFoundError."""
    from stardew_vision.tools.crop_pierres_detail_panel import (
        PanelNotFoundError,
        crop_pierres_detail_panel,
    )

    # Only run if a template exists (needed for the function to proceed to matching)
    if not TEMPLATE_FILE.exists() or not LAYOUT_FILE.exists():
        pytest.skip("Template not yet extracted — run scripts/extract_anchor_template.py")

    # Create a blank image that will never match the template
    blank = np.zeros((200, 200, 3), dtype=np.uint8)
    blank_path = tmp_path / "blank.png"

    import cv2
    cv2.imwrite(str(blank_path), blank)

    with pytest.raises(PanelNotFoundError):
        crop_pierres_detail_panel(blank_path)


def test_parse_pierre_fields_structure():
    """parse_pierre_fields always returns the five required keys."""
    from stardew_vision.tools.crop_pierres_detail_panel import parse_pierre_fields

    result = parse_pierre_fields([])
    assert set(result.keys()) == {"name", "description", "price_per_unit", "quantity_selected", "total_cost"}


def test_parse_pierre_fields_types():
    """Returned field types are correct even on empty input."""
    from stardew_vision.tools.crop_pierres_detail_panel import parse_pierre_fields

    result = parse_pierre_fields([])
    assert isinstance(result["name"], str)
    assert isinstance(result["description"], str)
    assert isinstance(result["price_per_unit"], int)
    assert isinstance(result["quantity_selected"], int)
    assert isinstance(result["total_cost"], int)


def test_parse_pierre_fields_price_parsing():
    """Numeric price extraction handles 'g' suffix and commas."""
    from stardew_vision.tools.crop_pierres_detail_panel import parse_pierre_fields

    ocr = [
        {"text": "Parsnip", "score": 0.99, "rel_y": 0.05},
        {"text": "A spring crop.", "score": 0.95, "rel_y": 0.30},
        {"text": "20g", "score": 0.97, "rel_y": 0.65},
        {"text": "1", "score": 0.98, "rel_y": 0.75},
        {"text": "20g", "score": 0.96, "rel_y": 0.85},
    ]
    result = parse_pierre_fields(ocr)
    assert result["name"] == "Parsnip"
    assert result["price_per_unit"] == 20
    assert result["quantity_selected"] == 1
    assert result["total_cost"] == 20


# ---------------------------------------------------------------------------
# Integration tests — require real fixture screenshot and template
# ---------------------------------------------------------------------------


@_fixture_skip()
def test_locate_panel_finds_match():
    """Template match confidence must be >= 0.85 on the fixture screenshot."""
    import cv2
    from stardew_vision.tools.crop_pierres_detail_panel import locate_panel

    img = cv2.imread(str(FIXTURE_SCREENSHOT))
    template = cv2.imread(str(TEMPLATE_FILE))
    assert img is not None, "Could not load fixture screenshot"
    assert template is not None, "Could not load template"

    _, _, _, _, _, conf = locate_panel(img, template)
    assert conf >= 0.85, f"Match confidence too low: {conf:.3f}"


@_fixture_skip()
def test_extract_returns_required_keys():
    """Full extraction returns all five required keys."""
    from stardew_vision.tools.crop_pierres_detail_panel import crop_pierres_detail_panel

    result = crop_pierres_detail_panel(FIXTURE_SCREENSHOT)
    assert set(result.keys()) == {"name", "description", "price_per_unit", "quantity_selected", "total_cost"}


@_fixture_skip()
def test_field_types():
    """Extracted name/description are str; price fields are int."""
    from stardew_vision.tools.crop_pierres_detail_panel import crop_pierres_detail_panel

    result = crop_pierres_detail_panel(FIXTURE_SCREENSHOT)
    assert isinstance(result["name"], str)
    assert isinstance(result["description"], str)
    assert isinstance(result["price_per_unit"], int)
    assert isinstance(result["quantity_selected"], int)
    assert isinstance(result["total_cost"], int)


@_fixture_skip()
def test_known_fixture_values():
    """Extracted values match ground truth for the fixture screenshot."""
    from rapidfuzz import fuzz
    from stardew_vision.tools.crop_pierres_detail_panel import crop_pierres_detail_panel

    result = crop_pierres_detail_panel(FIXTURE_SCREENSHOT)

    # String fields: rapidfuzz ratio >= 90
    name_ratio = fuzz.ratio(result["name"].lower(), GROUND_TRUTH["name"].lower())
    assert name_ratio >= 90, f"Name mismatch: got {result['name']!r}, ratio={name_ratio}"

    frag = GROUND_TRUTH["description_fragment"].lower()
    assert frag in result["description"].lower(), (
        f"Description fragment {frag!r} not found in {result['description']!r}"
    )

    # Numeric fields: exact match
    assert result["price_per_unit"] == GROUND_TRUTH["price_per_unit"], (
        f"price_per_unit: expected {GROUND_TRUTH['price_per_unit']}, got {result['price_per_unit']}"
    )
    assert result["quantity_selected"] == GROUND_TRUTH["quantity_selected"], (
        f"quantity_selected: expected {GROUND_TRUTH['quantity_selected']}, got {result['quantity_selected']}"
    )
    assert result["total_cost"] == GROUND_TRUTH["total_cost"], (
        f"total_cost: expected {GROUND_TRUTH['total_cost']}, got {result['total_cost']}"
    )
