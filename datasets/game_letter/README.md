# Game Letter Screen Dataset

## Overview

This dataset contains screenshots of in-game letters that arrive in the player's mailbox. Letters can be from NPCs, the mayor, Joja Corp, or system notifications about quests, events, and achievements.

## Screen Characteristics

**Visual elements:**
- Letter background (paper texture)
- Sender name/signature
- Letter body text (may be multiple paragraphs)
- Attached items or money (sometimes)
- Quest notifications
- Event invitations

**Letter Types:**
- NPC letters (friendship, gifts, requests)
- Mayor Lewis (community announcements, events)
- Joja Corp (advertisements, membership)
- Quest letters (special orders, Help Wanted)
- Achievement letters (community center completion, etc.)

**Typical use case:**
Player receives a letter in mailbox and wants to hear who it's from and what it says.

## Annotation Schema

Each screenshot is annotated with:
- `image_id`: UUID
- `image_path`: Relative path to screenshot
- `screen_type`: "game_letter"
- `letter_type`: Category (npc, mayor, joja, quest, achievement)
- `tool_call`: Expected extraction tool to call (TBD - may be `crop_letter_text`)
- `ocr_fields`: Expected OCR output (sender, letter text, attached items)
- `narration`: Expected natural language narration

## Collection Guidelines

**Screenshot criteria:**
- Capture the full letter screen
- Include variety of senders and letter types
- Ensure all text is visible
- Include letters with and without attached items

**Diversity targets:**
- NPC letters: 5-8 examples (different NPCs)
- Mayor letters: 2-3 examples
- Quest letters: 2-3 examples
- Letters with attachments: 2-3 examples

## Current Status

**Images collected**: 0
**Images annotated**: 0
**Quality check**: Not started
