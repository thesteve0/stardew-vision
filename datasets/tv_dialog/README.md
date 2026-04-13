# TV Dialog Screen Dataset

## Overview

This dataset contains screenshots of the TV dialog screens in the player's farmhouse, including weather forecasts, fortune teller predictions, Queen of Sauce cooking show, and Livin' Off The Land tips.

## Screen Characteristics

**Visual elements:**
- TV screen with scrolling text dialog
- Different TV shows have different visual styles
- Text appears in a dialog box at the bottom of the screen
- May include character portraits (Queen of Sauce)

**TV Show Types:**
- Weather forecast (daily)
- Fortune teller (daily)
- Queen of Sauce (Sunday and Wednesday reruns)
- Livin' Off The Land (Monday and Thursday)

**Typical use case:**
Player watches TV to check tomorrow's weather or learn a cooking recipe, wants to hear the TV dialog read aloud.

## Annotation Schema

Each screenshot is annotated with:
- `image_id`: UUID
- `image_path`: Relative path to screenshot
- `screen_type`: "tv_dialog"
- `tv_show`: Specific show type (weather, fortune, cooking, tips)
- `tool_call`: Expected extraction tool to call (TBD - may be `crop_tv_dialog`)
- `ocr_fields`: Expected OCR output (dialog text)
- `narration`: Expected natural language narration

## Collection Guidelines

**Screenshot criteria:**
- Capture the TV screen with visible dialog text
- Include all four TV show types
- Ensure text is fully visible (not mid-scroll)
- Clear screenshot without other UI overlays

**Diversity targets:**
- Weather forecast: 3-5 examples (sunny, rain, storm, snow)
- Fortune teller: 2-3 examples
- Queen of Sauce: 3-4 examples (different recipes)
- Livin' Off The Land: 2-3 examples

## Current Status

**Images collected**: 1/15 (2_tv_second.jpg - weather forecast)
**Images annotated**: 0
**Quality check**: Not started
**Priority**: #2 (user priority after pierre_shop)
