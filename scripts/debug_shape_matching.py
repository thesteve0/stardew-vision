"""
Test shape-based sprite matching approaches that ignore color entirely:
1. Grayscale + TM_CCOEFF_NORMED (white-bg composite)
2. Grayscale + TM_CCOEFF_NORMED (bg-sampled composite)
3. Edge detection (Canny) + TM_CCOEFF_NORMED
4. Alpha-masked grayscale + TM_CCOEFF_NORMED
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
    top = inner[:margin_px, :, :]
    bottom = inner[-margin_px:, :, :]
    left = inner[:, :margin_px, :]
    right = inner[:, -margin_px:, :]
    edge_pixels = np.concatenate([
        top.reshape(-1, 3), bottom.reshape(-1, 3),
        left.reshape(-1, 3), right.reshape(-1, 3),
    ], axis=0)
    return np.median(edge_pixels, axis=0).astype(np.uint8)


def rank_all(inner_bgr, fish_sprites, fish_names, method_fn):
    """Generic ranker: method_fn(inner, sprite_rgba) -> preprocessed (inner, template)."""
    inner_h, inner_w = inner_bgr.shape[:2]
    all_scores = []

    for item_id, sprite_rgba in fish_sprites.items():
        proc_inner, proc_template = method_fn(inner_bgr, sprite_rgba)
        best_score = -1.0
        best_scale = -1

        for scale in range(6, 18):
            scaled = cv2.resize(proc_template, None, fx=scale, fy=scale,
                                 interpolation=cv2.INTER_NEAREST)
            if scaled.shape[0] > proc_inner.shape[0] or scaled.shape[1] > proc_inner.shape[1]:
                continue
            result = cv2.matchTemplate(proc_inner, scaled, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(result)
            if max_val > best_score:
                best_score = max_val
                best_scale = scale

        name = fish_names.get(item_id, f"Unknown({item_id})")
        all_scores.append((best_score, item_id, name, best_scale))

    all_scores.sort(reverse=True)
    return all_scores


def method_grayscale_white(inner_bgr, sprite_rgba):
    """Grayscale matching with white-bg composite."""
    inner_gray = cv2.cvtColor(inner_bgr, cv2.COLOR_BGR2GRAY)
    if sprite_rgba.shape[2] == 4:
        a = sprite_rgba[:, :, 3:4].astype(np.float32) / 255.0
        bgr = sprite_rgba[:, :, :3].astype(np.float32)
        comp = (bgr * a + np.full_like(bgr, 255.0) * (1.0 - a)).astype(np.uint8)
    else:
        comp = sprite_rgba
    comp_gray = cv2.cvtColor(comp, cv2.COLOR_BGR2GRAY)
    return inner_gray, comp_gray


def make_method_grayscale_bg(bg_color):
    def method(inner_bgr, sprite_rgba):
        inner_gray = cv2.cvtColor(inner_bgr, cv2.COLOR_BGR2GRAY)
        if sprite_rgba.shape[2] == 4:
            a = sprite_rgba[:, :, 3:4].astype(np.float32) / 255.0
            bgr = sprite_rgba[:, :, :3].astype(np.float32)
            bg = np.full_like(bgr, bg_color.astype(np.float32))
            comp = (bgr * a + bg * (1.0 - a)).astype(np.uint8)
        else:
            comp = sprite_rgba
        comp_gray = cv2.cvtColor(comp, cv2.COLOR_BGR2GRAY)
        return inner_gray, comp_gray
    return method


def method_edges(inner_bgr, sprite_rgba):
    """Canny edge matching."""
    inner_gray = cv2.cvtColor(inner_bgr, cv2.COLOR_BGR2GRAY)
    inner_edges = cv2.Canny(inner_gray, 50, 150)
    if sprite_rgba.shape[2] == 4:
        a = sprite_rgba[:, :, 3:4].astype(np.float32) / 255.0
        bgr = sprite_rgba[:, :, :3].astype(np.float32)
        comp = (bgr * a + np.full_like(bgr, 255.0) * (1.0 - a)).astype(np.uint8)
    else:
        comp = sprite_rgba
    comp_gray = cv2.cvtColor(comp, cv2.COLOR_BGR2GRAY)
    comp_edges = cv2.Canny(comp_gray, 50, 150)
    return inner_edges, comp_edges


def method_alpha_masked_gray(inner_bgr, sprite_rgba):
    """Grayscale with alpha mask (only compare opaque pixels)."""
    inner_gray = cv2.cvtColor(inner_bgr, cv2.COLOR_BGR2GRAY)
    if sprite_rgba.shape[2] == 4:
        bgr = sprite_rgba[:, :, :3]
        comp_gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    else:
        comp_gray = cv2.cvtColor(sprite_rgba, cv2.COLOR_BGR2GRAY)
    return inner_gray, comp_gray


def method_hist_eq_gray(inner_bgr, sprite_rgba):
    """Histogram-equalized grayscale (normalizes brightness/contrast)."""
    inner_gray = cv2.equalizeHist(cv2.cvtColor(inner_bgr, cv2.COLOR_BGR2GRAY))
    if sprite_rgba.shape[2] == 4:
        a = sprite_rgba[:, :, 3:4].astype(np.float32) / 255.0
        bgr = sprite_rgba[:, :, :3].astype(np.float32)
        comp = (bgr * a + np.full_like(bgr, 255.0) * (1.0 - a)).astype(np.uint8)
    else:
        comp = sprite_rgba
    comp_gray = cv2.equalizeHist(cv2.cvtColor(comp, cv2.COLOR_BGR2GRAY))
    return inner_gray, comp_gray


def print_ranking(scores, label):
    print(f"\n  {label}:")
    for i, (score, item_id, name, scale) in enumerate(scores[:10]):
        marker = " <-- FLOUNDER" if name.lower() == "flounder" else ""
        print(f"    {i+1:2d}. {name} (id={item_id}) score={score:.4f} scale={scale}{marker}")
    for i, (score, item_id, name, scale) in enumerate(scores):
        if name.lower() == "flounder":
            if i >= 10:
                print(f"    Flounder rank: #{i+1} score={score:.4f}")
            break


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

    fish_sprites = load_fish_sprites()
    fish_names = load_manifest_fish()
    bg_color = sample_background_color(inner)

    print(f"\n{'='*60}")
    print(f"Image: {src.name}  inner={inner.shape[1]}x{inner.shape[0]}")
    print(f"Sampled bg BGR: [{bg_color[0]}, {bg_color[1]}, {bg_color[2]}]")
    print(f"{'='*60}")

    methods = [
        ("Grayscale (white-bg)", method_grayscale_white),
        ("Grayscale (sampled-bg)", make_method_grayscale_bg(bg_color)),
        ("Histogram-equalized grayscale", method_hist_eq_gray),
        ("Canny edges", method_edges),
        ("Alpha-masked grayscale (raw sprite)", method_alpha_masked_gray),
    ]

    for label, method_fn in methods:
        scores = rank_all(inner, fish_sprites, fish_names, method_fn)
        print_ranking(scores, label)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/debug_shape_matching.py <image1> [image2] ...")
        sys.exit(1)
    for img_path in sys.argv[1:]:
        analyze(img_path)
