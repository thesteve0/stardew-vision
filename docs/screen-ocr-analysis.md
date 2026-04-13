# Screen OCR Analysis and Tool Development Plan

**Date**: 2026-04-12  
**Purpose**: Analyze example screenshots to determine OCR extraction requirements and prioritize tool development.

## Fish Sprite Identification Strategy

**Problem**: User's enlarged UI crops fish names from caught fish notifications.

**Solution**: Template matching against sprite library.

**Implementation**:
1. Crop fish sprite from wooden frame region in screenshot
2. Use OpenCV template matching against `datasets/assets/sprites/sprite_*.png`
3. Find best match by sprite_index
4. Look up fish name in `datasets/assets/item_manifest.json` using sprite_index
5. Example: sprite_128.png → "Pufferfish", sprite_138.png → "Rainbow Trout"

**Technical notes**:
- item_manifest.json maps all fish with `"type": "Fish"` and `sprite_index` field
- Sprites are 16×16 pixel art icons (may need scaling tolerance for enlarged UI)
- Fish category in manifest: `"category": -4`

---

## Screen Analysis by OCR Difficulty

### 1. Level Up (EASIEST)

**Screenshot**: `datasets/level_up/images/level_up_choice.jpg`

**Visual characteristics**:
- Excellent contrast: dark brown text on tan/peach background
- Clean layout with clear regions
- Black background isolates UI panel
- Large, readable font

**Template matching anchor**:
- "Level Up" header in stylized gold/orange font at top
- Wooden panel border (unique shape)
- Skill icons (left and right of header)

**OCR extraction fields**:
```json
{
  "screen_type": "level_up",
  "skill": "Farming",
  "level": 5,
  "profession_choice": true,
  "profession_1": {
    "name": "Rancher",
    "description": "Animal products worth 20% more."
  },
  "profession_2": {
    "name": "Tiller",
    "description": "Crops worth 10% more."
  }
}
```

**Crop regions**:
1. Header: "Level 5 Farming"
2. Subheader: "Choose a profession:"
3. Left panel: profession name + description
4. Right panel: profession name + description

**Expected narration**:
> "You've reached Level 5 Farming! Choose a profession: Rancher - Animal products worth 20% more, or Tiller - Crops worth 10% more."

**Difficulty**: ★☆☆☆☆ (1/5)

---

### 2. Quest Board (EASY)

**Screenshot**: `datasets/quest_board/images/help_wanted_board.jpg`

**Visual characteristics**:
- Good contrast: black text on white/cream paper
- Wooden board background (distinctive)
- Quest note pinned to board
- Clear text layout

**Template matching anchor**:
- Wooden board texture
- "Help Wanted" header at top
- Star/pin icons holding paper
- "Accept Quest" button at bottom

**OCR extraction fields**:
```json
{
  "screen_type": "quest_board",
  "quest_type": "slay_monsters",
  "quest_giver": "Demetrius",
  "quest_description": "An invasive crab species is living in the local mine, threatening the native wildlife! These creatures are known for disguising themselves as stones. I'll pay someone to slay 2 of them.",
  "target_monster": "crab",
  "quantity": 2,
  "reward": "150g"
}
```

**Crop regions**:
1. Quest paper region (white note)
2. Quest text (full body)
3. Signature line ("-Demetrius")
4. Reward line ("- 150g reward.")

**Expected narration**:
> "Help Wanted quest from Demetrius: Slay 2 crabs in the local mine. Reward: 150 gold."

**Difficulty**: ★★☆☆☆ (2/5)

---

### 3. TV Dialog (MEDIUM)

**Screenshot**: `datasets/tv_dialog/images/2_tv_second.jpg`

**Visual characteristics**:
- Good contrast: dark text on tan dialog box
- Generic dialog box (used for many interactions)
- TV visible in background
- Standard dialog UI

**Template matching anchor**:
- TV sprite in background (CRT TV with green screen)
- Dialog box shape (rounded rectangle at bottom)
- Next arrow icon (bottom right of dialog)
- Challenge: Generic dialog box used throughout game

**Screen recognition challenge**:
- Dialog box appears for NPCs, shops, TV, events, etc.
- Must detect TV context from surrounding elements:
  - TV sprite visible in frame
  - Farmhouse interior background
  - No NPC portrait
  - KOZU 5 or other TV show identifier in text

