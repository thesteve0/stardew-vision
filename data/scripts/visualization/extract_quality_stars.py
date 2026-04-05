#!/usr/bin/env python3
"""
Extract quality star sprites from Stardew Valley Cursors.png

Based on game source code coordinates:
- Silver star (quality 1): Rectangle(338, 400, 8, 8)
- Gold star (quality 2): Rectangle(346, 400, 8, 8)
- Iridium star (quality 4): Rectangle(346, 392, 8, 8)
"""

from PIL import Image
import os

# Paths
CURSORS_PATH = "datasets/assets/game_files/unpacked/Cursors.png"
OUTPUT_DIR = "datasets/assets/quality_stars"

# Quality star coordinates from game source code
# Format: (x, y, width, height)
STARS = {
    "silver": (338, 400, 8, 8),
    "gold": (346, 400, 8, 8),
    "iridium": (346, 392, 8, 8),
}

def extract_stars():
    """Extract quality star sprites from Cursors.png"""

    # Load the sprite sheet
    print(f"Loading {CURSORS_PATH}...")
    cursors = Image.open(CURSORS_PATH)
    print(f"Cursors.png dimensions: {cursors.size}")

    # Ensure output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Extract each star
    for quality_name, (x, y, width, height) in STARS.items():
        print(f"\nExtracting {quality_name} star...")
        print(f"  Coordinates: ({x}, {y}), size: {width}×{height}")

        # Crop the star region
        # PIL crop uses (left, upper, right, lower)
        star = cursors.crop((x, y, x + width, y + height))

        # Save at 100% scale (original 8×8)
        output_path_100 = os.path.join(OUTPUT_DIR, f"{quality_name}_star_100.png")
        star.save(output_path_100)
        print(f"  Saved: {output_path_100}")

        # Save at 125% scale (10×10) using nearest neighbor to preserve pixel art
        star_125 = star.resize((10, 10), Image.NEAREST)
        output_path_125 = os.path.join(OUTPUT_DIR, f"{quality_name}_star_125.png")
        star_125.save(output_path_125)
        print(f"  Saved: {output_path_125}")

        # Verify transparency
        if star.mode == 'RGBA':
            print(f"  ✓ Has alpha channel (transparency preserved)")
        else:
            print(f"  ⚠ Warning: No alpha channel (mode: {star.mode})")

    print(f"\n✅ All quality stars extracted to {OUTPUT_DIR}/")
    print("\nExtracted files:")
    for quality in ["silver", "gold", "iridium"]:
        print(f"  - {quality}_star_100.png (8×8)")
        print(f"  - {quality}_star_125.png (10×10)")

if __name__ == "__main__":
    extract_stars()
