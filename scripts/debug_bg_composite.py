"""
Test sprite matching after compositing sprites onto the sampled background
color from the inner crop, rather than white.
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


def sample_background_color(inner: np.ndarray, margin_px: int = 8) -> np.ndarray:
    """Sample the background color from the edges of the inner crop.

    Uses a margin strip around the edges, takes the median to be robust
    against any fish pixels bleeding into the edges.
    """
    top = inner[:margin_px, :, :]
    bottom = inner[-margin_px:, :, :]
    left = inner[:, :margin_px, :]
    right = inner[:, -margin_px:, :]

    edge_pixels = np.concatenate([
        top.reshape(-1, 3),
        bottom.reshape(-1, 3),
        left.reshape(-1, 3),
        right.reshape(-1, 3),
    ], axis=0)

    bg_color = np.median(edge_pixels, axis=0).astype(np.uint8)
    return bg_color


def match_with_bg_composite(inner_bgr, bg_color, fish_sprites, fish_names, inner_h, inner_w):
    """Composite sprites onto sampled bg color, then TM_CCOEFF_NORMED."""
    all_scores = []
    for item_id, sprite_rgba in fish_sprites.items():
        if sprite_rgba.shape[2] == 4:
            alpha = sprite_rgba[:, :, 3:4].astype(np.float32) / 255.0
            bgr = sprite_rgba[:, :, :3].astype(np.float32)
            bg = np.full_like(bgr, bg_color.astype(np.float32))
            composited = (bgr * alpha + bg * (1.0 - alpha)).astype(np.uint8)
        else:
            composited = sprite_rgba

        best_for_fish = -1.0
        best_fish_scale = -1
        for scale in range(6, 18):
            scaled = cv2.resize(composited, None, fx=scale, fy=scale,
                                 interpolation=cv2.INTER_NEAREST)
            if scaled.shape[0] > inner_h or scaled.shape[1] > inner_w:
                continue
            result = cv2.matchTemplate(inner_bgr, scaled, cv2.TM_CCOEFF_NORMED)
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

    # Sample background
    bg_color = sample_background_color(inner)
    print(f"\n{'='*60}")
    print(f"Image: {src.name}")
    print(f"Sampled background BGR: [{bg_color[0]}, {bg_color[1]}, {bg_color[2]}]")
    print(f"{'='*60}")

    # Save a visualization of what the composited flounder looks like
    out_dir = Path("tmp") / f"debug_{src.stem}"
    out_dir.mkdir(parents=True, exist_ok=True)

    flounder_id = None
    for item_id, name in fish_names.items():
        if name.lower() == "flounder":
            flounder_id = item_id
            break

    if flounder_id:
        sprite_rgba = fish_sprites[flounder_id]
        alpha = sprite_rgba[:, :, 3:4].astype(np.float32) / 255.0
        bgr = sprite_rgba[:, :, :3].astype(np.float32)
        bg = np.full_like(bgr, bg_color.astype(np.float32))
        composited = (bgr * alpha + bg * (1.0 - alpha)).astype(np.uint8)
        for scale in [8, 10]:
            scaled = cv2.resize(composited, None, fx=scale, fy=scale,
                                 interpolation=cv2.INTER_NEAREST)
            cv2.imwrite(str(out_dir / f"08_flounder_on_bg_scale{scale}.png"), scaled)
            print(f"  Saved composited flounder at scale {scale}: {scaled.shape[1]}x{scaled.shape[0]}")

    # Run matching
    scores = match_with_bg_composite(inner, bg_color, fish_sprites, fish_names,
                                      inner_h, inner_w)
    print(f"\n  BG-composite + TM_CCOEFF_NORMED - Top 10:")
    for i, (score, item_id, name, scale) in enumerate(scores[:10]):
        marker = " <-- FLOUNDER" if name.lower() == "flounder" else ""
        print(f"    {i+1:2d}. {name} (id={item_id}) score={score:.4f} scale={scale}{marker}")
    for i, (score, item_id, name, scale) in enumerate(scores):
        if name.lower() == "flounder":
            if i >= 10:
                print(f"\n    Flounder rank: #{i+1} score={score:.4f}")
            break


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/debug_bg_composite.py <image1> [image2] ...")
        sys.exit(1)
    for img_path in sys.argv[1:]:
        analyze(img_path)
