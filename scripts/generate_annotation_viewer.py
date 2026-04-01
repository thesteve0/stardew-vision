#!/usr/bin/env python3
"""Generate an HTML viewer for annotation images."""

import json
from pathlib import Path

def generate_viewer(annotations_jsonl: Path, output_html: Path, all_images: bool = True):
    """Generate HTML page showing images for annotation.

    Args:
        annotations_jsonl: Path to annotations JSONL file
        output_html: Path to output HTML file
        all_images: If True, show all images. If False, show only failed extractions.
    """

    # Load annotations
    annotations = []
    with open(annotations_jsonl) as f:
        for line in f:
            annotation = json.loads(line)
            if all_images or not annotation.get('extraction_succeeded', False):
                annotations.append(annotation)

    # Generate HTML
    html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Pierre's Shop Annotation Viewer</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }
        h1 {
            color: #333;
        }
        .image-card {
            background: white;
            margin: 20px 0;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .image-card h2 {
            margin-top: 0;
            color: #d97000;
        }
        .image-card img {
            max-width: 100%;
            height: auto;
            border: 2px solid #ddd;
            border-radius: 4px;
        }
        .metadata {
            margin: 10px 0;
            color: #666;
            font-size: 0.9em;
        }
        .status-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.85em;
            font-weight: bold;
            color: white;
            margin-left: 10px;
        }
        .instructions {
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 15px;
            margin-bottom: 30px;
        }
    </style>
</head>
<body>
    <h1>Pierre's Shop - Images to Annotate</h1>

    <div class="instructions">
        <h3>Instructions:</h3>
        <ol>
            <li>Keep this page open while running <code>python scripts/interactive_annotate.py</code></li>
            <li>For each image, look at the <strong>RIGHT PANEL</strong> (orange detail view)</li>
            <li>Enter the 5 fields into the terminal when prompted</li>
            <li>Images marked with ✓ are already annotated (you can skip or review them)</li>
        </ol>
    </div>

"""

    for i, annotation in enumerate(annotations, 1):
        # Check if already annotated
        is_annotated = annotation.get('extraction_succeeded', False)
        status_badge = "✓ Annotated" if is_annotated else "Needs Annotation"
        badge_color = "#4caf50" if is_annotated else "#ff9800"
        # Make path relative from HTML file location
        img_path = Path(annotation['image_path'])
        # Both HTML and images are in the workspace, so use relative path
        rel_path = img_path

        # Build metadata string
        metadata_parts = [
            f"Hash: {annotation['image_hash'][:16]}...",
            f"Resolution: {annotation['resolution'][0]}x{annotation['resolution'][1]}"
        ]

        # Add energy/health if present and annotated
        if is_annotated:
            extraction = annotation.get('expected_extraction', {})
            if extraction.get('energy'):
                metadata_parts.append(f"Energy: {extraction['energy']}")
            if extraction.get('health'):
                metadata_parts.append(f"Health: {extraction['health']}")

        metadata_str = " | ".join(metadata_parts)

        html += f"""
    <div class="image-card" id="img-{i}">
        <h2>#{i} - {annotation['original_file_name']}<span class="status-badge" style="background-color: {badge_color}">{status_badge}</span></h2>
        <div class="metadata">
            {metadata_str}
        </div>
        <img src="{rel_path}" alt="{annotation['original_file_name']}">
    </div>
"""

    # Count how many need annotation
    needs_annotation = sum(1 for a in annotations if not a.get('extraction_succeeded', False))
    already_done = len(annotations) - needs_annotation

    html += f"""
    <div style="margin-top: 40px; padding: 20px; background: #e8f5e9; border-radius: 8px;">
        <p><strong>Total images: {len(annotations)}</strong> ({already_done} already annotated, {needs_annotation} need annotation)</p>
        <p>After completing annotations, validate with:<br>
        <code>python scripts/annotate_pierre_shop.py --mode validate --annotations datasets/annotated/pierre_shop/annotations.jsonl</code></p>
    </div>
</body>
</html>
"""

    # Write HTML
    with open(output_html, 'w') as f:
        f.write(html)

    print(f"✓ Generated annotation viewer: {output_html}")
    print(f"  {len(annotations)} images included")
    print(f"\n  Open this file in your web browser, then run:")
    print(f"  python scripts/interactive_annotate.py")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="Generate HTML annotation viewer")
    parser.add_argument(
        '--annotations',
        type=Path,
        default=Path('datasets/pierre_shop/annotations.jsonl'),
        help='Annotations JSONL file'
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=Path('annotation_viewer.html'),
        help='Output HTML file'
    )
    parser.add_argument(
        '--failed-only',
        action='store_true',
        help='Show only images that need annotation (default: show all images)'
    )

    args = parser.parse_args()
    generate_viewer(args.annotations, args.output, all_images=not args.failed_only)
