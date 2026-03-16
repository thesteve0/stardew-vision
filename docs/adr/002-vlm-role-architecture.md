# ADR-002: VLM Role Architecture — Structured Output vs. End-to-End Description

**Date**: 2026-03-03
**Status**: Accepted
**Deciders**: Project team

## Context

The end goal is for a user to receive an **audio description** of their Stardew Valley loot box. There are two fundamentally different ways the VLM can fit into that pipeline:

**Option A — Structured Output**: Fine-tune the VLM to output a JSON object listing each cell's contents (item name, quantity). A separate Python template converts this JSON into natural language, which is passed to TTS.

**Option B — End-to-End Description**: Fine-tune the VLM to directly output a complete natural language description of the loot box ("In your treasure chest you have: Copper Bar times 5 in the top left, an Ancient Sword in the top right..."). This text goes directly to TTS.

The decision affects: annotation cost, evaluation approach, debugging ability, and the pedagogical story for the talk.

## Decision

**Option A — Structured Output (JSON per cell → template → TTS)**

The VLM outputs:
```json
{
  "cells": [
    {"row": 0, "col": 0, "item": "Copper Bar", "quantity": 5},
    {"row": 0, "col": 1, "item": "Ancient Sword", "quantity": 1},
    {"row": 0, "col": 2, "item": "empty"}
  ]
}
```

A Python template function converts this to a narration string, which Kokoro TTS synthesizes to audio.

## Alternatives Considered

| Option | Why not selected for MVP |
|--------|-------------------------|
| **Option B: End-to-end instruct VLM** | Annotation is more expensive (must write natural language descriptions, not just item labels); evaluation requires LLM-judge or human raters; harder to debug (if the description is wrong, is it the VLM or the narration style?); post-MVP stretch goal |
| **Option C: VLM as classifier only + separate LLM for dialog** | Requires two model inference calls per request, adds latency; the "large LLM for dialog" is unnecessary for the MVP use case (no dialog — just one description per screenshot) |

## Consequences

**Gets easier**:
- Annotation: label each cell with an item name (bounded ~600-item vocabulary) vs. writing natural language descriptions
- Evaluation: exact match and fuzzy match on item names vs. LLM-judge or human evaluation
- Debugging: can inspect the JSON intermediate to see exactly where errors occur (wrong item? wrong cell? missing cell?)
- The JSON intermediate is a great teaching artifact in the talk — audience can see what the VLM "knows"
- Narration style can be improved without retraining (just edit the template)

**Gets harder**:
- The template-generated narration may sound robotic; if naturalness is required, must add an LLM paraphrase step (post-MVP)
- SmolVLM2's known weakness with complex JSON schemas means we must keep the schema flat (no deep nesting)

**We are committing to**:
- A flat JSON schema that both Qwen2.5-VL and SmolVLM2 can reliably produce
- Writing a JSON schema validator (`configs/output_schema.json`) and treating invalid JSON as evaluation failures
- The narration template being the primary "voice" of the application at MVP; improving it later without retraining

## Post-MVP Path

Option B remains a valuable stretch goal: once the dataset is annotated (item names + quantities), generating natural language training targets is straightforward. Running both Options A and B in the talk is a strong comparative story: "here's the explicit pipeline vs. the end-to-end approach."
