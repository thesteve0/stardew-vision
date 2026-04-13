# Phase 2 Screenshot Collection Plan

**Date**: 2026-04-13  
**Priority Screen Types**: tv_dialog, caught_fish  
**Target**: 15-20 screenshots per type  
**Timeline**: Collect before building extraction tools

---

## tv_dialog Collection (Priority 1)

**Target**: 15-20 screenshots  
**Location**: Player's farmhouse, interact with TV

### Diversity Requirements

**TV Show Types** (aim for 3-5 of each):
- ☐ Weather forecast (KOZU 5) — sunny, rainy, stormy, snowy
- ☐ Fortune teller (daily predictions)
- ☐ Queen of Sauce (Sunday + Wednesday reruns) — different recipes
- ☐ Livin' Off The Land (Monday + Thursday) — farming tips

**What to Capture**:
- Full game screen showing:
  - TV sprite in background
  - Dialog box with text visible
  - No other UI overlays (pause menu, inventory, etc.)
- Text must be fully visible (not mid-scroll)
- Clear screenshot without blur

**Screenshot Naming Convention**:
```
datasets/tv_dialog/images/tv_weather_01.jpg
datasets/tv_dialog/images/tv_weather_02.jpg
datasets/tv_dialog/images/tv_fortune_01.jpg
datasets/tv_dialog/images/tv_cooking_01.jpg
datasets/tv_dialog/images/tv_tips_01.jpg
```

**Collection Tips**:
- Watch TV daily in-game for different shows
- Sunday = Queen of Sauce new recipe
- Wednesday = Queen of Sauce rerun
- Monday/Thursday = Livin' Off The Land
- Every day = Weather + Fortune available
- Take screenshot when full dialog appears (before clicking through)

**Current Status**: 1/15 collected (2_tv_second.jpg - weather forecast)

---

## caught_fish Collection (Priority 2)

**Target**: 15-20 screenshots  
**Location**: Fishing anywhere (ocean, river, lake, mine)

### Diversity Requirements

**Fish Variety** (different species for sprite matching validation):
- ☐ Common ocean fish: Anchovy, Sardine, Tuna
- ☐ Common river fish: Smallmouth Bass, Rainbow Trout, Catfish
- ☐ Lake fish: Largemouth Bass, Carp
- ☐ Rare/legendary fish: Pufferfish, Sturgeon, Legend
- ☐ Different seasons (seasonal fish change)

**Quality Variety**:
- ☐ Normal quality (no star)
- ☐ Silver star
- ☐ Gold star
- ☐ Iridium star

