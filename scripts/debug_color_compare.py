"""
Compare the actual in-game fish pixels with the sprite at the best matching
position and scale to understand the color transformation.

Also try histogram-equalized and grayscale matching.
"""

from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "services" / "ocr-tools"))

from stardew_ocr_tools.common import (
    crop_regions,
    load_fish_sprites,
    load_layout,
    load_manifest_fish,
    strip_letterbox,
)


def test_grayscale_matching(inner_bgr, fish_sprites, fish_names, inner_h, inner_w):
    """Try matching in grayscale to remove color mismatch issues."""
    inner_gray = cv2.cvtColor(inner_bgr, cv2.COLOR_BGR2GRAY)

    all_scores = []
    for item_id, sprite_rgba in fish_sprites.items():
        if sprite_rgba.shape[2] == 4:
            alpha = sprite_rgba[:, :, 3:4].astype(np.float32) / 255.0
            bgr = sprite_rgba[:, :, :3].astype(np.float32)
            white_bg = np.full_like(bgr, 255.0)
            composited = (bgr * alpha + white_bg * (1.0 - alpha)).astype(np.uint8)
        else:
            composited = sprite_rgba

        comp_gray = cv2.cvtColor(composited, cv2.COLOR_BGR2GRAY)

        best_for_fish = -1.0
        best_fish_scale = -1
        for scale in range(6, 18):
            scaled = cv2.resize(comp_gray, None, fx=scale, fy=scale,
                                 interpolation=cv2.INTER_NEAREST)
            if scaled.shape[0] > inner_h or scaled.shape[1] > inner_w:
                continue
            result = cv2.matchTemplate(inner_gray, scaled, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(result)
            if max_val > best_for_fish:
                best_for_fish = max_val
                best_fish_scale = scale

        name = fish_names.get(item_id, f"Unknown({item_id})")
        all_scores.append((best_for_fish, item_id, name, best_fish_scale))

    all_scores.sort(reverse=True)
    return all_scores


def test_edge_matching(inner_bgr, fish_sprites, fish_names, inner_h, inner_w):
    """Try matching on edge-detected images (shape only, ignoring color)."""
    inner_gray = cv2.cvtColor(inner_bgr, cv2.COLOR_BGR2GRAY)
    inner_edges = cv2.Canny(inner_gray, 50, 150)

    all_scores = []
    for item_id, sprite_rgba in fish_sprites.items():
        if sprite_rgba.shape[2] == 4:
            alpha = sprite_rgba[:, :, 3:4].astype(np.float32) / 255.0
            bgr = sprite_rgba[:, :, :3].astype(np.float32)
            white_bg = np.full_like(bgr, 255.0)
            composited = (bgr * alpha + white_bg * (1.0 - alpha)).astype(np.uint8)
        else:
            composited = sprite_rgba

        comp_gray = cv2.cvtColor(composited, cv2.COLOR_BGR2GRAY)
        comp_edges = cv2.Canny(comp_gray, 50, 150)

        best_for_fish = -1.0
        best_fish_scale = -1
        for scale in range(6, 18):
            scaled = cv2.resize(comp_edges, None, fx=scale, fy=scale,
                                 interpolation=cv2.INTER_NEAREST)
            if scaled.shape[0] > inner_h or scaled.shape[1] > inner_w:
                continue
            result = cv2.matchTemplate(inner_edges, scaled, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(result)
            if max_val > best_for_fish:
                best_for_fish = max_val
                best_fish_scale = scale

        name = fish_names.get(item_id, f"Unknown({item_id})")
        all_scores.append((best_for_fish, item_id, name, best_fish_scale))

    all_scores.sort(reverse=True)
    return all_scores


def test_alpha_mask_ccoeff(inner_bgr, fish_sprites, fish_names, inner_h, inner_w):
    """Alpha-mask + TM_CCOEFF_NORMED (hybrid of both approaches)."""
    all_scores = []
    for item_id, sprite_rgba in fish_sprites.items():
        if sprite_rgba.shape[2] == 4:
            bgr = sprite_rgba[:, :, :3]
            alpha = sprite_rgba[:, :, 3]
        else:
            bgr = sprite_rgba
            alpha = None

        best_for_fish = -1.0
        best_fish_scale = -1
        for scale in range(6, 18):
            scaled_bgr = cv2.resize(bgr, None, fx=scale, fy=scale,
                                     interpolation=cv2.INTER_NEAREST)
            if scaled_bgr.shape[0] > inner_h or scaled_bgr.shape[1] > inner_w:
                continue

            if alpha is not None:
                scaled_mask = cv2.resize(alpha, None, fx=scale, fy=scale,
                                          interpolation=cv2.INTER_NEAREST)
                scaled_mask_3ch = cv2.merge([scaled_mask, scaled_mask, scaled_mask])
                result = cv2.matchTemplate(inner_bgr, scaled_bgr, cv2.TM_CCOEFF_NORMED,
                                            mask=scaled_mask_3ch)
            else:
                result = cv2.matchTemplate(inner_bgr, scaled_bgr, cv2.TM_CCOEFF_NORMED)

            _, max_val, _, _ = cv2.minMaxLoc(result)
            if max_val > best_for_fish:
                best_for_fish = max_val
                best_fish_scale = scale

        name = fish_names.get(item_id, f"Unknown({item_id})")
        all_scores.append((best_for_fish, item_id, name, best_fish_scale))

    all_scores.sort(reverse=True)
    return all_scores


def analyze(image_path: str) -> None:
    src = Path(image_path)

    raw_bytes = src.read_bytes()
    raw_arr = np.frombuffer(raw_bytes, dtype=np.uint8)
    raw_img = cv2.imdecode(raw_arr, cv2.IMREAD_COLOR)
    stripped = strip_letterbox(raw_img)

    layout = load_layout("caught_fish_layout.json")
    cropped = crop_regions(stripped, layout)
    fish_sprite_crop = cropped["fish_sprite"]

    frame_margin = 0.15
    fh, fw = fish_sprite_crop.shape[:2]
    mx = int(fw * frame_margin)
    my = int(fh * frame_margin)
    inner = fish_sprite_crop[my : fh - my, mx : fw - mx]
    if inner.shape[2] == 4:
        inner = cv2.cvtColor(inner, cv2.COLOR_BGRA2BGR)
    inner_h, inner_w = inner.shape[:2]

    fish_sprites = load_fish_sprites()
    fish_names = load_manifest_fish()

    print(f"\n{'='*60}")
    print(f"Image: {src.name}  inner={inner_w}x{inner_h}")
    print(f"{'='*60}")

    methods = [
        ("Grayscale (white-bg composite)", test_grayscale_matching),
        ("Edge detection (Canny)", test_edge_matching),
        ("Alpha-mask + TM_CCOEFF_NORMED", test_alpha_mask_ccoeff),
    ]

    for method_name, method_fn in methods:
        scores = method_fn(inner, fish_sprites, fish_names, inner_h, inner_w)
        print(f"\n  {method_name}:")
        for i, (score, item_id, name, scale) in enumerate(scores[:5]):
            marker = " <-- FLOUNDER" if name.lower() == "flounder" else ""
            print(f"    {i+1}. {name} (id={item_id}) score={score:.4f} scale={scale}{marker}")
        for i, (score, item_id, name, scale) in enumerate(scores):
            if name.lower() == "flounder":
                if i >= 5:
                    print(f"    Flounder rank: #{i+1} score={score:.4f}")
                break


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/debug_color_compare.py <image1> [image2] ...")
        sys.exit(1)
    for img_path in sys.argv[1:]:
        analyze(img_path)
