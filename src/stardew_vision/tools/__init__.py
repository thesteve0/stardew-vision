"""
Tool registry for Stardew Vision extraction agents.

TODO (NEXT SESSION - 2026-03-21):
1. Define extraction tool in OpenAI function-calling format (add TOOL_DEFINITIONS)
2. Build VLM orchestrator wrapper to call this tool
3. Test VLM calling the agent with Pierre's shop screenshot
4. Research: LangGraph, CrewAI, or other agent frameworks for orchestration
"""

from stardew_vision.tools.crop_pierres_detail_panel import crop_pierres_detail_panel

TOOL_REGISTRY = {
    "crop_pierres_detail_panel": crop_pierres_detail_panel,
}