**What to Capture**:
- Fish caught notification popup showing:
  - Wooden frame with fish sprite visible
  - "Length: X in." text
  - Full notification (fish name will be cropped due to enlarged UI — that's OK!)
- Clean screenshot without other overlays

**Screenshot Naming Convention**:
```
datasets/caught_fish/images/fish_anchovy_01.jpg
datasets/caught_fish/images/fish_trout_01.jpg
datasets/caught_fish/images/fish_bass_silver_01.jpg
datasets/caught_fish/images/fish_pufferfish_gold_01.jpg
```

**Collection Tips**:
- Fish in different locations for variety
- Screenshot immediately when "You caught..." notification appears
- Don't worry that fish name is cropped — that's expected
- Try to get different quality levels (fishing skill + tackle affects this)
- Include at least one legendary/rare fish if possible

**Current Status**: 1/15 collected (which_fish.jpg - unknown species, 23 in.)

---

## Annotation Workflow (Once Screenshots Collected)

### For Each Screenshot

1. **Copy to images/ directory** with naming convention
2. **Run extraction tool** (once built) to get OCR output
3. **Manually verify** OCR fields are correct
4. **Write ground truth annotation** to annotations.jsonl:

```jsonl
{"image_id": "uuid", "image_path": "images/tv_weather_01.jpg", "screen_type": "tv_dialog", "tv_show": "weather_forecast", "dialog_text": "Welcome to KOZU 5...", "narration": "TV weather forecast: ...", "timestamp": "2026-04-13T..."}
```

5. **Add to quality report**: Track OCR accuracy, template matching success rate

### Annotation Format (Standard Across All Screen Types)

```json
{
  "image_id": "550e8400-e29b-41d4-a716-446655440000",
  "image_path": "images/tv_weather_01.jpg",
  "screen_type": "tv_dialog",
  "timestamp": "2026-04-13T10:30:00Z",
  
  "ocr_fields": {
    "tv_show": "weather_forecast",
    "channel": "KOZU 5",
    "dialog_text": "Welcome to KOZU 5... your number one source for weather, news, and entertainment. And now, the weather forecast for tomorrow..."
  },
  
  "narration": "TV weather forecast: Welcome to KOZU 5, your number one source for weather, news, and entertainment. And now, the weather forecast for tomorrow...",
  
  "tool_call": "crop_tv_dialog",
  
  "metadata": {
    "game_season": "Spring",
    "game_year": 1,
    "ui_scale": "enlarged"
  }
}
```

---

## Quality Targets

### tv_dialog
- ☐ 15-20 total screenshots
- ☐ All 4 TV show types represented (3-5 each)
- ☐ All text fully visible (not mid-scroll)
- ☐ Clear template anchor (TV sprite visible in background)

### caught_fish
- ☐ 15-20 total screenshots
- ☐ At least 10 different fish species (for sprite matching variety)
- ☐ Multiple quality levels (normal, silver, gold, iridium)
- ☐ Fish sprite clearly visible in wooden frame
- ☐ Length text readable

---

## Helper Script: Screenshot Organizer

**Purpose**: Rename and organize screenshots as they're collected

**Usage**:
```bash
# Copy screenshot to appropriate directory
python data/scripts/annotation/organize_screenshot.py \
  /path/to/screenshot.jpg \
  --screen-type tv_dialog \
  --name tv_weather_01

# Auto-generates UUID, moves to datasets/tv_dialog/images/
# Creates stub annotation entry in annotations.jsonl
```

**Status**: To be created after collection starts

---

## Post-Collection Next Steps

Once 15-20 screenshots collected for tv_dialog + caught_fish:

1. **Build extraction tools**:
   - `crop_tv_dialog()` — test on real examples
   - `crop_caught_fish_notification()` — validate sprite matching

2. **Annotate ground truth**:
   - Run tools on all screenshots
   - Manually verify OCR output
   - Write annotations.jsonl entries

3. **Generate synthetic data**:
   - Use real annotations as templates
   - LLM generates variations (different fish, different weather, etc.)
   - Create full ChatML conversations

4. **Create training artifacts**:
   - tool_definitions.json
   - narration_templates.json
   - conversations_train.jsonl (real + synthetic)

5. **Fine-tune Qwen**:
   - LoRA training on pierre_shop + tv_dialog + caught_fish
   - ~450 total training examples

---

## Collection Progress Tracking

Update this section as screenshots are collected:

### tv_dialog: 1/15 ☐
- [x] Weather forecast (1)
- [ ] Fortune teller (0)
- [ ] Queen of Sauce (0)
- [ ] Livin' Off The Land (0)

### caught_fish: 1/15 ☐
- [x] Unknown species (1) — needs sprite matching to identify
- [ ] Common ocean fish (0)
- [ ] Common river fish (0)
- [ ] Rare/legendary fish (0)
- [ ] Quality variety (0 silver, 0 gold, 0 iridium)

---

## Notes

- User has enlarged UI scale — fish names will be cropped (expected behavior)
- TV dialog uses generic dialog box — extraction tool must detect TV context from surrounding elements
- Sprite matching for caught_fish is novel challenge — needs robust template matching algorithm
- All screenshots should be 1600×1200 or similar resolution (consistent with existing pierre_shop examples)
