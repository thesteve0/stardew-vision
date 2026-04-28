"""
Diagnostic script: run the full caught fish pipeline on images and report results.
Also saves the flounder sprite at various scales for visual inspection.

Usage:
    python scripts/debug_caught_fish_results.py tmp/IMG_0035.PNG tmp/good/IMG_0036.PNG
"""

from __future__ import annotations

import sys
import json
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "services" / "ocr-tools"))

from stardew_ocr_tools.common import (
    crop_regions,
    decode_image_b64,
    load_fish_sprites,
    load_image_from_path,
    load_layout,
    load_manifest_fish,
    run_ocr,
    strip_letterbox,
)
from stardew_ocr_tools.crop_caught_fish import (
    match_fish_sprite,
    parse_caught_fish_fields,
)


def dump_sprite_info():
    """Save the flounder sprite and show alpha channel details."""
    out_dir = Path("tmp/debug_sprites")
    out_dir.mkdir(parents=True, exist_ok=True)

    sprites = load_fish_sprites()
    names = load_manifest_fish()

    # Find flounder
    flounder_id = None
    for item_id, name in names.items():
        if name.lower() == "flounder":
            flounder_id = item_id
            break

    if flounder_id is None:
        print("Flounder not found in manifest!")
        return

    print(f"\nFlounder: item_id={flounder_id}")
    sprite = sprites[flounder_id]
    print(f"  Sprite shape: {sprite.shape} dtype={sprite.dtype}")

    if sprite.shape[2] == 4:
        bgr = sprite[:, :, :3]
        alpha = sprite[:, :, 3]
        print(f"  Alpha channel: min={alpha.min()} max={alpha.max()} "
              f"unique values={np.unique(alpha)}")
        print(f"  Opaque pixels: {(alpha > 0).sum()} / {alpha.size}")
        print(f"  Fully transparent: {(alpha == 0).sum()}")

        # Save raw sprite
        cv2.imwrite(str(out_dir / "flounder_raw_16x16.png"), sprite)

        # Save alpha channel as grayscale
        cv2.imwrite(str(out_dir / "flounder_alpha_16x16.png"), alpha)

        # Save at scale 10 for visibility
        for scale in [8, 10, 12]:
            scaled_bgr = cv2.resize(bgr, None, fx=scale, fy=scale,
                                     interpolation=cv2.INTER_NEAREST)
            scaled_alpha = cv2.resize(alpha, None, fx=scale, fy=scale,
                                       interpolation=cv2.INTER_NEAREST)
            scaled_rgba = cv2.merge([scaled_bgr[:,:,0], scaled_bgr[:,:,1],
                                      scaled_bgr[:,:,2], scaled_alpha])
            cv2.imwrite(str(out_dir / f"flounder_scale{scale}.png"), scaled_rgba)
            cv2.imwrite(str(out_dir / f"flounder_bgr_scale{scale}.png"), scaled_bgr)
            cv2.imwrite(str(out_dir / f"flounder_alpha_scale{scale}.png"), scaled_alpha)
            print(f"  Saved scale {scale}: {scaled_bgr.shape[1]}x{scaled_bgr.shape[0]}")

    print(f"  Sprites saved to {out_dir}/")


def run_full_pipeline(image_path: str) -> None:
    src = Path(image_path)
    label = src.stem
    out_dir = Path("tmp") / f"debug_{label}"
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"FULL PIPELINE: {src}")
    print(f"{'='*60}")

    # Decode & strip
    raw_bytes = src.read_bytes()
    raw_arr = np.frombuffer(raw_bytes, dtype=np.uint8)
    raw_img = cv2.imdecode(raw_arr, cv2.IMREAD_COLOR)
    stripped = strip_letterbox(raw_img)
    print(f"Image: {raw_img.shape[1]}x{raw_img.shape[0]} -> stripped: {stripped.shape[1]}x{stripped.shape[0]}")

    layout = load_layout("caught_fish_layout.json")
    cropped = crop_regions(stripped, layout)
    notification_crop = cropped["notification"]
    fish_sprite_crop = cropped["fish_sprite"]

    # --- OCR ---
    print(f"\n--- OCR Results ---")
    ocr_results = run_ocr(notification_crop, upscale=3.0)
    if not ocr_results:
        print("  NO OCR RESULTS!")
    else:
        for rec in ocr_results:
            print(f"  text='{rec['text']}' score={rec['score']:.3f} "
                  f"rel_x={rec['rel_x']:.3f} rel_y={rec['rel_y']:.3f}")

    fields = parse_caught_fish_fields(ocr_results) if ocr_results else {}
    print(f"\n  Parsed fields: {json.dumps(fields, indent=2)}")

    # --- Sprite matching ---
    print(f"\n--- Sprite Matching ---")
    sprite_result = match_fish_sprite(fish_sprite_crop)
    print(f"  Result: {json.dumps(sprite_result, indent=2)}")

    # Also test with different thresholds
    for threshold in [0.5, 0.6, 0.7, 0.8, 0.9]:
        result = match_fish_sprite(fish_sprite_crop, match_threshold=threshold)
        status = "PASS" if result["fish_name"] else "FAIL"
        print(f"  threshold={threshold:.1f}: score={result['match_score']:.4f} "
              f"name={result.get('fish_name', 'None')} [{status}]")

    # --- Background color analysis of inner crop ---
    print(f"\n--- Background Color Analysis ---")
    frame_margin = 0.15
    fh, fw = fish_sprite_crop.shape[:2]
    mx = int(fw * frame_margin)
    my = int(fh * frame_margin)
    inner = fish_sprite_crop[my : fh - my, mx : fw - mx]

    # Sample background regions (edges of inner crop where fish isn't)
    top_strip = inner[:5, :, :]
    bottom_strip = inner[-5:, :, :]
    left_strip = inner[:, :5, :]
    right_strip = inner[:, -5:, :]

    for name, strip in [("top", top_strip), ("bottom", bottom_strip),
                         ("left", left_strip), ("right", right_strip)]:
        mean_bgr = strip.mean(axis=(0, 1))
        print(f"  {name} strip mean BGR: [{mean_bgr[0]:.1f}, {mean_bgr[1]:.1f}, {mean_bgr[2]:.1f}]")


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO, format="%(name)s: %(message)s")

    dump_sprite_info()

    if len(sys.argv) < 2:
        print("Usage: python scripts/debug_caught_fish_results.py <image1> [image2] ...")
        sys.exit(1)
    for img_path in sys.argv[1:]:
        run_full_pipeline(img_path)
