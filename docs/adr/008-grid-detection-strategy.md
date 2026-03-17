# ADR-008: Grid Detection Strategy for Dual-Grid Screenshots

**Date**: 2026-03-05
**Status**: Deferred (2026-03-17)
**Deciders**: Project team

> **Note**: Full-page grid detection is not needed for the targeted panel extraction approach. Revisit if inventory grid reading becomes a priority screen type.

## Context

The current architecture assumes VLMs receive clean, cropped loot box screenshots. However, new requirements reveal critical gaps in handling real-world user submissions:

### Reality of Stardew Valley UI

1. **Dual-grid layout**: When users open a chest, the screenshot contains:
   - **Upper grid**: Chest/container contents (3 rows × 12 columns = 36 slots, or 3×24 = 72 slots for large chests)
   - **Lower grid**: Player inventory (always visible in the UI)

2. **Spatial variability**: The VLM must handle:
   - iPad Retina displays (2048×2732 @ 4:3 aspect)
   - Linux/Windows varying resolutions (1080p, 1440p, 4K @ 16:9)
   - User-configurable UI scale percentage (75%-150% in game settings)
   - Different screen zoom levels across platforms (Switch vs. PC vs. tablet)

3. **Hardcoded coordinates fail**: Cannot rely on fixed pixel positions for grid boundaries because:
   - Resolution varies dramatically across platforms
   - UI scale setting shifts all UI elements proportionally
   - Game updates/mods may adjust layout

### The Problem

If the VLM receives a full screenshot showing **both** the chest grid and inventory grid, it must:
1. Identify which grid is the chest vs. the inventory
2. Locate the geometric boundaries of the chest grid
3. Extract cell contents from the chest grid **only**
4. Ignore the inventory grid entirely

Overlay detection (ADR-007) assumed the VLM receives a clean grid image. But if users submit uncropped dual-grid screenshots, the VLM's task becomes significantly harder — it must perform spatial reasoning to isolate the correct grid before analyzing contents.

### Why This Matters for Accessibility

Users should not be required to crop screenshots before submission:
- Cropping requires precise motor control and vision
- Many accessibility tools/workflows (Switch screenshot sharing, iOS screenshot shortcuts) don't support easy cropping
- Better UX: "just screenshot and upload" vs. "screenshot, open editor, crop precisely, then upload"

## Decision

**Use VLM-First Grid Detection (Option A)**: The VLM receives full-UI screenshots and is prompted to analyze only the upper chest grid.

### Approach

1. **User workflow**: Accept full screenshots (dual-grid or cropped)
2. **VLM system prompt**: Explicitly instruct the model to:
   - Identify the upper grid (chest contents) vs. lower grid (player inventory)
   - Analyze only the chest grid
   - Ignore the inventory grid entirely
3. **No preprocessing**: No OpenCV-based grid detection or cropping pipeline
4. **Supported grid sizes**: 3×12 (standard chest, 36 slots) and 3×24 (large chest, 72 slots)

### VLM System Prompt Strategy

The VLM system prompt must include spatial isolation instructions:

```
You are analyzing a Stardew Valley screenshot showing loot containers.

CRITICAL: If the screenshot shows BOTH a chest/container grid AND a player inventory grid:
- Analyze ONLY the UPPER grid (chest/container contents)
- IGNORE the lower grid (player inventory)
- The chest grid is typically 3 rows × 12 columns (36 slots) or 3 rows × 24 columns (72 slots)

For each cell in the UPPER CHEST GRID:
1. Identify the item name (ignore overlays obscuring the sprite)
2. Report the stack count (white number in bottom-right; default to 1 if none)
3. Report the quality (star in bottom-left: no star = "normal", silver/gold/iridium star = that quality)

Output valid JSON matching this schema:
{
  "cells": [
    {"row": 0, "col": 0, "item": "Copper Bar", "quantity": 5, "quality": "silver"},
    {"row": 0, "col": 1, "item": "empty", "quantity": 0, "quality": null}
  ]
}

Cells are indexed from top-left (row 0, col 0) to bottom-right.
Empty cells MUST be included with item="empty".
```

**Key prompting techniques**:
- Use "CRITICAL" emphasis for grid isolation
- Provide explicit grid size hints (3×12, 3×24)
- Use spatial language ("UPPER grid", "lower grid")
- Reiterate empty cell handling

## Alternatives Considered

### Option B: Preprocessing-First Approach

Use OpenCV/traditional CV to detect and crop the chest grid before sending to the VLM.

