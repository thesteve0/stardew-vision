# Plan: Documentation Updates for Architecture Pivot to Agent/Tool-Calling Pipeline

**Scope**: This plan covers ONLY the documentation updates. No code will be written.

## Context

The project is pivoting from a "VLM reads grid cells and outputs structured JSON" architecture to an **agent/tool-calling architecture** focused on reading specific UI panels from Stardew Valley screenshots aloud to visually impaired players. The new architecture is more modular (one agent per screen type), the MVP problem is simpler (text extraction, not object detection), and the design scales naturally as new screen types are added.

The user's daughter (Katarina) needs specific panels read from specific screens -- starting with the right detail column in Pierre's shop. This is NOT a full-page OCR problem; it's a targeted extraction pipeline.

## New Architecture

```
User uploads screenshot
        |
        v
[Orchestrator VLM - Qwen2.5-VL-7B, LoRA fine-tuned, GPU]
   Classifies screen type, calls tools:
        |
        +-- tool: crop_pierres_detail_panel(image)
        |       |-> [OpenCV template matching] -> cropped right panel
        |       |-> [OCR agent - Tesseract/EasyOCR, CPU] -> extracted text
        |       |-> returns structured text to orchestrator
        |
        +-- tool: crop_tv_dialog(image)          [Phase 2]
        +-- tool: crop_inventory_tooltip(image)   [Phase 3]
        |
        v
   Orchestrator formats narration from extracted text
        |
        v
[TTS Agent - MeloTTS, CPU]
        |
        v
   Audio file returned to user
```

**Key design decisions from discussion:**
- Orchestrator is a VLM (needs vision to classify screen types) - Qwen2.5-VL-7B with LoRA fine-tuning
- Text extraction uses CPU-only OCR (Tesseract/EasyOCR), NOT another VLM
- Cropping uses OpenCV template matching (handles resolution variations without ML)
- Separate models from day one (orchestrator VLM on GPU, extraction on CPU)

## Priority Screens

1. **Pierre's shop** (`datasets/from-katarina/1_pierres_top.jpg`) -- MVP
   - Read the far right column: item name, description, price, quantity selected, total cost
   - Example: "You are buying Parsnip seeds. Plant these in the spring. Takes 4 days to mature. 20 gold pieces for each pack. You currently have 60 packs selected for a total cost of one thousand two hundred gold pieces"
2. **TV screen** (`datasets/from-katarina/2_tv_second.jpg`) -- Phase 2
3. **Inventory** (`datasets/from-katarina/3_inventory_third.jpg`) -- Phase 3

## Documentation Updates

Update all project docs to reflect the new architecture.

### 1.1 New ADR-009: Agent/Tool-Calling Architecture
- **File**: `docs/adr/009-agent-tool-calling-architecture.md`
- Supersedes ADR-002 (VLM Role Architecture)
- Documents: orchestrator VLM + tool dispatch + specialized agents pattern
- Covers: why separate models, why tool-calling, how it scales to new screen types

### 1.2 New ADR-010: Screen Region Extraction Strategy
- **File**: `docs/adr/010-screen-region-extraction.md`
- Documents: OpenCV template matching for UI region cropping
- Documents: OCR (Tesseract/EasyOCR) for text extraction on CPU
- Rationale: CPU-only extraction keeps GPU free for orchestrator

### 1.3 Update existing ADRs
- **ADR-002** (`docs/adr/002-vlm-role-architecture.md`): Change status to "Superseded by ADR-009"
- **ADR-007** (`docs/adr/007-overlay-detection-strategy.md`): Change status to "Deferred" (grid-cell specific, not relevant to current screen types)
- **ADR-008** (`docs/adr/008-grid-detection-strategy.md`): Change status to "Deferred" (same reason)
- **ADR-001** (`docs/adr/001-vlm-selection.md`): Update role description -- Qwen2.5-VL-7B is now the orchestrator, not the grid reader. SmolVLM2 comparison shifts to "can it orchestrate?"
- **ADR-005** (`docs/adr/005-serving-strategy.md`): Minor update -- API interaction now involves tool-calling

