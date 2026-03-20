"""
Anchor template extraction script for Pierre's shop detail panel.

Usage:
    python scripts/extract_anchor_template.py <screenshot_path> [--output-dir <dir>]

Interactively (or via terminal prompt) selects the panel corner region,
saves it as a PNG anchor template, and writes pierre_panel_layout.json with
relative coordinates.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import cv2
import numpy as np


def select_roi_interactive(img: np.ndarray) -> tuple[int, int, int, int]:
    """Use cv2.selectROI for interactive selection. Returns (x, y, w, h)."""
    print("Select the Pierre's shop detail panel region (drag a rectangle, then press ENTER or SPACE).")
    print("Press 'c' to cancel.")
    roi = cv2.selectROI("Select Panel Region", img, fromCenter=False, showCrosshair=True)
    cv2.destroyWindow("Select Panel Region")
    x, y, w, h = roi
    if w == 0 or h == 0:
        print("No region selected. Exiting.")
        sys.exit(1)
    return int(x), int(y), int(w), int(h)


def select_roi_terminal(img_shape: tuple[int, int]) -> tuple[int, int, int, int]:
    """Prompt user to enter x y w h from terminal. Returns (x, y, w, h)."""
    img_h, img_w = img_shape[:2]
    print(f"Image size: {img_w} x {img_h} pixels")
    print("Enter the panel region as: x y w h  (pixel coordinates, integers)")
    print("Tip: use a screenshot tool to find the coordinates.")
    raw = input("x y w h > ").strip()
    parts = raw.split()
    if len(parts) != 4:
        print("Expected 4 integers. Exiting.")
        sys.exit(1)
    x, y, w, h = (int(p) for p in parts)
    return x, y, w, h


def draw_debug(img: np.ndarray, x: int, y: int, w: int, h: int, out_path: Path) -> None:
    """Save a debug image with the selected region highlighted in green."""
    debug = img.copy()
    cv2.rectangle(debug, (x, y), (x + w, y + h), (0, 255, 0), 3)
    cv2.imwrite(str(out_path), debug)
    print(f"Debug image saved: {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract Pierre's shop panel anchor template.")
    parser.add_argument("screenshot", help="Path to Pierre's shop screenshot")
    parser.add_argument(
        "--output-dir",
        default="datasets/assets/templates",
        help="Directory to save template PNG and pierre_panel_layout.json (default: datasets/assets/templates)",
    )
    args = parser.parse_args()

    screenshot_path = Path(args.screenshot).resolve()
    output_dir = Path(args.output_dir).resolve()

    if not screenshot_path.exists():
        print(f"Error: screenshot not found: {screenshot_path}")
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    img = cv2.imread(str(screenshot_path))
    if img is None:
        print(f"Error: could not read image: {screenshot_path}")
        sys.exit(1)

    img_h, img_w = img.shape[:2]
    print(f"Loaded screenshot: {img_w}x{img_h}")

    # Choose selection method based on display availability
    has_display = bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    if has_display:
        x, y, w, h = select_roi_interactive(img)
    else:
        print("No display detected ($DISPLAY not set). Falling back to terminal input.")
        x, y, w, h = select_roi_terminal(img.shape)

    # Validate bounds
    if x < 0 or y < 0 or x + w > img_w or y + h > img_h:
        print(f"Error: selection ({x},{y},{w},{h}) is out of image bounds ({img_w},{img_h}).")
        sys.exit(1)

    # Compute relative coordinates
    x_rel = x / img_w
    y_rel = y / img_h
    w_rel = w / img_w
    h_rel = h / img_h

    # Save template PNG
    template_png = output_dir / "pierres_detail_panel_corner.png"
    corner_crop = img[y : y + h, x : x + w]
    cv2.imwrite(str(template_png), corner_crop)
    print(f"Template saved: {template_png}")

    # Save pierre_panel_layout.json
    layout = {
        "template_file": "pierres_detail_panel_corner.png",
        "extracted_from_resolution": [img_w, img_h],
        "template_rel": {"x": x_rel, "y": y_rel, "w": w_rel, "h": h_rel},
        # panel_rel is the full panel extent relative to image — set equal to
        # template_rel initially; user can refine to cover the full panel.
        "panel_rel": {"x": x_rel, "y": y_rel, "w": w_rel, "h": h_rel},
        "notes": (
            "Top-left corner of the wood-grain panel border. "
            "Update 'panel_rel' w/h to cover the full detail panel if needed."
        ),
    }
    layout_json = output_dir / "pierre_panel_layout.json"
    with open(layout_json, "w") as f:
        json.dump(layout, f, indent=2)
    print(f"Layout JSON saved: {layout_json}")
    print(f"  template_rel: x={x_rel:.4f}  y={y_rel:.4f}  w={w_rel:.4f}  h={h_rel:.4f}")

    # Save debug image
    debug_png = output_dir / "debug_selection.png"
    draw_debug(img, x, y, w, h, debug_png)

    print("\nDone. Verify the template PNG and debug image look correct.")
    print("If the full detail panel is larger than the selected corner, update")
    print(f"'panel_rel' in pierre_panel_layout.json to cover the full panel area.")


if __name__ == "__main__":
    main()
