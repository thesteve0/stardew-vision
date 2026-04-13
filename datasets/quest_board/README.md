# Quest Board Screen Dataset

## Overview

This dataset contains screenshots of the Help Wanted quest board outside Pierre's General Store. The board displays daily quests from villagers requesting items or reporting lost items.

## Screen Characteristics

**Visual elements:**
- Wooden quest board background
- Pinned quest note/paper
- Villager name (quest giver)
- Quest type (Item Delivery, Slay Monsters, Fishing, Gathering)
- Requested item(s) and quantity
- Reward amount (gold)
- Expiration (end of day)

**Quest Types:**
- Item Delivery ("Please bring me...")
- Slay Monsters ("I need help clearing out...")
- Fishing ("Can you catch me a...")
- Gathering ("I need [quantity] of [item]")

**Typical use case:**
Player checks the quest board and wants to hear who posted the quest, what they need, and what the reward is.

## Annotation Schema

Each screenshot is annotated with:
- `image_id`: UUID
- `image_path`: Relative path to screenshot
- `screen_type`: "quest_board"
- `quest_type`: Category (delivery, slay, fishing, gathering)
- `tool_call`: Expected extraction tool to call (TBD - may be `crop_quest_board`)
- `ocr_fields`: Expected OCR output (villager name, quest type, items, quantity, reward)
- `narration`: Expected natural language narration

## Collection Guidelines

**Screenshot criteria:**
- Capture the full quest board with visible quest
- Include all quest types
- Include variety of villagers
- Ensure all quest details are readable

**Diversity targets:**
- Item Delivery quests: 5-8 examples
- Slay Monsters quests: 2-3 examples
- Fishing quests: 2-3 examples
- Gathering quests: 2-3 examples

## Current Status

**Images collected**: 0
**Images annotated**: 0
**Quality check**: Not started
