#!/usr/bin/env python3
"""
Helper script to organize collected screenshots into dataset directories.

Usage:
    python organize_screenshot.py /path/to/screenshot.jpg \\
        --screen-type tv_dialog \\
        --name tv_weather_01

This will:
1. Copy the screenshot to datasets/{screen_type}/images/{name}.jpg
2. Generate a UUID for the image
3. Create a stub annotation entry in annotations.jsonl
4. Print the new path for verification
"""

import argparse
import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path


def organize_screenshot(
    source_path: str,
    screen_type: str,
    name: str,
    base_dir: str = "/workspaces/stardew-vision/datasets"
) -> dict:
    """
    Organize a screenshot into the appropriate dataset directory.

    Args:
        source_path: Path to the source screenshot file
        screen_type: Type of screen (tv_dialog, caught_fish, etc.)
        name: Desired filename (without extension)
        base_dir: Base datasets directory

    Returns:
        dict with image_id, destination path, and stub annotation
    """
    source = Path(source_path)
    if not source.exists():
        raise FileNotFoundError(f"Source file not found: {source_path}")

    # Determine destination
    dataset_dir = Path(base_dir) / screen_type
    images_dir = dataset_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    # Get file extension from source
    extension = source.suffix.lower()
    if extension not in ['.jpg', '.jpeg', '.png']:
        raise ValueError(f"Unsupported file format: {extension}")

    # Destination path
    dest_filename = f"{name}{extension}"
    dest_path = images_dir / dest_filename

    # Copy file
    shutil.copy2(source, dest_path)
    print(f"✓ Copied to: {dest_path}")

    # Generate UUID and stub annotation
    image_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()

    stub_annotation = {
        "image_id": image_id,
        "image_path": f"images/{dest_filename}",
        "screen_type": screen_type,
        "timestamp": timestamp,
        "ocr_fields": {},  # To be filled during annotation
        "narration": "",    # To be filled during annotation
        "tool_call": f"crop_{screen_type}",
        "metadata": {
            "collection_method": "manual",
            "ui_scale": "enlarged"
        }
    }

    # Append to annotations.jsonl
    annotations_file = dataset_dir / "annotations.jsonl"
    with open(annotations_file, 'a') as f:
        f.write(json.dumps(stub_annotation) + '\n')

    print(f"✓ Added stub annotation with image_id: {image_id}")
    print(f"✓ Appended to: {annotations_file}")

    return {
        "image_id": image_id,
        "dest_path": str(dest_path),
        "annotation": stub_annotation
    }


def main():
    parser = argparse.ArgumentParser(
        description="Organize screenshots into dataset directories"
    )
    parser.add_argument(
        "source_path",
        help="Path to the screenshot file to organize"
    )
    parser.add_argument(
        "--screen-type",
        required=True,
        choices=[
            "pierre_shop",
            "tv_dialog",
            "caught_fish",
            "quest_board",
            "game_letter",
            "level_up"
        ],
        help="Type of screen in the screenshot"
    )
    parser.add_argument(
        "--name",
        required=True,
        help="Desired filename (without extension), e.g., tv_weather_01"
    )
    parser.add_argument(
        "--base-dir",
        default="/workspaces/stardew-vision/datasets",
        help="Base datasets directory (default: /workspaces/stardew-vision/datasets)"
    )

    args = parser.parse_args()

    try:
        result = organize_screenshot(
            args.source_path,
            args.screen_type,
            args.name,
            args.base_dir
        )
        print("\n✓ Screenshot organized successfully!")
        print(f"\nNext steps:")
        print(f"1. Verify the screenshot looks correct: {result['dest_path']}")
        print(f"2. After building extraction tool, run it on this image")
        print(f"3. Manually verify OCR output and update annotation in annotations.jsonl")
        print(f"4. Track progress in docs/phase2-collection-plan.md")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
