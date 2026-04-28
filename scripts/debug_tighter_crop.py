"""
Test tighter crops: varying frame_margin values + adaptive frame detection.
Save each crop for visual inspection and run grayscale matching at each.
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


def rank_grayscale_white(inner_bgr, fish_sprites, fish_names):
    """Grayscale white-bg composite + TM_CCOEFF_NORMED."""
    inner_gray = cv2.cvtColor(inner_bgr, cv2.COLOR_BGR2GRAY)
    inner_h, inner_w = inner_gray.shape[:2]
    all_scores = []

    for item_id, sprite_rgba in fish_sprites.items():
        if sprite_rgba.shape[2] == 4:
            a = sprite_rgba[:, :, 3:4].astype(np.float32) / 255.0
            bgr = sprite_rgba[:, :, :3].astype(np.float32)
            comp = (bgr * a + np.full_like(bgr, 255.0) * (1.0 - a)).astype(np.uint8)
        else:
            comp = sprite_rgba
        comp_gray = cv2.cvtColor(comp, cv2.COLOR_BGR2GRAY)

        best_score = -1.0
        best_scale = -1
        for scale in range(6, 18):
            scaled = cv2.resize(comp_gray, None, fx=scale, fy=scale,
                                 interpolation=cv2.INTER_NEAREST)
            if scaled.shape[0] > inner_h or scaled.shape[1] > inner_w:
                continue
            result = cv2.matchTemplate(inner_gray, scaled, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(result)
            if max_val > best_score:
                best_score = max_val
                best_scale = scale

        name = fish_names.get(item_id, f"Unknown({item_id})")
        all_scores.append((best_score, item_id, name, best_scale))

    all_scores.sort(reverse=True)
    return all_scores


def detect_frame_interior(fish_sprite_crop: np.ndarray) -> np.ndarray | None:
    """Detect the wooden frame and crop to just the interior.

    The frame is brown/tan pixels. The interior is dark purple/blue.
    Strategy: convert to HSV, detect the brown frame pixels, find the
    largest interior rectangle that doesn't touch the frame.
    """
    hsv = cv2.cvtColor(fish_sprite_crop, cv2.COLOR_BGR2HSV)
    h, w = fish_sprite_crop.shape[:2]

    # The frame interior (dark purple/blue bg) has low saturation or
    # specific hue range. Let's look at brightness - the frame is
    # medium brightness brown, interior is dark.
    # Actually, let's find frame edges by scanning inward from each side
    # until we hit a significant color change.

    gray = cv2.cvtColor(fish_sprite_crop, cv2.COLOR_BGR2GRAY)

    # Scan from each edge inward, looking for where the brown frame ends
    # Frame pixels tend to be in the 80-160 brightness range
    # Interior/fish pixels tend to be different

    # Use gradient: frame->interior has a sharp brightness change
    # Scan horizontally from left
    mid_y = h // 2
    row = gray[mid_y, :]
    grad = np.abs(np.diff(row.astype(np.int16)))

    # Find first big gradient from left and right
    threshold = 15
    left_edge = 0
    for i in range(len(grad)):
        if grad[i] > threshold:
            left_edge = i + 1
            break

    right_edge = w
    for i in range(len(grad) - 1, -1, -1):
        if grad[i] > threshold:
            right_edge = i
            break

    # Scan vertically
    mid_x = w // 2
    col = gray[:, mid_x]
    grad_v = np.abs(np.diff(col.astype(np.int16)))

    top_edge = 0
    for i in range(len(grad_v)):
        if grad_v[i] > threshold:
            top_edge = i + 1
            break

    bottom_edge = h
    for i in range(len(grad_v) - 1, -1, -1):
        if grad_v[i] > threshold:
            bottom_edge = i
            break

    return fish_sprite_crop[top_edge:bottom_edge, left_edge:right_edge]


def detect_frame_color_based(fish_sprite_crop: np.ndarray) -> np.ndarray:
    """Detect the frame boundary using color clustering.

    The wooden frame has distinctive brown/tan colors.
    The interior has dark purple/blue background.
    Separate them and crop to the interior.
    """
    h, w = fish_sprite_crop.shape[:2]
    hsv = cv2.cvtColor(fish_sprite_crop, cv2.COLOR_BGR2HSV)

    # The wooden frame is brownish: Hue ~10-25, Sat ~100-200, Val ~80-180
    # The dark interior background: Hue ~100-140, Sat ~50-150, Val ~30-100
    # Create mask for "not frame" (interior)
    # Actually let's be simpler: the frame pixels have warm hue (H < 30 in OpenCV 0-180)
    # and moderate brightness. Interior has cool hue or low brightness.

    hue = hsv[:, :, 0]
    sat = hsv[:, :, 1]
    val = hsv[:, :, 2]

    # Frame mask: warm hue (brown/tan), moderate+ saturation
    frame_mask = ((hue < 25) | (hue > 165)) & (sat > 60) & (val > 60)

    # Find bounding box of non-frame region
    interior_mask = ~frame_mask

    # Find rows/cols that are mostly interior (>50% non-frame)
    row_interior_frac = interior_mask.mean(axis=1)
    col_interior_frac = interior_mask.mean(axis=0)

    interior_rows = np.where(row_interior_frac > 0.5)[0]
    interior_cols = np.where(col_interior_frac > 0.5)[0]

    if len(interior_rows) == 0 or len(interior_cols) == 0:
        return fish_sprite_crop

    top = interior_rows[0]
    bottom = interior_rows[-1] + 1
    left = interior_cols[0]
    right = interior_cols[-1] + 1

    return fish_sprite_crop[top:bottom, left:right]


def analyze(image_path: str) -> None:
    src = Path(image_path)
    label = src.stem
    out_dir = Path("tmp") / f"debug_{label}"
    out_dir.mkdir(parents=True, exist_ok=True)

    raw_bytes = src.read_bytes()
    raw_arr = np.frombuffer(raw_bytes, dtype=np.uint8)
    raw_img = cv2.imdecode(raw_arr, cv2.IMREAD_COLOR)
    stripped = strip_letterbox(raw_img)

    layout = load_layout("caught_fish_layout.json")
    cropped = crop_regions(stripped, layout)
    fish_sprite_crop = cropped["fish_sprite"]
    fh, fw = fish_sprite_crop.shape[:2]

    fish_sprites = load_fish_sprites()
    fish_names = load_manifest_fish()

    print(f"\n{'='*60}")
    print(f"Image: {src.name}  fish_sprite_crop={fw}x{fh}")
    print(f"{'='*60}")

    # --- Test varying frame_margin ---
    for margin in [0.15, 0.20, 0.25, 0.30]:
        mx = int(fw * margin)
        my = int(fh * margin)
        inner = fish_sprite_crop[my : fh - my, mx : fw - mx]
        if inner.shape[2] == 4:
            inner = cv2.cvtColor(inner, cv2.COLOR_BGRA2BGR)

        fname = f"09_inner_margin{int(margin*100):02d}.png"
        cv2.imwrite(str(out_dir / fname), inner)

        scores = rank_grayscale_white(inner, fish_sprites, fish_names)
        flounder_rank = None
        flounder_score = None
        for i, (score, item_id, name, scale) in enumerate(scores):
            if name.lower() == "flounder":
                flounder_rank = i + 1
                flounder_score = score
                break

        top_name = scores[0][2] if scores else "?"
        top_score = scores[0][0] if scores else 0
        gap = top_score - (flounder_score or 0) if flounder_rank != 1 else 0
        print(f"\n  margin={margin:.2f} -> inner={inner.shape[1]}x{inner.shape[0]}")
        print(f"    #1: {top_name} ({top_score:.4f})")
        print(f"    Flounder: rank=#{flounder_rank} score={flounder_score:.4f} gap={gap:.4f}")

    # --- Adaptive crop: gradient-based ---
    print(f"\n  --- Adaptive crop (gradient scan) ---")
    adaptive_crop = detect_frame_interior(fish_sprite_crop)
    if adaptive_crop is not None and adaptive_crop.size > 0:
        if adaptive_crop.shape[2] == 4:
            adaptive_crop = cv2.cvtColor(adaptive_crop, cv2.COLOR_BGRA2BGR)
        cv2.imwrite(str(out_dir / "09_inner_adaptive_gradient.png"), adaptive_crop)
        print(f"    crop: {adaptive_crop.shape[1]}x{adaptive_crop.shape[0]}")

        scores = rank_grayscale_white(adaptive_crop, fish_sprites, fish_names)
        for i, (score, item_id, name, scale) in enumerate(scores):
            if name.lower() == "flounder":
                print(f"    Flounder: rank=#{i+1} score={score:.4f}")
                break
        print(f"    #1: {scores[0][2]} ({scores[0][0]:.4f})")
    else:
        print(f"    Adaptive crop failed - empty result")

    # --- Adaptive crop: color-based ---
    print(f"\n  --- Adaptive crop (color-based frame detection) ---")
    color_crop = detect_frame_color_based(fish_sprite_crop)
    if color_crop is not None and color_crop.size > 0:
        if color_crop.shape[2] == 4:
            color_crop = cv2.cvtColor(color_crop, cv2.COLOR_BGRA2BGR)
        cv2.imwrite(str(out_dir / "09_inner_adaptive_color.png"), color_crop)
        print(f"    crop: {color_crop.shape[1]}x{color_crop.shape[0]}")

        scores = rank_grayscale_white(color_crop, fish_sprites, fish_names)
        for i, (score, item_id, name, scale) in enumerate(scores):
            if name.lower() == "flounder":
                print(f"    Flounder: rank=#{i+1} score={score:.4f}")
                break
        print(f"    #1: {scores[0][2]} ({scores[0][0]:.4f})")
    else:
        print(f"    Color crop failed - empty result")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/debug_tighter_crop.py <image1> [image2] ...")
        sys.exit(1)
    for img_path in sys.argv[1:]:
        analyze(img_path)
