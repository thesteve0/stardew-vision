"""OpenAI function-calling definitions sent to Qwen in every loop request.

These are the tool *schemas* only — no implementation. The coordinator
dispatches actual tool calls over HTTP to the OCR microservice.

Design: image_b64 is NOT in any tool definition. The coordinator injects it
at dispatch time so Qwen never needs to generate or pass image bytes.

TTS is NOT a tool — FastAPI calls it directly after parsing Qwen's final JSON.
"""

TOOL_DEFINITIONS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "crop_pierres_detail_panel",
            "description": (
                "Extract item details from Pierre's General Store detail panel using OCR. "
                "Returns name, description, price_per_unit, quantity_selected, total_cost, "
                "energy, and health."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "debug": {
                        "type": "boolean",
                        "description": (
                            "When true, also returns ocr_raw — a list of "
                            "{text, score, rel_y} dicts sorted by vertical position. "
                            "Use only for manual debugging — not normally needed."
                        ),
                    }
                },
                "required": [],
            },
        },
    },
]
