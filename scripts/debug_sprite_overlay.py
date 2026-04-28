"""
Diagnostic: overlay the flounder sprite at best-fit scale on the inner crop
to visualize where the match is landing and what the background color mismatch looks like.

Also tests matching with TM_CCOEFF_NORMED (no mask) vs TM_CCORR_NORMED (with mask)
to see which method is more robust.
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


def analyze_matching(image_path: str) -> None:
    src = Path(image_path)
    label = src.stem
    out_dir = Path("tmp") / f"debug_{label}"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Decode
    raw_bytes = src.read_bytes()
    raw_arr = np.frombuffer(raw_bytes, dtype=np.uint8)
    raw_img = cv2.imdecode(raw_arr, cv2.IMREAD_COLOR)
    stripped = strip_letterbox(raw_img)

    layout = load_layout("caught_fish_layout.json")
    cropped = crop_regions(stripped, layout)
    fish_sprite_crop = cropped["fish_sprite"]

    # Inner crop
    frame_margin = 0.15
    fh, fw = fish_sprite_crop.shape[:2]
    mx = int(fw * frame_margin)
    my = int(fh * frame_margin)
    inner = fish_sprite_crop[my : fh - my, mx : fw - mx]
    inner_bgr = inner if inner.shape[2] == 3 else cv2.cvtColor(inner, cv2.COLOR_BGRA2BGR)
    inner_h, inner_w = inner_bgr.shape[:2]

    sprites = load_fish_sprites()
    names = load_manifest_fish()

    # Find flounder ID
    flounder_id = None
    for item_id, name in names.items():
        if name.lower() == "flounder":
            flounder_id = item_id
            break

    print(f"\n{'='*60}")
    print(f"SPRITE MATCHING ANALYSIS: {src.name}")
    print(f"Inner crop: {inner_w}x{inner_h}")
    print(f"{'='*60}")

    # Test all methods for flounder specifically
    sprite_rgba = sprites[flounder_id]
    bgr = sprite_rgba[:, :, :3]
    alpha = sprite_rgba[:, :, 3]

    methods = [
        ("TM_CCORR_NORMED (masked)", cv2.TM_CCORR_NORMED, True),
        ("TM_CCOEFF_NORMED (masked)", cv2.TM_CCOEFF_NORMED, True),
        ("TM_CCORR_NORMED (no mask)", cv2.TM_CCORR_NORMED, False),
        ("TM_CCOEFF_NORMED (no mask)", cv2.TM_CCOEFF_NORMED, False),
    ]

    print(f"\n--- Flounder (ID {flounder_id}) match scores by method & scale ---")
    for method_name, method, use_mask in methods:
        print(f"\n  {method_name}:")
        best_score = -1.0
        best_scale = -1
        best_loc = None
        for scale in range(6, 18):
            scaled_bgr = cv2.resize(bgr, None, fx=scale, fy=scale,
                                     interpolation=cv2.INTER_NEAREST)
            if scaled_bgr.shape[0] > inner_h or scaled_bgr.shape[1] > inner_w:
                continue

            if use_mask:
                scaled_mask = cv2.resize(alpha, None, fx=scale, fy=scale,
                                          interpolation=cv2.INTER_NEAREST)
                scaled_mask_3ch = cv2.merge([scaled_mask, scaled_mask, scaled_mask])
                result = cv2.matchTemplate(inner_bgr, scaled_bgr, method,
                                            mask=scaled_mask_3ch)
            else:
                result = cv2.matchTemplate(inner_bgr, scaled_bgr, method)

            _, max_val, _, max_loc = cv2.minMaxLoc(result)
            marker = " <-- BEST" if max_val > best_score else ""
            print(f"    scale={scale:2d} ({scaled_bgr.shape[1]:3d}x{scaled_bgr.shape[0]:3d}) "
                  f"score={max_val:.4f}{marker}")
            if max_val > best_score:
                best_score = max_val
                best_scale = scale
                best_loc = max_loc

        if best_loc and best_scale > 0:
            vis = inner_bgr.copy()
            s_bgr = cv2.resize(bgr, None, fx=best_scale, fy=best_scale,
                                interpolation=cv2.INTER_NEAREST)
            x, y = best_loc
            cv2.rectangle(vis, (x, y), (x + s_bgr.shape[1], y + s_bgr.shape[0]),
                          (0, 255, 0), 1)
            fname = f"07_flounder_match_{method_name.split()[0].lower()}.png"
            cv2.imwrite(str(out_dir / fname), vis)

    # Now find the TOP 5 matches across ALL fish using current method
    print(f"\n--- Top 10 matches (TM_CCORR_NORMED masked, current method) ---")
    all_scores = []
    for item_id, sprite_rgba in sprites.items():
        if sprite_rgba.shape[2] == 4:
            s_bgr = sprite_rgba[:, :, :3]
            s_alpha = sprite_rgba[:, :, 3]
        else:
            s_bgr = sprite_rgba
            s_alpha = None

        best_for_fish = -1.0
        best_fish_scale = -1
        for scale in range(6, 18):
            scaled = cv2.resize(s_bgr, None, fx=scale, fy=scale,
                                 interpolation=cv2.INTER_NEAREST)
            if scaled.shape[0] > inner_h or scaled.shape[1] > inner_w:
                continue
            if s_alpha is not None:
                sm = cv2.resize(s_alpha, None, fx=scale, fy=scale,
                                 interpolation=cv2.INTER_NEAREST)
                sm3 = cv2.merge([sm, sm, sm])
                result = cv2.matchTemplate(inner_bgr, scaled, cv2.TM_CCORR_NORMED,
                                            mask=sm3)
            else:
                result = cv2.matchTemplate(inner_bgr, scaled, cv2.TM_CCOEFF_NORMED)

            _, max_val, _, _ = cv2.minMaxLoc(result)
            if max_val > best_for_fish:
                best_for_fish = max_val
                best_fish_scale = scale

        fish_name = names.get(item_id, f"Unknown({item_id})")
        all_scores.append((best_for_fish, item_id, fish_name, best_fish_scale))

    all_scores.sort(reverse=True)
    for i, (score, item_id, name, scale) in enumerate(all_scores[:10]):
        marker = " <-- CORRECT" if item_id == flounder_id else ""
        print(f"  {i+1}. {name} (id={item_id}) score={score:.4f} scale={scale}{marker}")

    # Find where flounder actually ranks
    for i, (score, item_id, name, scale) in enumerate(all_scores):
        if item_id == flounder_id:
            print(f"\n  Flounder actual rank: #{i+1} out of {len(all_scores)}")
            break


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/debug_sprite_overlay.py <image1> [image2] ...")
        sys.exit(1)
    for img_path in sys.argv[1:]:
        analyze_matching(img_path)
