"""
Test the training repo's sprite matching approach (white-bg composite + TM_CCOEFF_NORMED)
against both test images to confirm it fixes fish identification.
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


def match_fish_sprite_training_method(
    fish_sprite_crop: np.ndarray,
    frame_margin: float = 0.15,
    scale_range: tuple[int, int] = (6, 18),
    match_threshold: float = 0.80,
) -> dict:
    """Training repo version: white-bg composite + TM_CCOEFF_NORMED."""
    h, w = fish_sprite_crop.shape[:2]
    mx = int(w * frame_margin)
    my = int(h * frame_margin)
    inner = fish_sprite_crop[my : h - my, mx : w - mx]

    if inner.shape[2] == 4:
        inner = cv2.cvtColor(inner, cv2.COLOR_BGRA2BGR)

    fish_sprites = load_fish_sprites()
    fish_names = load_manifest_fish()

    best_score = -1.0
    best_id = None
    best_scale = -1
    inner_h, inner_w = inner.shape[:2]

    for item_id, sprite_rgba in fish_sprites.items():
        if sprite_rgba.shape[2] == 4:
            alpha = sprite_rgba[:, :, 3:4].astype(np.float32) / 255.0
            bgr = sprite_rgba[:, :, :3].astype(np.float32)
            white_bg = np.full_like(bgr, 255.0)
            composited = (bgr * alpha + white_bg * (1.0 - alpha)).astype(np.uint8)
        else:
            composited = sprite_rgba

        for scale in range(scale_range[0], scale_range[1]):
            scaled = cv2.resize(
                composited, None, fx=scale, fy=scale, interpolation=cv2.INTER_NEAREST
            )
            if scaled.shape[0] > inner_h or scaled.shape[1] > inner_w:
                continue

            result = cv2.matchTemplate(inner, scaled, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(result)

            if max_val > best_score:
                best_score = max_val
                best_id = item_id
                best_scale = scale

    return {
        "fish_name": fish_names.get(best_id, f"Unknown ({best_id})") if best_score >= match_threshold else None,
        "item_id": best_id if best_score >= match_threshold else None,
        "match_score": round(float(best_score), 4),
        "best_scale": best_scale,
        "_best_id_raw": best_id,
        "_best_name_raw": fish_names.get(best_id, "?"),
    }


def test_image(image_path: str) -> None:
    src = Path(image_path)

    raw_bytes = src.read_bytes()
    raw_arr = np.frombuffer(raw_bytes, dtype=np.uint8)
    raw_img = cv2.imdecode(raw_arr, cv2.IMREAD_COLOR)
    stripped = strip_letterbox(raw_img)

    layout = load_layout("caught_fish_layout.json")
    cropped = crop_regions(stripped, layout)
    fish_sprite_crop = cropped["fish_sprite"]

    print(f"\n{'='*60}")
    print(f"Image: {src}")
    print(f"{'='*60}")

    # Training method
    result = match_fish_sprite_training_method(fish_sprite_crop)
    print(f"\n  Training method (white-bg + TM_CCOEFF_NORMED):")
    print(f"    fish_name:   {result['fish_name']}")
    print(f"    match_score: {result['match_score']}")
    print(f"    best_scale:  {result['best_scale']}")
    print(f"    raw best:    {result['_best_name_raw']} (id={result['_best_id_raw']})")

    # Top 10 ranking with training method
    print(f"\n  Top 10 ranking (training method):")
    fish_sprites = load_fish_sprites()
    fish_names = load_manifest_fish()

    frame_margin = 0.15
    fh, fw = fish_sprite_crop.shape[:2]
    mx = int(fw * frame_margin)
    my = int(fh * frame_margin)
    inner = fish_sprite_crop[my : fh - my, mx : fw - mx]
    if inner.shape[2] == 4:
        inner = cv2.cvtColor(inner, cv2.COLOR_BGRA2BGR)
    inner_h, inner_w = inner.shape[:2]

    all_scores = []
    for item_id, sprite_rgba in fish_sprites.items():
        if sprite_rgba.shape[2] == 4:
            alpha = sprite_rgba[:, :, 3:4].astype(np.float32) / 255.0
            bgr = sprite_rgba[:, :, :3].astype(np.float32)
            white_bg = np.full_like(bgr, 255.0)
            composited = (bgr * alpha + white_bg * (1.0 - alpha)).astype(np.uint8)
        else:
            composited = sprite_rgba

        best_for_fish = -1.0
        best_fish_scale = -1
        for scale in range(6, 18):
            scaled = cv2.resize(composited, None, fx=scale, fy=scale,
                                 interpolation=cv2.INTER_NEAREST)
            if scaled.shape[0] > inner_h or scaled.shape[1] > inner_w:
                continue
            result = cv2.matchTemplate(inner, scaled, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(result)
            if max_val > best_for_fish:
                best_for_fish = max_val
                best_fish_scale = scale

        name = fish_names.get(item_id, f"Unknown({item_id})")
        all_scores.append((best_for_fish, item_id, name, best_fish_scale))

    all_scores.sort(reverse=True)
    for i, (score, item_id, name, scale) in enumerate(all_scores[:10]):
        marker = " <-- FLOUNDER" if name.lower() == "flounder" else ""
        print(f"    {i+1:2d}. {name} (id={item_id}) score={score:.4f} scale={scale}{marker}")

    for i, (score, item_id, name, scale) in enumerate(all_scores):
        if name.lower() == "flounder":
            if i >= 10:
                print(f"\n    Flounder rank: #{i+1}")
            break


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/debug_training_method.py <image1> [image2] ...")
        sys.exit(1)
    for img_path in sys.argv[1:]:
        test_image(img_path)
