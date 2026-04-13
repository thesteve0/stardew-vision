# Level Up Screen Dataset

## Overview

This dataset contains screenshots of the skill level-up notification screen that appears when the player gains a level in one of the five skills (Farming, Mining, Foraging, Fishing, Combat).

## Screen Characteristics

**Visual elements:**
- Skill name (Farming, Mining, Foraging, Fishing, Combat)
- New level number (1-10)
- Profession choice dialog (at levels 5 and 10)
- Skill description text
- Background image specific to the skill

**Typical use case:**
Player levels up a skill and wants to hear which skill leveled up, what new level they reached, and what profession choices are available (if applicable).

## Annotation Schema

Each screenshot is annotated with:
- `image_id`: UUID
- `image_path`: Relative path to screenshot
- `screen_type`: "level_up"
- `tool_call`: Expected extraction tool to call (TBD - may be `crop_level_up_notification`)
- `ocr_fields`: Expected OCR output (skill name, level, profession choices if present)
- `narration`: Expected natural language narration

## Collection Guidelines

**Screenshot criteria:**
- Capture the full level-up notification screen
- Include all 5 skills
- Include both simple level-ups (1-4, 6-9) and profession choice screens (5, 10)
- Clear text, no overlapping UI elements

**Diversity targets:**
- Each skill: 2-3 examples
- Profession choice screens: 3-4 examples (levels 5 and 10)
- Simple level-ups: 12-15 examples

## Current Status

**Images collected**: 0
**Images annotated**: 0
**Quality check**: Not started
