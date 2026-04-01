#!/usr/bin/env python3
"""
Interactive annotation tool for Pierre's shop screenshots.

Shows each image and prompts for the 5 expected_extraction fields.
"""

import json
import re
import sys
from pathlib import Path

from PIL import Image

def load_annotations(jsonl_path: Path) -> list[dict]:
    """Load all annotations from JSONL file."""
    annotations = []
    with open(jsonl_path) as f:
        for line in f:
            annotations.append(json.loads(line))
    return annotations


def save_annotations(jsonl_path: Path, annotations: list[dict]):
    """Save annotations back to JSONL file."""
    with open(jsonl_path, 'w') as f:
        for annotation in annotations:
            f.write(json.dumps(annotation) + '\n')
    print(f"\n✓ Saved {len(annotations)} annotations to {jsonl_path}")


def show_image(image_path: str):
    """Display image path for manual viewing."""
    try:
        img = Image.open(image_path)
        width, height = img.size

        print(f"\n{'='*70}")
        print(f"IMAGE TO ANNOTATE:")
        print(f"{'='*70}")
        print(f"File: {image_path}")
        print(f"Size: {width}x{height}")
        print(f"\nPlease open this file on your HOST machine to view it.")
        print(f"(The file is in the workspace folder, accessible from your host)")
        print(f"{'='*70}\n")

        input("Press ENTER when you've viewed the image and are ready to annotate...")
        return True
    except Exception as e:
        print(f"ERROR: Could not load image: {image_path} - {e}")
        return False


def prompt_extraction_fields() -> dict:
    """Prompt user for the 5 extraction fields."""
    print("\n" + "="*60)
    print("Enter the values from the RIGHT PANEL (detail view):")
    print("="*60)

    name = input("Item name: ").strip()
    description = input("Item description: ").strip()

    while True:
        try:
            price_per_unit = int(input("Price per unit (gold): ").strip())
            break
        except ValueError:
            print("  ✗ Please enter a valid integer")

    while True:
        try:
            quantity_selected = int(input("Quantity selected: ").strip())
            break
        except ValueError:
            print("  ✗ Please enter a valid integer")

    while True:
        try:
            total_cost = int(input("Total cost (gold): ").strip())
            break
        except ValueError:
            print("  ✗ Please enter a valid integer")

    # Verify math
    expected_total = price_per_unit * quantity_selected
    if total_cost != expected_total:
        print(f"\n⚠ WARNING: total_cost ({total_cost}) != price_per_unit ({price_per_unit}) × quantity_selected ({quantity_selected}) = {expected_total}")
        confirm = input("Continue anyway? [y/N]: ").strip().lower()
        if confirm != 'y':
            print("Aborting this annotation.")
            return None

    # Energy and health (optional)
    print("\nOptional fields (press ENTER to skip):")

    while True:
        energy = input("Energy (e.g., '+13' or leave blank): ").strip()
        if not energy or re.match(r'^[+\-]\d+$', energy):
            break
        print("  ✗ Data entry error, please try to enter the data again")

    while True:
        health = input("Health (e.g., '+5' or leave blank): ").strip()
        if not health or re.match(r'^[+\-]\d+$', health):
            break
        print("  ✗ Data entry error, please try to enter the data again")

    return {
        "name": name,
        "description": description,
        "price_per_unit": price_per_unit,
        "quantity_selected": quantity_selected,
        "total_cost": total_cost,
        "energy": energy,
        "health": health
    }


def annotate_interactive(jsonl_path: Path, only_failed: bool = True):
    """Interactive annotation session."""
    print(f"Loading annotations from: {jsonl_path}")
    annotations = load_annotations(jsonl_path)

    # Filter which annotations need work
    if only_failed:
        to_annotate = [a for a in annotations if not a.get("extraction_succeeded", False)]
        print(f"\nFound {len(to_annotate)} images that need manual annotation")
    else:
        to_annotate = annotations
        print(f"\nAnnotating all {len(to_annotate)} images")

    if not to_annotate:
        print("No images to annotate!")
        return

    print("\nInstructions:")
    print("- Look at the RIGHT PANEL (orange detail view)")
    print("- Enter the 5 fields as shown in the panel")
    print("- Press ENTER with empty input to skip an image")
    print("- Press Ctrl+C to quit and save progress")
    print()

    modified_count = 0

    try:
        for i, annotation in enumerate(to_annotate, 1):
            print(f"\n{'='*60}")
            print(f"Image {i} / {len(to_annotate)}")
            print(f"{'='*60}")
            print(f"File: {annotation['original_file_name']}")
            print(f"Hash: {annotation['image_hash'][:16]}...")
            print(f"Resolution: {annotation['resolution'][0]}x{annotation['resolution'][1]}")

            # Show current extraction (if any)
            current = annotation['expected_extraction']
            if current['name']:
                print(f"\nCurrent annotation:")
                print(f"  Name: {current['name']}")
                print(f"  Description: {current['description']}")
                print(f"  Price per unit: {current['price_per_unit']}g")
                print(f"  Quantity selected: {current['quantity_selected']}")
                print(f"  Total cost: {current['total_cost']}g")
                if current.get('energy'):
                    print(f"  Energy: {current['energy']}")
                if current.get('health'):
                    print(f"  Health: {current['health']}")

            # Show the image
            print(f"\nDisplaying image: {annotation['image_path']}")
            if not show_image(annotation['image_path']):
                print("Skipping this image due to load error.")
                continue

            # Prompt for action
            print("\nOptions:")
            print("  [a] Annotate/update this image")
            print("  [s] Skip this image")
            print("  [q] Quit and save")

            action = input("Choose [a/s/q]: ").strip().lower()

            if action == 'q':
                print("\nQuitting...")
                break
            elif action == 's':
                print("Skipping.")
                continue
            elif action == 'a':
                # Prompt for fields
                extraction = prompt_extraction_fields()
                if extraction is None:
                    continue  # User aborted

                # Update annotation
                annotation['expected_extraction'] = extraction
                annotation['annotated_by'] = 'human'
                annotation['extraction_succeeded'] = True
                if 'notes' in annotation:
                    del annotation['notes']

                modified_count += 1
                print(f"✓ Annotation updated ({modified_count} total)")
            else:
                print("Invalid choice, skipping.")
                continue

    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")

    # Save all annotations
    if modified_count > 0:
        print(f"\n{'='*60}")
        print(f"Saving {modified_count} modified annotations...")
        save_annotations(jsonl_path, annotations)
    else:
        print("\nNo annotations were modified.")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Interactive annotation tool")
    parser.add_argument(
        '--annotations',
        type=Path,
        default=Path('datasets/pierre_shop/annotations.jsonl'),
        help='Path to annotations JSONL file'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Annotate all images (not just failed extractions)'
    )

    args = parser.parse_args()

    if not args.annotations.exists():
        print(f"ERROR: Annotations file not found: {args.annotations}")
        sys.exit(1)

    annotate_interactive(args.annotations, only_failed=not args.all)


if __name__ == '__main__':
    main()
