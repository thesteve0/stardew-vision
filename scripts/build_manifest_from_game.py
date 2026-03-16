#!/usr/bin/env python3
"""
Build the item manifest from the actual game data (SMAPI export).

This script processes the Data/Objects.json file exported by SMAPI and
extracts individual sprites from springobjects.png using the SpriteIndex field.
"""

import json
from pathlib import Path
from PIL import Image


def build_manifest_from_game(
    objects_json_path: Path,
    sprite_sheet_path: Path,
    output_manifest_path: Path,
    output_sprites_dir: Path,
    sprite_size: int = 16,
    sheet_columns: int = 24
):
    """
    Build item manifest and extract sprites from game data.

    Args:
        objects_json_path: Path to Data_Objects.json (SMAPI export)
        sprite_sheet_path: Path to springobjects.png
        output_manifest_path: Path to save item_manifest.json
        output_sprites_dir: Directory to save individual sprites
        sprite_size: Size of each sprite (16×16)
        sheet_columns: Number of columns in sprite sheet (24)
    """
    # Load the Objects data
    print(f"Loading Objects data from: {objects_json_path}")
    with open(objects_json_path) as f:
        objects_data = json.load(f)

    print(f"✓ Loaded {len(objects_data)} items")

    # Load the sprite sheet
    print(f"Loading sprite sheet from: {sprite_sheet_path}")
    sprite_sheet = Image.open(sprite_sheet_path)
    print(f"✓ Sprite sheet: {sprite_sheet.size[0]}×{sprite_sheet.size[1]} pixels")

    # Create output directory
    output_sprites_dir.mkdir(parents=True, exist_ok=True)

    # Build manifest and extract sprites
    manifest = {}
    extracted_count = 0
    skipped_count = 0

    for item_id, item_data in objects_data.items():
        # Get sprite index
        sprite_index = item_data.get('SpriteIndex', None)

        if sprite_index is None:
            print(f"Warning: Item {item_id} has no SpriteIndex, skipping")
            skipped_count += 1
            continue

        # Extract item info
        item_name = item_data.get('Name', f'Item_{item_id}')
        display_name = item_data.get('DisplayName', item_name)
        item_type = item_data.get('Type', 'Unknown')
        category_num = item_data.get('Category', -999)
        description = item_data.get('Description', '')

        # Calculate sprite position in the sheet
        row = sprite_index // sheet_columns
        col = sprite_index % sheet_columns

        # Extract sprite from sheet
        x = col * sprite_size
        y = row * sprite_size

        try:
            sprite = sprite_sheet.crop((x, y, x + sprite_size, y + sprite_size))
            sprite_filename = f"sprite_{item_id}.png"
            sprite_path = output_sprites_dir / sprite_filename
            sprite.save(sprite_path)
            extracted_count += 1
        except Exception as e:
            print(f"Error extracting sprite for item {item_id} at index {sprite_index}: {e}")
            skipped_count += 1
            continue

        # Add to manifest
        manifest[item_id] = {
            "name": item_name,
            "display_name": display_name,
            "type": item_type,
            "category": category_num,
            "description": description,
            "sprite_index": sprite_index,
            "sprite_file": f"sprites/{sprite_filename}",
            "price": item_data.get('Price', 0),
            "edibility": item_data.get('Edibility', -300)
        }

    # Save manifest
    print(f"\nSaving manifest to: {output_manifest_path}")
    with open(output_manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)

    print(f"\n✓ Manifest created: {len(manifest)} items")
    print(f"✓ Sprites extracted: {extracted_count}")
    print(f"✓ Skipped: {skipped_count}")
    print(f"✓ Output directory: {output_sprites_dir}")

    # Print some sample items
    print("\nSample items:")
    sample_ids = ['334', '335', '336', '338', '390', '388']  # Bars, stone, wood
    for item_id in sample_ids:
        if item_id in manifest:
            item = manifest[item_id]
            print(f"  {item_id}: {item['name']} (Type: {item['type']}, SpriteIndex: {item['sprite_index']})")

    return manifest


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--objects',
        type=Path,
        default=Path('datasets/assets/game_files/Data_Objects.json'),
        help='Path to SMAPI-exported Objects JSON'
    )
    parser.add_argument(
        '--sheet',
        type=Path,
        default=Path('datasets/assets/game_files/springobjects.png'),
        help='Path to springobjects.png'
    )
    parser.add_argument(
        '--manifest',
        type=Path,
        default=Path('datasets/assets/item_manifest_game.json'),
        help='Output path for item manifest'
    )
    parser.add_argument(
        '--sprites',
        type=Path,
        default=Path('datasets/assets/sprites_game'),
        help='Output directory for extracted sprites'
    )

    args = parser.parse_args()
    build_manifest_from_game(
        args.objects,
        args.sheet,
        args.manifest,
        args.sprites
    )


if __name__ == '__main__':
    main()
