"""Tool definitions and system prompt for the fine-tuned Qwen2.5-VL model.

The fine-tuned model was trained with tools baked directly into the system
prompt (not passed via the OpenAI ``tools=`` parameter). The tool injection
text here matches the vLLM chat template's ``{%- if tools -%}`` block output
character-for-character, so the model sees identical token sequences at
training and inference time.

See: stardew-vision-training/evaluation/prompt.py for the training prompt.
"""

import json

# ---------------------------------------------------------------------------
# Tool definitions — must match training exactly (empty parameters for all)
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "crop_tv_dialog",
            "description": "Extract TV show type and dialog text from a TV screen",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "crop_caught_fish_notification",
            "description": (
                "Extract fish name and length from a caught fish notification"
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "crop_pierres_detail_panel",
            "description": (
                "Extract item name, description, price, and quantity "
                "from Pierre's shop detail panel"
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
]

EXTRACTION_TOOLS = {
    "crop_tv_dialog",
    "crop_caught_fish_notification",
    "crop_pierres_detail_panel",
}

NO_TOOL_RESPONSE = "I don't have a tool to handle that screen"

# ---------------------------------------------------------------------------
# System prompt — tools baked in to match training token sequences
# ---------------------------------------------------------------------------

# Tool injection text — rendered with json.dumps to match the Jinja tojson
# filter output from the vLLM chat template. Each tool is a single line of
# compact JSON (no extra whitespace).
_TOOLS_JSON = "\n".join(json.dumps(t) for t in TOOL_DEFINITIONS)

_TASK_PROMPT = (
    "You are a Stardew Valley accessibility assistant. "
    "Analyze the screenshot and call the appropriate extraction tool. "
    "If no extraction tool matches the screen, respond with exactly: "
    f'"{NO_TOOL_RESPONSE}"'
)

_TOOL_INJECTION = (
    "\n\n# Tools\n\n"
    "You may call one or more functions to assist with the user query.\n\n"
    "You are provided with function signatures within <tools></tools> XML tags:\n"
    "<tools>\n"
    f"{_TOOLS_JSON}\n"
    "</tools>\n\n"
    "For each function call, return a json object with function name and "
    "arguments within <tool_call></tool_call> XML tags:\n"
    "<tool_call>\n"
    '{"name": <function-name>, "arguments": <args-json-object>}\n'
    "</tool_call>"
)

SYSTEM_PROMPT_FINETUNED = (
    _TASK_PROMPT
    + _TOOL_INJECTION
    + "\n\nIf no tool matches the screen, respond with only: "
    + NO_TOOL_RESPONSE
)
