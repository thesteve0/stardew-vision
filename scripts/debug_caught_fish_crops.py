"""
Diagnostic script: save intermediate crops from the caught fish extraction pipeline.

Outputs numbered images to tmp/debug_<label>/ for each input image so we can
visually compare what the tool sees at each stage.

Usage:
    python scripts/debug_caught_fish_crops.py tmp/IMG_0035.PNG tmp/good/IMG_0036.PNG
"""

from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np

# Add the ocr-tools package to the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "services" / "ocr-tools"))

from stardew_ocr_tools.common import (
    crop_region,
    crop_regions,
    decode_image_b64,
    load_image_from_path,
    load_layout,
    strip_letterbox,
)


def save(img: np.ndarray, path: Path, label: str) -> None:
    cv2.imwrite(str(path), img)
    h, w = img.shape[:2]
    ch = img.shape[2] if img.ndim == 3 else 1
    print(f"  {label}: {w}x{h} ch={ch} -> {path.name}")


def run_diagnostics(image_path: str) -> None:
    src = Path(image_path)
    label = src.stem
    out_dir = Path("tmp") / f"debug_{label}"
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"Image: {src}")
    print(f"Output: {out_dir}/")
    print(f"{'='*60}")

    # --- 1. Raw decode (before letterbox strip) ---
    raw_bytes = src.read_bytes()
    raw_arr = np.frombuffer(raw_bytes, dtype=np.uint8)
    raw_img = cv2.imdecode(raw_arr, cv2.IMREAD_COLOR)
    print(f"\nRaw image: {raw_img.shape[1]}x{raw_img.shape[0]}")
    save(raw_img, out_dir / "01_raw.png", "raw")

    # --- 2. After letterbox strip ---
    stripped = strip_letterbox(raw_img)
    print(f"After letterbox strip: {stripped.shape[1]}x{stripped.shape[0]}")
    save(stripped, out_dir / "02_stripped.png", "stripped")

    # --- 3. Load layout and crop regions ---
    layout = load_layout("caught_fish_layout.json")
    print(f"\nLayout regions:")
    for name, region in layout["regions"].items():
        parent = region.get("parent", "full_image")
        print(f"  {name}: x={region['x']:.4f} y={region['y']:.4f} "
              f"w={region['w']:.4f} h={region['h']:.4f} parent={parent}")

    cropped = crop_regions(stripped, layout)

    # --- 4. Notification crop ---
    notif = cropped["notification"]
    save(notif, out_dir / "03_notification.png", "notification")

    # Draw notification region on stripped image for visual check
    img_h, img_w = stripped.shape[:2]
    region_notif = layout["regions"]["notification"]
    x1 = int(region_notif["x"] * img_w)
    y1 = int(region_notif["y"] * img_h)
    x2 = x1 + int(region_notif["w"] * img_w)
    y2 = y1 + int(region_notif["h"] * img_h)
    annotated = stripped.copy()
    cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
    cv2.putText(annotated, "notification", (x1, y1 - 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
    save(annotated, out_dir / "03a_notification_overlay.png", "notification overlay")

    # --- 5. Fish sprite crop ---
    fish = cropped["fish_sprite"]
    save(fish, out_dir / "04_fish_sprite.png", "fish_sprite")

    # Draw fish_sprite region on notification crop for visual check
    region_fish = layout["regions"]["fish_sprite"]
    nf_h, nf_w = notif.shape[:2]
    fx1 = int(region_fish["x"] * nf_w)
    fy1 = int(region_fish["y"] * nf_h)
    fx2 = fx1 + int(region_fish["w"] * nf_w)
    fy2 = fy1 + int(region_fish["h"] * nf_h)
    notif_annotated = notif.copy()
    cv2.rectangle(notif_annotated, (fx1, fy1), (fx2, fy2), (0, 0, 255), 2)
    cv2.putText(notif_annotated, "fish_sprite", (fx1, fy1 - 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
    save(notif_annotated, out_dir / "04a_fish_sprite_overlay.png",
         "fish_sprite overlay on notification")

    # --- 6. Inner crop (after frame_margin stripping) ---
    frame_margin = 0.15
    fh, fw = fish.shape[:2]
    mx = int(fw * frame_margin)
    my = int(fh * frame_margin)
    inner = fish[my : fh - my, mx : fw - mx]
    save(inner, out_dir / "05_inner_no_frame.png", "inner (frame stripped)")

    # --- 7. OCR upscale of notification (3x) ---
    upscale = 3.0
    upscaled_notif = cv2.resize(
        notif, None, fx=upscale, fy=upscale, interpolation=cv2.INTER_CUBIC
    )
    save(upscaled_notif, out_dir / "06_notification_3x.png", "notification 3x upscale")

    # --- 8. Pixel stats for inner crop (background color diagnosis) ---
    print(f"\n  Inner crop pixel stats:")
    print(f"    shape: {inner.shape}")
    if inner.size > 0:
        for ch_name, ch_idx in [("Blue", 0), ("Green", 1), ("Red", 2)]:
            channel = inner[:, :, ch_idx]
            print(f"    {ch_name}: min={channel.min()} max={channel.max()} "
                  f"mean={channel.mean():.1f} std={channel.std():.1f}")

        corners = [
            ("top-left", inner[0, 0]),
            ("top-right", inner[0, -1]),
            ("bottom-left", inner[-1, 0]),
            ("bottom-right", inner[-1, -1]),
        ]
        print(f"    Corner pixel colors (BGR):")
        for name, px in corners:
            print(f"      {name}: {px}")

    print(f"\nDone. Check {out_dir}/ for all diagnostic images.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/debug_caught_fish_crops.py <image1> [image2] ...")
        sys.exit(1)
    for img_path in sys.argv[1:]:
        run_diagnostics(img_path)
