# Training Data Collection for Phase 2 Fine-Tuning

**Status**: Ready to begin
**Target**: 500-1000 annotated screenshot conversations
**Timeline**: 2-3 weeks for data collection + annotation

## Overview

Phase 2 fine-tuning requires multi-turn conversation data showing Qwen:
1. Looking at a screenshot
2. Calling the correct extraction tool (or returning "unrecognized")
3. Receiving tool output (OCR JSON)
4. Returning final narration JSON with correct formatting

## Data Requirements

### Screen Type Distribution

| Screen Type | Target Count | Priority | Notes |
|-------------|--------------|----------|-------|
| Pierre's shop detail panel | 300 | High | Current MVP - need diversity in items, prices, quantities |
| Unrecognized screens | 100 | High | Train fallback behavior - main menu, inventory grid, crafting |
| TV dialog | 100 | Medium | Phase 2 target - teach new screen type |
| Inventory tooltip | 100 | Low | Phase 3 - defer until after TV dialog working |

**Total**: 600 examples minimum, 1000 examples ideal

### Screenshot Diversity Requirements

**Pierre's shop (300 examples):**
- Item variety: seeds, tools, wallpaper, fertilizer, saplings
- Price range: 10g to 10,000g
- Quantity variations: 1-999 selected
- Edge cases: out of season items, festival items, year 1 vs year 5 prices
- Resolution variety: 1920×1080, 2560×1440, 3840×2160
- UI scale: 100%, 125%, 150%

**Unrecognized screens (100 examples):**
- Main menu / title screen
- Inventory grid (9×12 slots)
- Crafting menu
- Shipping bin summary
- Collection menu
- Achievement screen
- Settings menu

**TV dialog (100 examples):**
- Weather forecast
- Fortune teller
- Queen of Sauce recipe
- Livin' Off The Land tips

## Annotation Format

### Full Conversation Structure

Each training example is a complete multi-turn conversation in OpenAI messages format:

```json
{
  "image_id": "550e8400-e29b-41d4-a716-446655440000",
  "image_path": "datasets/pierre_shop/images/IMG_7710.jpg",
  "screen_type": "pierres_shop_detail",
  "timestamp": "2026-04-13T12:00:00Z",
  "annotator": "human",
  "conversation": [
    {
      "role": "system",
      "content": "You are an accessibility assistant for Stardew Valley players with vision impairments..."
    },
    {
      "role": "user",
      "content": [
        {
          "type": "image_url",
          "image_url": {
            "url": "data:image/png;base64,<base64-encoded-image>"
          }
        },
        {
          "type": "text",
          "text": "Please extract and narrate the details from this screenshot."
        }
      ]
    },
    {
      "role": "assistant",
      "content": null,
      "tool_calls": [
        {
          "id": "call_001",
          "type": "function",
          "function": {
            "name": "crop_pierres_detail_panel",
            "arguments": "{}"
          }
        }
      ]
    },
    {
      "role": "tool",
      "tool_call_id": "call_001",
      "content": "{\"name\": \"Parsnip Seeds\", \"description\": \"Plant these in the spring. Takes 4 days to mature.\", \"price_per_unit\": 20, \"quantity_selected\": 5, \"total_cost\": 100, \"energy\": \"+0\", \"health\": \"+0\"}"
    },
    {
      "role": "assistant",
      "content": "{\"narration\": \"The item is Parsnip Seeds. The description reads: Plant these in the spring. Takes 4 days to mature. The price per unit is 20 gold. You have selected 5 items for a total cost of 100 gold.\", \"has_errors\": false}"
    }
  ]
}
```

### Unrecognized Screen Example

```json
{
  "image_id": "660e8400-e29b-41d4-a716-446655440001",
  "screen_type": "unrecognized_inventory_grid",
  "conversation": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": [...]},
    {
      "role": "assistant",
      "content": "{\"narration\": \"I have not been trained to recognize that screen. If it is important to you please let Steve know.\", \"has_errors\": false}"
    }
  ]
}
```

Note: Unrecognized screens have only 1 assistant turn (no tool call).

## Data Collection Process

### Step 1: Screenshot Capture

**Tools:**
- Game: Stardew Valley (vanilla, no mods)
- Platform: PC (Windows/Mac/Linux)
- Screenshot tool: Game's built-in (F4) or OS screenshot utility

**Instructions:**
1. Play game normally, visiting Pierre's shop regularly
2. Purchase various items (low price, high price, different quantities)
3. Take screenshot when item detail panel is visible
4. Save to `datasets/pierre_shop/raw_screenshots/YYYY-MM-DD/`
5. Repeat for TV screens, unrecognized screens

**File naming**: `IMG_<timestamp>.png` or `screenshot_<YYYY-MM-DD>_<HH-MM-SS>.png`

### Step 2: OCR Ground Truth Generation

**Run OCR on all screenshots:**
```bash
python data/scripts/evaluation/batch_ocr.py \
  --input datasets/pierre_shop/raw_screenshots/ \
  --output datasets/pierre_shop/ocr_results.jsonl
```

**Review and correct OCR output:**
- Automated OCR may have typos ("Storter Seeds" → "Starter Seeds")
- Manually correct in `ocr_results.jsonl`
- This becomes the ground truth `tool` response

### Step 3: Narration Annotation

**For each screenshot, write the ideal narration:**