**OCR extraction fields**:
```json
{
  "screen_type": "tv_dialog",
  "tv_show": "weather_forecast",
  "channel": "KOZU 5",
  "dialog_text": "Welcome to KOZU 5... your number one source for weather, news, and entertainment. And now, the weather forecast for tomorrow..."
}
```

**Crop regions**:
1. Dialog box region (bottom third of screen)
2. Full dialog text

**Expected narration**:
> "TV weather forecast: Welcome to KOZU 5, your number one source for weather, news, and entertainment. And now, the weather forecast for tomorrow..."

**Difficulty**: ★★★☆☆ (3/5) — screen recognition is the challenge, not OCR itself

---

### 4. Caught Fish (MEDIUM-HARD)

**Screenshot**: `datasets/caught_fish/images/which_fish.jpg`

**Visual characteristics**:
- Clean white background in notification
- Fish name is CROPPED (not visible due to enlarged UI)
- Length text visible: "Length: 23 in."
- Fish sprite visible in wooden frame
- Minimal text to OCR

**Template matching anchor**:
- Wooden frame around fish sprite
- White notification box
- "Length:" label
- Challenge: Fish name requires sprite matching, not OCR

**OCR + Sprite Matching extraction**:
```json
{
  "screen_type": "caught_fish",
  "fish_name": "Rainbow Trout",
  "fish_sprite_index": 138,
  "length": "23 in.",
  "quality": "normal",
  "identification_method": "sprite_match"
}
```

**Processing steps**:
1. Crop wooden frame region containing fish sprite
2. Extract fish sprite (16×16 pixel art, may need scaling)
3. Template match against `datasets/assets/sprites/sprite_*.png`
4. Find best match (use normalized cross-correlation)
5. Look up sprite_index in item_manifest.json
6. Filter by `"type": "Fish"` and `"category": -4`
7. Return fish name
8. OCR "Length: 23 in." text

**Expected narration**:
> "You caught a Rainbow Trout, 23 inches long!"

**Difficulty**: ★★★★☆ (4/5) — sprite matching adds complexity; OCR is trivial

**Tool name**: `crop_caught_fish_notification()`

---

### 5. Game Letter (HARDEST)

**Screenshot**: `datasets/game_letter/images/in_game_letter.jpg`

**Visual characteristics**:
- POOR CONTRAST: brown text on tan/cream background
- Letter paper texture
- Multi-paragraph text
- Sender addressed as "To Mr. Pierre:"
- Signature at end

**Template matching anchor**:
- Letter background texture (cream/tan with slight texture)
- Letter borders (decorative top/bottom edges)
- Next arrow icon (bottom right)

**OCR extraction fields**:
```json
{
  "screen_type": "game_letter",
  "letter_type": "npc",
  "recipient": "Mr. Pierre",
  "sender": "Morris",
  "letter_body": "It pains me to be the bearer of bad news, but I feel obligated to inform you of a recent development most threatening to your livelihood. Joja Co. has decided to expand into Pelican Town. It's too late for protest. Joja Builders have already broken ground for the new JojaMart."
}
```

**Crop regions**:
1. Letter region (full letter background)
2. Recipient line ("To Mr. Pierre:")
3. Letter body (multiple paragraphs)
4. Signature (if visible)

**Expected narration**:
> "Letter to Mr. Pierre: It pains me to be the bearer of bad news, but I feel obligated to inform you of a recent development most threatening to your livelihood. Joja Co. has decided to expand into Pelican Town. It's too late for protest. Joja Builders have already broken ground for the new JojaMart."

**OCR challenges**:
- Low contrast between text and background
- May need preprocessing: increase contrast, adaptive thresholding
- PaddleOCR may struggle without preprocessing
- Consider converting to grayscale, then binary with adaptive threshold

**Difficulty**: ★★★★★ (5/5) — poor contrast requires preprocessing

---

## Tool Development Priority

Based on OCR difficulty, template matching feasibility, and user value:

### Phase 1 (Immediate — Week 1)
1. **crop_level_up_notification()** — Easiest OCR, high user value
2. **crop_quest_board()** — Easy OCR, clear template anchor

### Phase 2 (Week 2)
3. **crop_tv_dialog()** — Medium OCR, screen recognition challenge
4. **crop_caught_fish_notification()** — Sprite matching + simple OCR

### Phase 3 (Week 3)
5. **crop_game_letter()** — Hardest OCR, needs preprocessing

