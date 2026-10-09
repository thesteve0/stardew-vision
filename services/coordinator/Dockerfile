FROM python:3.12-slim@sha256:05cda9777409a9c3ffddd94a4c476b79f0769a0b4857f0c7ed9226b6800b0d6f

WORKDIR /app

# Pin the installer separately from the Python dependency graph.
COPY --from=ghcr.io/astral-sh/uv:0.11.8@sha256:3b7b60a81d3c57ef471703e5c83fd4aaa33abcd403596fb22ab07db85ae91347 /uv /usr/local/bin/uv

# Copy and install only coordinator dependencies
COPY services/coordinator/pyproject.toml services/coordinator/uv.lock ./
# Install hashed artifacts without resolving, then reject stale project metadata.
# Direct-URL metadata is now cached, so the check can run offline.
RUN uv sync --frozen --no-dev --no-editable && uv lock --check --offline

# Copy the coordinator package + static assets
COPY services/coordinator/stardew_coordinator/ ./stardew_coordinator/

ENV PYTHONPATH=/app
ENV UV_CACHE_DIR=/tmp/.uv
ENV UV_NO_SYNC=1

EXPOSE 8000
CMD ["uv", "run", "--frozen", "--no-dev", "python", "-m", "uvicorn", "stardew_coordinator.app_finetuned:app", "--host", "0.0.0.0", "--port", "8000"]
