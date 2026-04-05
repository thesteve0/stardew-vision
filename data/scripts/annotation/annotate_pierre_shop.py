#!/usr/bin/env python3
"""
Pierre's Shop Annotation Tool

Supports three modes:
- auto: Auto-generate annotations using the extraction tool
- validate: Validate annotations against schema and run quality checks
- review: Interactive review/correction of annotations
"""

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cv2
import jsonschema
from PIL import Image
from rapidfuzz import fuzz

from stardew_vision.tools.crop_pierres_detail_panel import (
    PanelNotFoundError,
    crop_pierres_detail_panel,
)


def load_schema(schema_path: Path) -> dict:
    """Load JSON schema for validation."""
    with open(schema_path) as f:
        return json.load(f)


def generate_annotation(
    image_path: Path, extraction_result: dict | None, extraction_succeeded: bool
) -> dict:
    """Generate annotation record from extraction result."""
    # Get image resolution
    img = Image.open(image_path)
    width, height = img.size

    # Compute SHA256 hash of the image file
    with open(image_path, "rb") as f:
        image_hash = hashlib.sha256(f.read()).hexdigest()

    # Create annotation
    # Handle both absolute and relative paths
    if image_path.is_absolute():
        try:
            rel_path = image_path.relative_to(Path.cwd())
        except ValueError:
            rel_path = image_path
    else:
        rel_path = image_path

    annotation = {
        "image_hash": image_hash,
        "original_file_name": image_path.name,
        "screen_type": "pierre_shop",
        "image_path": str(rel_path),
        "resolution": [width, height],
        "expected_extraction": extraction_result
        or {
            "name": "",
            "description": "",
            "price_per_unit": 0,
            "quantity_selected": 0,
            "total_cost": 0,
            "energy": "",
            "health": "",
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
        "annotated_by": "auto" if extraction_succeeded else "manual_required",
        "extraction_succeeded": extraction_succeeded,
        "version": "1.0",
    }

    if not extraction_succeeded:
        annotation["notes"] = "Template matching failed - manual annotation required"

    return annotation


def auto_generate(input_dir: Path, output_file: Path):
    """Auto-generate annotations from screenshots."""
    print(f"Auto-generating annotations from {input_dir}")
    print(f"Output: {output_file}")

    # Get all image files
    image_files = sorted(input_dir.glob("*.jpg")) + sorted(input_dir.glob("*.png"))
    print(f"Found {len(image_files)} images")

    annotations = []
    succeeded = 0
    failed = 0

    for img_path in image_files:
        print(f"\nProcessing: {img_path.name}")
        try:
            # Run extraction tool
            result = crop_pierres_detail_panel(str(img_path), debug=False)
            annotation = generate_annotation(img_path, result, True)
            succeeded += 1
            print(f"  ✓ Extracted: {result['name']}")
        except PanelNotFoundError as e:
            print(f"  ✗ Panel not found: {e}")
            annotation = generate_annotation(img_path, None, False)
            failed += 1
        except Exception as e:
            print(f"  ✗ Error: {e}")
            annotation = generate_annotation(img_path, None, False)
            failed += 1

        annotations.append(annotation)

    # Write JSONL
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w") as f:
        for annotation in annotations:
            f.write(json.dumps(annotation) + "\n")

    print(f"\n{'='*60}")
    print(f"Annotation generation complete!")
    print(f"Total: {len(annotations)}")
    print(f"Succeeded: {succeeded}")
    print(f"Failed: {failed}")
    print(f"Output: {output_file}")


def validate_annotations(annotations_file: Path, schema_path: Path):
    """Validate annotations and generate quality report."""
    print(f"Validating annotations: {annotations_file}")

    # Load schema
    schema = load_schema(schema_path)

    # Load annotations
    annotations = []
    with open(annotations_file) as f:
        for line_num, line in enumerate(f, 1):
            try:
                annotation = json.loads(line)
                annotations.append((line_num, annotation))
            except json.JSONDecodeError as e:
                print(f"✗ Line {line_num}: Invalid JSON: {e}")

    print(f"Loaded {len(annotations)} annotations")

    # Validation results
    schema_errors = []
    integrity_errors = []
    constraint_errors = []
    extraction_comparisons = []

    for line_num, annotation in annotations:
        # Schema validation
        try:
            jsonschema.validate(annotation, schema)
        except jsonschema.ValidationError as e:
            schema_errors.append((line_num, annotation["image_path"], str(e.message)))

        # Referential integrity
        image_path = Path(annotation["image_path"])
        if not image_path.exists():
            integrity_errors.append(
                (line_num, str(image_path), "Image file does not exist")
            )

        # Field constraints
        extraction = annotation["expected_extraction"]
        expected_total = extraction["price_per_unit"] * extraction["quantity_selected"]
        if extraction["total_cost"] != expected_total:
            constraint_errors.append(
                (
                    line_num,
                    annotation["image_path"],
                    f"total_cost={extraction['total_cost']} != "
                    f"price_per_unit={extraction['price_per_unit']} × "
                    f"quantity_selected={extraction['quantity_selected']} = {expected_total}",
                )
            )

        # Re-run extraction and compare (only if image exists and extraction originally succeeded)
        if image_path.exists() and annotation["extraction_succeeded"]:
            try:
                new_result = crop_pierres_detail_panel(str(image_path), debug=False)
                # Compare fields
                name_match = fuzz.ratio(
                    extraction["name"].lower(), new_result["name"].lower()
                )
                desc_match = fuzz.ratio(
                    extraction["description"].lower(),
                    new_result["description"].lower(),
                )
                price_match = extraction["price_per_unit"] == new_result["price_per_unit"]
                qty_match = (
                    extraction["quantity_selected"] == new_result["quantity_selected"]
                )
                total_match = extraction["total_cost"] == new_result["total_cost"]

                extraction_comparisons.append(
                    {
                        "image": annotation["image_path"],
                        "name_similarity": name_match,
                        "desc_similarity": desc_match,
                        "price_exact": price_match,
                        "quantity_exact": qty_match,
                        "total_exact": total_match,
                    }
                )
            except Exception as e:
                extraction_comparisons.append(
                    {"image": annotation["image_path"], "error": str(e)}
                )

    # Print validation results
    print(f"\n{'='*60}")
    print("VALIDATION RESULTS")
    print(f"{'='*60}")

    print(f"\n[1] Schema Validation: ", end="")
    if not schema_errors:
        print("✓ PASS (all annotations valid)")
    else:
        print(f"✗ FAIL ({len(schema_errors)} errors)")
        for line_num, img_path, error in schema_errors[:5]:
            print(f"  Line {line_num} ({img_path}): {error}")
        if len(schema_errors) > 5:
            print(f"  ... and {len(schema_errors) - 5} more")

    print(f"\n[2] Referential Integrity: ", end="")
    if not integrity_errors:
        print("✓ PASS (all image files exist)")
    else:
        print(f"✗ FAIL ({len(integrity_errors)} errors)")
        for line_num, img_path, error in integrity_errors:
            print(f"  Line {line_num} ({img_path}): {error}")

    print(f"\n[3] Field Constraints: ", end="")
    if not constraint_errors:
        print("✓ PASS (all math checks pass)")
    else:
        print(f"✗ FAIL ({len(constraint_errors)} errors)")
        for line_num, img_path, error in constraint_errors:
            print(f"  Line {line_num} ({img_path}): {error}")

    print(f"\n[4] Extraction Comparison:")
    if extraction_comparisons:
        # Compute averages
        total_comps = len(
            [c for c in extraction_comparisons if "error" not in c]
        )
        if total_comps > 0:
            avg_name = sum(
                c["name_similarity"]
                for c in extraction_comparisons
                if "error" not in c
            ) / total_comps
            avg_desc = sum(
                c["desc_similarity"]
                for c in extraction_comparisons
                if "error" not in c
            ) / total_comps
            price_exact = sum(
                c["price_exact"] for c in extraction_comparisons if "error" not in c
            )
            qty_exact = sum(
                c["quantity_exact"]
                for c in extraction_comparisons
                if "error" not in c
            )
            total_exact = sum(
                c["total_exact"] for c in extraction_comparisons if "error" not in c
            )

            print(f"  Name similarity: {avg_name:.1f}%")
            print(f"  Description similarity: {avg_desc:.1f}%")
            print(f"  Price exact match: {price_exact}/{total_comps} ({price_exact/total_comps*100:.1f}%)")
            print(f"  Quantity exact match: {qty_exact}/{total_comps} ({qty_exact/total_comps*100:.1f}%)")
            print(f"  Total exact match: {total_exact}/{total_comps} ({total_exact/total_comps*100:.1f}%)")

        errors = [c for c in extraction_comparisons if "error" in c]
        if errors:
            print(f"\n  Extraction errors: {len(errors)}")
            for comp in errors[:3]:
                print(f"    {comp['image']}: {comp['error']}")

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    total_errors = len(schema_errors) + len(integrity_errors) + len(constraint_errors)
    if total_errors == 0:
        print("✓ All validation checks passed!")
    else:
        print(f"✗ Found {total_errors} total errors")
        print("\nRecommendation: Run --mode review to fix errors")

    # Save quality report
    report_path = annotations_file.parent / "quality_report.json"
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_annotations": len(annotations),
        "schema_errors": len(schema_errors),
        "integrity_errors": len(integrity_errors),
        "constraint_errors": len(constraint_errors),
        "extraction_comparisons": extraction_comparisons,
    }
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nQuality report saved: {report_path}")


def review_annotations(annotations_file: Path):
    """Interactive review/correction of annotations."""
    print(f"Review mode: {annotations_file}")
    print("(Interactive review not yet implemented)")
    print("For now, manually edit the JSONL file or use --mode validate to check quality")


def main():
    parser = argparse.ArgumentParser(description="Pierre's Shop Annotation Tool")
    parser.add_argument(
        "--mode",
        choices=["auto", "validate", "review"],
        required=True,
        help="Operation mode",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("datasets/pierre_shop/images"),
        help="Input directory (for auto mode)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("datasets/pierre_shop/annotations.jsonl"),
        help="Output JSONL file (for auto mode)",
    )
    parser.add_argument(
        "--annotations",
        type=Path,
        default=Path("datasets/pierre_shop/annotations.jsonl"),
        help="Annotations file (for validate/review modes)",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=Path("configs/annotation_schema.json"),
        help="Annotation schema file",
    )

    args = parser.parse_args()

    if args.mode == "auto":
        auto_generate(args.input, args.output)
    elif args.mode == "validate":
        validate_annotations(args.annotations, args.schema)
    elif args.mode == "review":
        review_annotations(args.annotations)


if __name__ == "__main__":
    main()