---

## Common Extraction Tool Patterns

All tools follow this structure (based on `crop_pierres_detail_panel`):

```python
def crop_screen_region(image_b64: str, debug: bool = False) -> dict:
    """
    Extract text from [screen type] using template matching + OCR.
    
    Args:
        image_b64: Base64-encoded PNG screenshot
        debug: If True, include raw OCR output and intermediate images
        
    Returns:
        {
            "success": bool,
            "screen_type": str,
            "fields": {...},
            "ocr_raw": [...] if debug else None,
            "debug_images": {...} if debug else None
        }
    """
    # 1. Decode base64 → numpy array
    # 2. Template matching to locate region
    # 3. Crop region
    # 4. OCR with PaddleOCR
    # 5. Parse OCR results into structured fields
    # 6. Return JSON
```

**Template storage**: `datasets/assets/templates/{screen_type}/`
- Example: `datasets/assets/templates/level_up/header.png` (anchor for "Level Up" header)

**OCR preprocessing** (for low-contrast screens like game_letter):
```python
import cv2

# Convert to grayscale
gray = cv2.cvtColor(cropped_region, cv2.COLOR_BGR2GRAY)

# Increase contrast
alpha = 1.5  # Contrast control (1.0-3.0)
beta = 10    # Brightness control (0-100)
adjusted = cv2.convertScaleAbs(gray, alpha=alpha, beta=beta)

# Adaptive thresholding for text extraction
binary = cv2.adaptiveThreshold(
    adjusted, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
    cv2.THRESH_BINARY, 11, 2
)

# Pass binary image to PaddleOCR
```

---

## Sprite Matching Implementation (Caught Fish)

**Function**: `match_fish_sprite(fish_sprite_crop: np.ndarray) -> dict`

**Algorithm**:
1. Load all fish sprites from `datasets/assets/sprites/`
2. Filter item_manifest.json for `"type": "Fish"`
3. For each fish sprite:
   - Resize template to match screenshot scaling (if needed)
   - Compute normalized cross-correlation with cropped fish sprite
   - Track best match score
4. Return fish with highest match score (threshold: 0.8+)

**Returns**:
```json
{
  "fish_name": "Rainbow Trout",
  "sprite_index": 138,
  "match_score": 0.92,
  "sprite_file": "datasets/assets/sprites/sprite_138.png"
}
```

**Error handling**:
- If no match above 0.8 threshold: return `"fish_name": "Unknown Fish"` with warning
- Log match scores for debugging

---

## Fine-Tuning Artifacts (Phase 2)

Once extraction tools are built, create these artifacts for fine-tuning:

1. **tool_definitions.json** — OpenAI function calling schema for each screen type
2. **narration_templates.json** — Natural language templates for TTS output
3. **conversations_real.jsonl** — ChatML conversations from real screenshots
4. **conversations_synthetic.jsonl** — LLM-generated variations
5. **lora_config.yaml** — LoRA fine-tuning hyperparameters
6. **eval_metrics.yaml** — Evaluation rubric (tool selection accuracy, field extraction F1, narration quality)

Detailed artifact specs will be documented after extraction tools are validated.

---

## Next Steps

1. **Create template anchors**: Capture PNG templates for each screen type's unique UI element
2. **Build extraction tools**: Start with level_up (easiest) to validate pattern
3. **Test OCR accuracy**: Run PaddleOCR on each screen, measure field extraction success rate
4. **Document sprite matching**: Implement and test fish sprite identification
5. **Validate on 15-20 real examples**: Collect screenshots and annotate ground truth
6. **Generate synthetic data**: Use LLM to create variations for fine-tuning dataset expansion

---

## Tool Call Naming Convention

Following OpenAI function calling format:

```json
{
  "name": "crop_level_up_notification",
  "description": "Extract skill name, level, and profession choices from a level-up notification screen",
  "parameters": {
    "type": "object",
    "properties": {
      "image_b64": {"type": "string", "description": "Base64-encoded PNG screenshot"},
      "debug": {"type": "boolean", "description": "Include raw OCR output", "default": false}
    },
    "required": ["image_b64"]
  }
}
```

Tool names:
- `crop_level_up_notification`
- `crop_quest_board`
- `crop_tv_dialog`
- `crop_caught_fish_notification`
- `crop_game_letter`
- `crop_pierres_detail_panel` (existing)