**Steps**:
1. Color-based region detection (chest UI frame is distinct brown/wood color)
2. Contour detection to find rectangular chest grid boundary
3. Crop to chest grid only
4. Send cropped image to VLM (same as current workflow)

**Why not selected**:
- **Brittle to UI changes**: Game updates, mods, or theme changes break color/contour assumptions
- **Resolution-dependent**: Requires tuning thresholds for each platform/resolution
- **More complex**: Adds entire preprocessing pipeline to maintain
- **Debugging harder**: Failures can occur in CV stage OR VLM stage
- **User experience**: If preprocessing fails, user must manually crop (defeats accessibility goal)

### Option C: User-Required Cropping

Require users to crop screenshots to chest-only before submission.

**Why not selected**:
- **Poor accessibility**: Cropping requires motor control and vision that impaired users may lack
- **Higher friction**: Reduces likelihood of community submissions for training data
- **Platform limitations**: Switch/mobile screenshot workflows don't support easy cropping

## Why VLM-First Works

1. **Qwen2.5-VL is trained on UI understanding**: Specifically trained on screenshot/document tasks involving spatial reasoning
2. **Dynamic resolution support**: Qwen2.5-VL processes images at native resolution (not fixed-size compression), preserving spatial detail
3. **Spatial reasoning is a core VLM capability**: Identifying regions in images is exactly what VLMs excel at
4. **Robust to variation**: VLM handles resolution/scale/aspect ratio differences naturally (unlike hardcoded CV rules)
5. **Simpler architecture**: Single inference call vs. CV preprocessing + inference
6. **Better user experience**: No cropping required

## Testable Hypotheses

This decision creates testable hypotheses for the conference talk:

1. **Qwen2.5-VL (7B, dynamic resolution)**: Should achieve ≥95% grid detection accuracy due to superior spatial reasoning
2. **SmolVLM2 (2.2B, 81-token compression)**: May struggle with grid detection (<80% accuracy) because:
   - Aggressive image compression loses spatial layout details
   - Smaller model has weaker spatial reasoning capabilities
   - 81 tokens may not preserve enough information to distinguish chest from inventory

**⚠️ IMPORTANT**: If SmolVLM2 performs poorly, this is VALUABLE talk content, not a failure. It demonstrates that small VLMs are insufficient for complex UI understanding tasks.

## Consequences

### Gets Easier

- **User experience**: "Just screenshot and upload" — no cropping required
- **Simpler architecture**: No preprocessing pipeline to build/maintain/debug
- **Robust to variation**: VLM handles resolution/scale/platform differences naturally
- **Leverages VLM strengths**: Uses Qwen2.5-VL's UI understanding training directly

### Gets Harder

- **VLM task complexity**: VLM must handle grid detection AND item recognition (two tasks in one)
- **Prompt engineering**: Requires careful prompting to ensure grid isolation
- **SmolVLM2 may fail**: Smaller model may not handle dual-grid scenarios (but this is expected and valuable for the talk)
- **Data requirements**: Must generate synthetic dual-grid screenshots for training/testing
- **Evaluation complexity**: Must track grid detection accuracy as a separate metric

### Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Qwen2.5-VL also fails at grid detection (<95%) | Low | High (architecture invalid) | If Qwen fails, fall back to Option B (preprocessing); re-evaluate VLM-first approach |
| SmolVLM2 fails at grid detection (<80%) | Medium | **Low** (valuable talk content) | Document performance gap; use as narrative: "small VLMs struggle with spatial reasoning" |
| VLM confuses chest and inventory grids | Low | High (wrong output) | Iterative prompt engineering; add few-shot examples if needed |
| UI scale variation breaks detection | Low | Medium | Test at 75%-150% scale in synthetic data; VLM should be scale-invariant |
| 1.6 update introduces new UI layouts | Medium | Low (post-MVP) | Document assumption: vanilla 1.6 UI only; defer mod support |

### We Are Committing To

1. **Accepting uncropped screenshots** from users (chest + inventory visible)
2. **Prompting Qwen2.5-VL** to isolate the upper chest grid
3. **Tracking Grid Detection Accuracy** as a first-class metric (≥95% target)
4. **Testing both VLMs** on dual-grid scenarios (SmolVLM2 may struggle — document this)
5. **Generating dual-grid synthetic data** at multiple resolutions and UI scales
6. **Iterating on prompts** if grid detection is below target (few-shot examples if needed)
7. **Falling back to Option B** (preprocessing) if VLM-first approach fails on Qwen2.5-VL

## Implementation Requirements

