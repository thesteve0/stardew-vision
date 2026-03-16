#!/usr/bin/env python3
"""
Verify UI Reference Screenshots

This script checks that collected UI reference screenshots meet the required
specifications and extracts basic measurements for documentation.

Usage:
    python scripts/verify_ui_screenshots.py
"""

import sys
from pathlib import Path
from typing import Dict, List, Tuple
from PIL import Image

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class ScreenshotVerifier:
    """Verify and analyze UI reference screenshots."""

    # Required screenshots (Priority 1)
    ESSENTIAL_SCREENSHOTS = [
        "chest_empty_treasure_3x9.png",
        "chest_empty_storage_3x12.png",
        "chest_partial_treasure.png",
        "chest_partial_storage.png",
        "chest_full_treasure.png",
        "chest_full_storage.png",
    ]

    # Recommended screenshots (Priority 2)
    RECOMMENDED_SCREENSHOTS = [
        "chest_with_empty_inventory.png",
        "chest_with_partial_inventory.png",
        "inventory_empty_closeup.png",
        "inventory_partial_closeup.png",
    ]

    # Optional screenshots (Priority 3)
    OPTIONAL_SCREENSHOTS = [
        "chest_stacked_items.png",
    ]

    def __init__(self, ui_frames_dir: Path):
        """Initialize verifier with UI frames directory."""
        self.ui_frames_dir = ui_frames_dir
        self.results = {}

    def verify_all(self) -> Dict[str, dict]:
        """Verify all screenshots and return results."""
        print("=" * 80)
        print("UI Reference Screenshot Verification")
        print("=" * 80)
        print()

        # Check essential screenshots
        print("Priority 1: Essential Screenshots (REQUIRED)")
        print("-" * 80)
        essential_results = self._check_screenshots(self.ESSENTIAL_SCREENSHOTS)
        self._print_results(essential_results)
        print()

        # Check recommended screenshots
        print("Priority 2: Recommended Screenshots")
        print("-" * 80)
        recommended_results = self._check_screenshots(self.RECOMMENDED_SCREENSHOTS)
        self._print_results(recommended_results)
        print()

        # Check optional screenshots
        print("Priority 3: Optional Screenshots")
        print("-" * 80)
        optional_results = self._check_screenshots(self.OPTIONAL_SCREENSHOTS)
        self._print_results(optional_results)
        print()

        # Check for any additional screenshots
        print("Additional Screenshots Found")
        print("-" * 80)
        self._check_additional_screenshots()
        print()

        # Summary
        self._print_summary(essential_results, recommended_results, optional_results)

        return {
            "essential": essential_results,
            "recommended": recommended_results,
            "optional": optional_results,
        }

    def _check_screenshots(self, screenshot_list: List[str]) -> Dict[str, dict]:
        """Check a list of screenshots and return results."""
        results = {}
        for filename in screenshot_list:
            filepath = self.ui_frames_dir / filename
            results[filename] = self._verify_screenshot(filepath)
        return results

    def _verify_screenshot(self, filepath: Path) -> dict:
        """Verify a single screenshot and extract metadata."""
        result = {
            "exists": False,
            "valid_png": False,
            "resolution": None,
            "mode": None,
            "file_size": None,
            "error": None,
        }

        # Check if file exists
        if not filepath.exists():
            result["error"] = "File not found"
            return result

        result["exists"] = True
        result["file_size"] = filepath.stat().st_size

        # Try to open as image
        try:
            with Image.open(filepath) as img:
                # Verify it's a PNG
                if img.format != "PNG":
                    result["error"] = f"Wrong format: {img.format} (expected PNG)"
                    return result

                result["valid_png"] = True
                result["resolution"] = img.size  # (width, height)
                result["mode"] = img.mode  # RGB, RGBA, etc.

                # Check for reasonable resolution (at least 640x480)
                width, height = img.size
                if width < 640 or height < 480:
                    result["error"] = f"Resolution too low: {width}×{height}"
                    return result

        except Exception as e:
            result["error"] = f"Failed to open image: {str(e)}"
            return result

        return result

    def _print_results(self, results: Dict[str, dict]):
        """Print verification results for a set of screenshots."""
        for filename, result in results.items():
            status = "✓" if result["exists"] and result["valid_png"] else "✗"
            print(f"  {status} {filename}")

            if result["exists"] and result["valid_png"]:
                width, height = result["resolution"]
                size_mb = result["file_size"] / (1024 * 1024)
                print(f"      Resolution: {width}×{height} | Mode: {result['mode']} | Size: {size_mb:.2f} MB")
            elif result["exists"]:
                print(f"      Error: {result['error']}")
            else:
                print(f"      Status: Not collected yet")

    def _check_additional_screenshots(self):
        """Check for any PNG files not in the defined lists."""
        all_expected = set(
            self.ESSENTIAL_SCREENSHOTS
            + self.RECOMMENDED_SCREENSHOTS
            + self.OPTIONAL_SCREENSHOTS
            + ["chest_ui_reference.png"]  # Original reference
        )

        png_files = list(self.ui_frames_dir.glob("*.png"))
        additional = [f for f in png_files if f.name not in all_expected]

        if additional:
            for filepath in additional:
                result = self._verify_screenshot(filepath)
                status = "✓" if result["valid_png"] else "✗"
                print(f"  {status} {filepath.name}")
                if result["valid_png"]:
                    width, height = result["resolution"]
                    size_mb = result["file_size"] / (1024 * 1024)
                    print(f"      Resolution: {width}×{height} | Mode: {result['mode']} | Size: {size_mb:.2f} MB")
        else:
            print("  (None found)")

    def _print_summary(
        self,
        essential: Dict[str, dict],
        recommended: Dict[str, dict],
        optional: Dict[str, dict],
    ):
        """Print overall summary."""
        print("=" * 80)
        print("Summary")
        print("=" * 80)

        essential_complete = sum(1 for r in essential.values() if r["valid_png"])
        essential_total = len(essential)

        recommended_complete = sum(1 for r in recommended.values() if r["valid_png"])
        recommended_total = len(recommended)

        optional_complete = sum(1 for r in optional.values() if r["valid_png"])
        optional_total = len(optional)

        print(f"Essential (Priority 1):    {essential_complete}/{essential_total} collected")
        print(f"Recommended (Priority 2):  {recommended_complete}/{recommended_total} collected")
        print(f"Optional (Priority 3):     {optional_complete}/{optional_total} collected")
        print()

        if essential_complete == essential_total:
            print("✓ All essential screenshots collected! Ready for synthetic data generation.")
        else:
            missing = essential_total - essential_complete
            print(f"⚠ {missing} essential screenshot(s) still needed before proceeding.")
            print("  See COLLECTION_GUIDE.md for instructions.")

        print()


def main():
    """Main entry point."""
    # Determine ui_frames directory
    project_root = Path(__file__).parent.parent
    ui_frames_dir = project_root / "datasets" / "assets" / "ui_frames"

    if not ui_frames_dir.exists():
        print(f"Error: UI frames directory not found: {ui_frames_dir}")
        print("Expected location: datasets/assets/ui_frames/")
        sys.exit(1)

    # Run verification
    verifier = ScreenshotVerifier(ui_frames_dir)
    results = verifier.verify_all()

    # Return exit code based on essential screenshots
    essential_complete = sum(
        1 for r in results["essential"].values() if r["valid_png"]
    )
    essential_total = len(results["essential"])

    if essential_complete < essential_total:
        sys.exit(1)  # Not all essential screenshots collected
    else:
        sys.exit(0)  # Success


if __name__ == "__main__":
    main()
