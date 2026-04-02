"""
Tool registry for Stardew Vision extraction agents.

Production tools accept base64-encoded image bytes (image_b64: str).
Use the _from_path variants in local scripts and tests.
"""

from stardew_vision.tools.crop_pierres_detail_panel import (
    crop_pierres_detail_panel,
    crop_pierres_detail_panel_from_path,
)

# Registry maps tool names (as the VLM emits them) to their production callables.
# All registered functions accept image_b64: str as their first argument.
TOOL_REGISTRY = {
    "crop_pierres_detail_panel": crop_pierres_detail_panel,
}
