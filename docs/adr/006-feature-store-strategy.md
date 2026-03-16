# ADR-006: Feature Store Strategy — Feast

**Date**: 2026-03-03
**Status**: Proposed (Phase 2 — not blocking MVP)
**Deciders**: Project team

## Context

The user wants to use Feast as a feature store for: training/testing/validation images, VLM JSON output, and output audio files. Feast is designed for tabular/numeric ML features (embeddings, scalars, counts) and is part of the Red Hat OpenShift AI ecosystem.

Key tension: Feast is not designed for binary data (images, audio). The question is how to use it usefully without letting it block the 1-2 month MVP timeline.

## Decision

**Phase 1 (MVP, weeks 1-4)**: Use the filesystem-based JSONL approach for all data. Design the annotation schema to be **Feast-compatible from day 1** (flat features, explicit `image_id` UUIDs, timestamps on every record). No Feast setup required.

**Phase 2 (weeks 5-6 or post-MVP)**: Layer Feast on top. Because the Phase 1 schema is already Feast-compatible, migration is writing a `feature_store.yaml` and a data ingestion script — not redesigning the data model.

## What Goes in Feast vs. Object Storage

| Data Type | Stored In | Feast Role |
|-----------|-----------|------------|
| Images (PNG) | Filesystem (`datasets/raw/`) or MinIO/S3 on OpenShift | Feast stores URI + metadata only |
| Audio files (WAV) | Filesystem or MinIO/S3 | Feast stores URI + TTS model version + duration |
| Cell annotations (ground truth) | **Feast** — flat features per cell | Primary use case: entity (image_id, row, col) → item_name, quantity, occupied |
| VLM predictions | **Feast** — flat features per prediction | entity (image_id, model_version, row, col) → predicted_item, exact_match, fuzzy_score |
| Image metadata | **Feast** | entity (image_id) → source, loot_type, grid_rows, grid_cols, split |

Feast never stores raw binary files. Binary files always live in object storage; Feast stores the metadata and ML features that describe them.

## Feast Feature Views (Phase 2 Design)

```python
# feature_store.yaml sketch
entities:
  - name: image
    value_type: STRING  # UUID

  - name: cell
    value_type: STRING  # composite: "{image_id}_{row}_{col}"

feature_views:
  - name: image_metadata
    entities: [image]
    features: [source, loot_type, grid_rows, grid_cols, split, image_uri]

  - name: cell_ground_truth
    entities: [cell]
    features: [item_name, quantity, occupied, annotated_by, annotation_date]

  - name: vlm_predictions
    entities: [cell]
    features: [predicted_item, predicted_quantity, exact_match, fuzzy_score, model_version]

  - name: audio_outputs
    entities: [image]
    features: [audio_uri, tts_model_version, duration_seconds]
```

## Complexity Analysis

| Aspect | Filesystem only | With Feast |
|--------|----------------|-----------|
| Setup time | 0 | +1-2 weeks |
| New services | 0 | Offline store + Online store (Redis) + Registry |
| Schema changes | Edit JSONL | `feast apply` + migration |
| Point-in-time feature joins | Manual | Built-in |
| OpenShift AI integration | Manual | Native (Red Hat Data Science Feast Helm chart) |
| Talk pedagogical value | Low | High (production-grade ML architecture) |

## Alternatives Considered

| Option | Trade-offs |
|--------|-----------|
| **Feast from day 1** | Blocks critical path by 1-2 weeks; premature optimization before data schema is stable |
| **No Feast ever** | Simpler, but misses the production-architecture story for the talk; harder to track predictions across model versions |
| **Delta Lake / Iceberg instead** | More appropriate for pure offline analytics; lacks online serving capability |

## Consequences

**Gets easier (Phase 2)**: Point-in-time correct feature retrieval for training; consistent features between training and serving; model version comparison queries (e.g., "show all cells where v1 was wrong but v2 was right").

**Gets harder**: Two services to run; schema discipline required; team needs to understand Feast's entity/feature-view mental model.

**We are committing to** (Phase 1): Designing the JSONL annotation schema with `image_id` UUIDs and timestamps so it can be ingested into Feast without schema changes later.

## Dependencies (Phase 2 only)

```toml
"feast[redis]>=0.40.0",
```

On OpenShift AI: use the Red Hat Data Science Feast Helm chart; Redis online store is included.
