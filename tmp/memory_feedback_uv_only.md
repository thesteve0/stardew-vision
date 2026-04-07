---
name: Always use uv, never pip
description: Package management rule — uv only, never pip install in this project
type: feedback
---

Always use `uv` for package management in this project. Never use `pip install`.

**Why:** This is a ROCm devcontainer. The PyTorch build, numpy, and other GPU packages are ROCm-provided binaries placed outside the normal pip package index. Running `pip install` on any package that overlaps with these (torch, numpy, scipy, etc.) silently overwrites the ROCm build with a CPU-only version, breaking all GPU access. Additionally, the user has explicitly set this as a project rule.

**How to apply:**
- To add a new dependency: `uv add <package>`
- To install from lockfile: `uv sync`
- To run a one-off tool: `uvx <tool>` or `uv run <tool>`
- Exception — bootstrapping uv itself in a fresh Dockerfile: `pip install uv` is acceptable ONLY as the first step in a container build, before the project venv exists
- When writing Dockerfiles, the pattern `RUN pip install uv && uv sync` is acceptable for the container bootstrap only
