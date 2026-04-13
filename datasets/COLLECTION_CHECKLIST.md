# Screenshot Collection Checklist

**Phase 2 Priority**: tv_dialog (15-20) + caught_fish (15-20)  
**See full plan**: `docs/phase2-collection-plan.md`

---

## Quick Start

### 1. Take Screenshots in Game

**tv_dialog** (farmhouse TV):
- ☐ Weather forecast (3-5) — different weather types
- ☐ Fortune teller (3-5)
- ☐ Queen of Sauce (3-5) — different recipes
- ☐ Livin' Off The Land (3-5)

**caught_fish** (fishing anywhere):
- ☐ Common fish (8-10) — ocean, river, lake
- ☐ Rare fish (3-5)
- ☐ Different qualities (normal, silver, gold, iridium)

### 2. Organize Each Screenshot

```bash
# Example: TV weather forecast
python data/scripts/annotation/organize_screenshot.py \
  /path/to/screenshot.jpg \
  --screen-type tv_dialog \
  --name tv_weather_01

# Example: Caught fish
python data/scripts/annotation/organize_screenshot.py \
  /path/to/screenshot.jpg \
  --screen-type caught_fish \
  --name fish_anchovy_01
```

This automatically:
- Copies to `datasets/{screen_type}/images/`
- Generates UUID
- Creates stub annotation entry
- Updates annotations.jsonl

### 3. Track Progress

Update `docs/phase2-collection-plan.md` collection progress section.

---

## Current Status

### tv_dialog: 1/15
- [x] weather_forecast (1) — 2_tv_second.jpg
- [ ] fortune_teller (0)
- [ ] cooking_show (0)
- [ ] tips_show (0)

### caught_fish: 1/15
- [x] unknown_species (1) — which_fish.jpg (23 in., needs sprite ID)
- [ ] common_fish (0)
- [ ] rare_fish (0)
- [ ] quality_variety (0)

---

## After Collection Complete

1. Build extraction tools (`crop_tv_dialog`, `crop_caught_fish_notification`)
2. Test tools on all collected screenshots
3. Manually verify OCR output
4. Complete annotations.jsonl entries
5. Generate synthetic training data
6. Fine-tune Qwen

---

## Helper Commands

**List collected screenshots**:
```bash
ls -lh datasets/tv_dialog/images/
ls -lh datasets/caught_fish/images/
```

**Count annotations**:
```bash
wc -l datasets/tv_dialog/annotations.jsonl
wc -l datasets/caught_fish/annotations.jsonl
```

**View latest annotation**:
```bash
tail -n 1 datasets/tv_dialog/annotations.jsonl | jq .
```
