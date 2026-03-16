# ADR-004: Repository Structure — Monorepo vs. Multi-Repo

**Date**: 2026-03-03
**Status**: Accepted
**Deciders**: Project team

## Context

The project has several distinct concerns that could reasonably be separated into different repositories:
- Data collection and annotation scripts
- VLM fine-tuning pipeline
- TTS integration
- Web application
- OpenShift AI deployment configuration

The choice between a monorepo and multiple repositories affects: discoverability for talk attendees, ease of sharing, CI/CD complexity, and the ability to refactor across concern boundaries.

## Decision

**Single monorepo** at `github.com/{username}/stardew-vision`.

A separate **HuggingFace Hub organization** holds the dataset and model artifacts (not git repos, but HF repos):
- `{username}/stardew-loot-vision-dataset`
- `{username}/stardew-vision-vlm`

## Alternatives Considered

| Option | Why not selected |
|--------|----------------|
| **Multi-repo** (data / model / webapp / configs as separate git repos) | One `git clone` for talk attendees is far simpler; at MVP scale the coupling between components is tight (data schema changes ripple into model code ripple into webapp); coordination overhead exceeds the benefit of isolation |
| **GitHub monorepo + submodules** | Submodules add friction without adding clear benefit at this scale |
| **Separate HuggingFace Space for webapp** | Could be useful post-MVP for public demo; not appropriate as primary code repo |

## Consequences

**Gets easier**: Talk attendees clone one URL and see the entire project; changes that span components (e.g., changing the JSON schema) are in one commit; no inter-repo dependency management.

**Gets harder**: As the project grows, the repo may become large; if different teams own different components, a monorepo requires coordination on branch strategy.

**We are committing to**:
- `src/stardew_vision/` as the single installable Python package (note: underscore, not hyphen — `stardew-vision` is not a valid Python package identifier)
- `PYTHONPATH=/workspaces/stardew-vision/src` (already set in devcontainer.json) making `import stardew_vision` work
- HuggingFace Hub for model/dataset artifacts; GitHub for source code

## Directory Conventions

- `src/stardew_vision/` — importable application code
- `scripts/` — one-off scripts (data generation, push to HF) not part of the package
- `notebooks/` — Jupyter notebooks for exploration and talk demos
- `docs/` — documentation including ADRs, plan, rubric, data guide
- `configs/` — YAML configuration files for training, serving, and OpenShift
- `datasets/` — host-volume-mounted; not committed to git (add to .gitignore)
- `models/` — host-volume-mounted; not committed to git (add to .gitignore)
- `tests/` — pytest test suite
