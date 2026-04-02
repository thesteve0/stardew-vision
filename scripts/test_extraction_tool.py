"""
Test the Pierre's shop extraction tool on the original screenshot.
"""

from stardew_vision.tools.crop_pierres_detail_panel import crop_pierres_detail_panel_from_path as crop_pierres_detail_panel
import json

# Test on the original screenshot
screenshot_path = 'datasets/from-katarina/1_pierres_top.jpg'

print("Testing extraction tool on:", screenshot_path)
print("=" * 80)

try:
    result = crop_pierres_detail_panel(screenshot_path, debug=True)

    print("\n" + "=" * 80)
    print("EXTRACTED FIELDS:")
    print("=" * 80)
    print(json.dumps(result, indent=2))

except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