### Synthetic Data Generation (`scripts/generate_synthetic_data.py`)

Must support:
- Dual-grid layout generation (chest above, inventory below)
- Variable grid sizes: 3×12 (36 slots) and 3×24 (72 slots)
- Multiple resolutions:
  - iPad Retina: 2048×2732 (4:3 aspect)
  - 1080p: 1920×1080 (16:9)
  - 1440p: 2560×1440 (16:9)
  - 4K: 3840×2160 (16:9)
- UI scale variations: 75%, 100%, 125%
- Inventory grid populated with random items (visual distractor)

### Annotation Schema Update

Add `grid_type` field to JSONL annotations:

```json
{
  "image_id": "550e8400-...",
  "loot_type": "storage_chest",
  "grid": {"rows": 3, "cols": 12},
  "grid_type": "chest_with_inventory",
  "cells": [...]
}
```

**Values**: `"chest_only"` (cropped) or `"chest_with_inventory"` (dual-grid)

This tracks whether the VLM is seeing dual-grid or single-grid screenshots during evaluation.

### Evaluation Metric: Grid Detection Accuracy

**Definition**: % of dual-grid screenshots where the VLM correctly identified and analyzed only the chest grid

**Measurement**:
- Compare VLM output cell count to ground truth chest grid size
- If VLM outputs 36 cells for a 3×12 chest: ✓ correct
- If VLM outputs 72+ cells (chest + inventory): ✗ analyzed both grids
- If VLM outputs <36 cells: ✗ incomplete grid

**MVP Target**: ≥ 95% (grid detection is critical for correct output)

**Implementation**: Add to `src/stardew_vision/models/evaluate.py`

### VLM Wrapper Update

Update `src/stardew_vision/models/vlm_wrapper.py` system prompt to include grid isolation instructions (see "VLM System Prompt Strategy" above).

### User Submission Guide

Create `docs/user-submission-guide.md` clarifying:
- ✅ Full screenshots accepted (inventory visible is fine)
- ✅ Any platform/resolution supported
- ❌ No cropping required

## Validation Approach

1. **Synthetic data test**: Generate 100 dual-grid screenshots at varied resolutions; run VLM baseline evaluation
2. **Cross-resolution test**: Generate same chest contents at 3 resolutions; verify VLM output is identical
3. **Zero-shot comparison**: Compare Qwen2.5-VL vs. SmolVLM2 grid detection accuracy
4. **Community submission test**: Once real screenshots arrive, validate on 5 dual-grid examples

**Success criteria**:
- Qwen2.5-VL: Grid Detection Accuracy ≥95%
- SmolVLM2: Baseline evaluation complete (accuracy may be lower — this is expected)

## Conference Talk Narrative

**Expected outcome**: Qwen2.5-VL succeeds (≥95%), SmolVLM2 struggles (<80%)

**Talk story arc**:
1. **Problem**: Accessibility for pixel-art games requires spatial reasoning (distinguish chest from inventory)
2. **Approach 1 - Small VLM (SmolVLM2)**: Fast, but 81-token compression loses spatial layout
   - Grid detection: ❌ confuses grids or misses cells
3. **Approach 2 - Large VLM (Qwen2.5-VL)**: Slower, but preserves spatial detail
   - Grid detection: ✅ correctly isolates chest grid
4. **Lesson**: Small VLMs are NOT sufficient for complex UI understanding — accessibility applications need larger, more capable models

## Post-MVP Enhancements

**If Qwen2.5-VL Grid Detection Accuracy < 95%**:
- Add few-shot examples to system prompt (show example dual-grid screenshots with correct output)
- Experiment with vision-focused prompting (e.g., "Draw an imaginary box around the upper grid")
- Fall back to Option B (preprocessing) for production

**If Qwen2.5-VL Grid Detection Accuracy ≥ 95%**:
- Extend to other loot types (shipping bin, Junimo hut)
- Remove `grid_type` annotation field (not needed for tracking)
- Fine-tune only Qwen2.5-VL (skip SmolVLM2 if zero-shot is poor)

## References

- [ADR-001](001-vlm-selection.md): VLM selection — Qwen2.5-VL's dynamic resolution supports this approach
- [ADR-002](002-vlm-role-architecture.md): Structured JSON output — flexible enough to handle variable grid sizes
- [ADR-007](007-overlay-detection-strategy.md): Overlay detection — assumed clean grid input; this ADR extends to handle dual-grid
- `docs/plan.md`: Overall project timeline
- `docs/data-collection-plan.md`: Synthetic data generation requirements