### 1.4 Rewrite plan.md
- **File**: `docs/plan.md`
- New architecture diagram (as above)
- New phase sequence: Pierre's shop MVP -> TV -> Inventory
- New data strategy: screen-type screenshots for orchestrator training, Pierre's shop screenshots for OCR evaluation
- Updated evaluation metrics: screen classification accuracy, text extraction accuracy, end-to-end narration quality

### 1.5 Update CLAUDE.md
- Architecture section: replace grid-cell JSON pipeline with agent/tool-calling pipeline
- Codebase structure: update `src/` layout for agents, tools, cropping
- Key files: update for new module paths
- Architectural decisions: update quick reference
- Remove/update grid-specific patterns and known issues

### 1.6 Update data-collection-plan.md
- **File**: `docs/data-collection-plan.md`
- Refocus from synthetic grid data to real screen-type screenshots
- Track 1: Pierre's shop screenshots (different items selected, different resolutions)
- Track 2: TV, inventory, other screen types
- New annotation approach: screen_type label + expected extracted text

### 1.7 Update configs/output_schema.json
- Replace single grid-cell schema with per-screen-type schemas
- Pierre's shop schema: `{ selected_item: { name, description, price_per_unit, quantity_selected, total_cost } }`

### ADRs that stay unchanged
- ADR-003 (TTS - MeloTTS) -- no changes
- ADR-004 (Repo structure - monorepo) -- no changes
- ADR-006 (Feature store - Feast Phase 2) -- no changes

## Execution Order

1. New ADR-009 (agent/tool-calling architecture) -- foundational, other docs reference it
2. New ADR-010 (screen region extraction) -- depends on ADR-009
3. Update ADR-002 status to Superseded
4. Update ADR-007, ADR-008 status to Deferred
5. Update ADR-001 role description
6. Update ADR-005 serving details
7. Rewrite plan.md (references all ADRs)
8. Update CLAUDE.md (references plan.md and ADRs)
9. Rewrite data-collection-plan.md
10. Update configs/output_schema.json

## Verification

After all doc updates are complete:
1. All ADRs are internally consistent (no contradictions between them)
2. CLAUDE.md accurately reflects the new architecture
3. plan.md matches the architecture described in ADR-009 and ADR-010
4. data-collection-plan.md is refocused on screen-type screenshots
5. output_schema.json validates against a sample Pierre's shop extraction result

## Files to Modify/Create

| File | Action |
|------|--------|
| `docs/adr/009-agent-tool-calling-architecture.md` | Create |
| `docs/adr/010-screen-region-extraction.md` | Create |
| `docs/adr/002-vlm-role-architecture.md` | Update status to Superseded |
| `docs/adr/007-overlay-detection-strategy.md` | Update status to Deferred |
| `docs/adr/008-grid-detection-strategy.md` | Update status to Deferred |
| `docs/adr/001-vlm-selection.md` | Update role description |
| `docs/adr/005-serving-strategy.md` | Minor update |
| `docs/plan.md` | Major rewrite |
| `CLAUDE.md` | Update architecture, structure, patterns |
| `docs/data-collection-plan.md` | Refocus on screen-type screenshots |
| `configs/output_schema.json` | Replace with per-screen-type schemas |

## Existing Assets to Reuse

- `datasets/from-katarina/*.jpg` -- 7 real screenshots covering multiple screen types
- `datasets/assets/` -- game sprites, fonts, UI frames (useful for future phases)
- `configs/output_schema.json` -- structure to build from (replace content)
- `docs/adr/000-adr-template.md` -- template for new ADRs
- All devcontainer configuration (ROCm, GPU, env vars)
- `scripts/` -- existing utility scripts stay as-is