```python
# Helper script: data/scripts/annotation/annotate_narration.py
# Opens screenshot + OCR JSON, asks annotator to write narration

Example narration (Pierre's shop):
"The item is Parsnip Seeds. The description reads: Plant these in the spring. 
Takes 4 days to mature. The price per unit is 20 gold. You have selected 5 
items for a total cost of 100 gold."

Guidelines:
- Natural language (not robotic)
- Read item name first
- Include description verbatim (it's important lore/gameplay info)
- State price per unit, quantity, and total cost
- Skip energy/health if both are +0 (common case)
```

### Step 4: Conversation Assembly

**Automated via script:**
```bash
python data/scripts/annotation/assemble_conversations.py \
  --screenshots datasets/pierre_shop/raw_screenshots/ \
  --ocr datasets/pierre_shop/ocr_results.jsonl \
  --narrations datasets/pierre_shop/narrations.jsonl \
  --output datasets/training/pierre_shop_conversations.jsonl
```

**Output format**: JSONL file with one conversation per line (JSON object per screenshot)

### Step 5: Quality Check

**Validation checks:**
- Image file exists and is readable
- Base64 encoding is valid
- OCR JSON has all required fields
- Narration is non-empty and sensible
- Tool call format is valid OpenAI schema
- Final assistant response is valid JSON with `{"narration": ..., "has_errors": ...}`

```bash
python data/scripts/annotation/validate_conversations.py \
  --input datasets/training/pierre_shop_conversations.jsonl \
  --report datasets/training/validation_report.txt
```

## Annotation Tools

### Manual Annotation UI (To Be Built)

**Streamlit app**: `data/scripts/annotation/annotation_ui.py`

Features:
- Display screenshot
- Show OCR result (editable)
- Text box for narration (with character count)
- Preview assembled conversation
- Save to JSONL
- Progress tracker (X of Y annotated)

**Run annotation UI:**
```bash
streamlit run data/scripts/annotation/annotation_ui.py
```

### Batch Processing Scripts

**Already exist:**
- `data/scripts/evaluation/batch_ocr.py` - Run OCR on directory of images
- `data/scripts/evaluation/eval_ocr_quality.py` - Compare OCR output to ground truth

**To be created:**
- `data/scripts/annotation/annotate_narration.py` - Terminal-based narration annotation
- `data/scripts/annotation/assemble_conversations.py` - Combine screenshot + OCR + narration → conversation
- `data/scripts/annotation/validate_conversations.py` - Check conversation format
- `data/scripts/annotation/annotation_ui.py` - Streamlit web UI for annotation

## Data Storage Structure

```
datasets/
├── pierre_shop/
│   ├── raw_screenshots/          # Original PNGs from game
│   │   ├── 2026-04-13/
│   │   ├── 2026-04-14/
│   │   └── ...
│   ├── ocr_results.jsonl         # OCR ground truth (corrected)
│   ├── narrations.jsonl          # Human-written narrations
│   └── images/                   # Curated final set (linked from training data)
├── tv_dialog/
│   ├── raw_screenshots/
│   ├── ocr_results.jsonl
│   └── narrations.jsonl
├── unrecognized/
│   ├── raw_screenshots/
│   └── annotations.jsonl         # Simple: screen type + fallback narration
└── training/
    ├── pierre_shop_conversations.jsonl      # Assembled training data
    ├── tv_dialog_conversations.jsonl
    ├── unrecognized_conversations.jsonl
    └── combined_training_data.jsonl         # All screen types merged
```

## Timeline Estimate

| Task | Time | Output |
|------|------|--------|
| Capture 300 Pierre's shop screenshots | 2-3 days | Raw screenshots |
| Run batch OCR + manual correction | 1-2 days | ocr_results.jsonl |
| Write narrations (300 examples) | 3-4 days | narrations.jsonl |
| Assemble conversations | 1 day | pierre_shop_conversations.jsonl |
| Capture + annotate 100 unrecognized | 1 day | unrecognized_conversations.jsonl |
| Capture + annotate 100 TV dialog | 2 days | tv_dialog_conversations.jsonl |
| Validation + cleanup | 1 day | validated data |
| **Total** | **11-16 days** | **500-600 training examples** |

Additional 100-200 examples for diversity: +3-5 days

## Quality Targets

**Minimum viable:**
- 300 Pierre's shop examples (high quality)
- 100 unrecognized examples
- All conversations validated

**Ideal:**
- 500 Pierre's shop examples (diverse items, prices, edge cases)
- 100 unrecognized examples
- 100 TV dialog examples
- 100 inventory tooltip examples

**Stretch goal:**
- 1000 total examples
- Multiple annotators for inter-annotator agreement
- Difficult edge cases (OCR failures, unusual items, festival-only items)

## Next Steps After Data Collection

1. **Split data**: 80% train, 10% validation, 10% test
2. **Train LoRA adapter**: Qwen2.5-VL-7B on combined_training_data.jsonl
3. **Evaluate**: Measure screen classification accuracy, tool calling accuracy, narration quality
4. **Iterate**: Add more examples for failure cases
5. **Deploy**: Upload LoRA adapter to HuggingFace, update vLLM InferenceService

## References

- [ADR-009: Agent/Tool-Calling Architecture](adr/009-agent-tool-calling-architecture.md) - System prompt and tool definitions
- [ADR-011: Agent Loop Refinements](adr/011-agent-loop-refinements.md) - JSON output format
- [data-collection-plan.md](data-collection-plan.md) - Original data collection strategy (if exists)
