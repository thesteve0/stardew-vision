# Caught Fish Screen Dataset

## Overview

This dataset contains screenshots of the "fish caught" notification screen that appears immediately after successfully catching a fish in Stardew Valley.

## Screen Characteristics

**Visual elements:**
- Fish sprite/icon
- Fish name
- Fish description
- Size/length measurement
- Quality indicator (normal, silver star, gold star, iridium star)

**Typical use case:**
Player catches a fish and wants to hear what fish they caught, its quality, and its description.

## Annotation Schema

Each screenshot is annotated with:
- `image_id`: UUID
- `image_path`: Relative path to screenshot
- `screen_type`: "caught_fish"
- `tool_call`: Expected extraction tool to call (TBD - may be `crop_fish_notification`)
- `ocr_fields`: Expected OCR output (fish name, description, size, quality)
- `narration`: Expected natural language narration

## Collection Guidelines

**Screenshot criteria:**
- Capture the full fish caught notification screen
- Include variety of fish species (ocean, river, lake, night, seasonal)
- Include all quality levels (normal, silver, gold, iridium)
- Include legendary fish if possible
- Avoid partial UI overlays

**Diversity targets:**
- Common fish (10 examples)
- Rare fish (5 examples)
- Legendary fish (2-3 examples)
- Quality variations (normal, silver, gold, iridium)

## Current Status

**Images collected**: 1/15 (which_fish.jpg - species unknown, 23 in., needs sprite matching)
**Images annotated**: 0
**Quality check**: Not started
**Priority**: #3 (sprite matching challenge)

## Special Note

User's enlarged UI crops fish names from the notification. Fish identification will use sprite matching against `datasets/assets/sprites/` instead of OCR for the name field.
