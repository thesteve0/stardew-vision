FROM python:3.12-slim@sha256:05cda9777409a9c3ffddd94a4c476b79f0769a0b4857f0c7ed9226b6800b0d6f

WORKDIR /app

# Install system dependencies for OpenCV and PaddleOCR
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Pin the installer separately from the Python dependency graph.
COPY --from=ghcr.io/astral-sh/uv:0.11.8@sha256:3b7b60a81d3c57ef471703e5c83fd4aaa33abcd403596fb22ab07db85ae91347 /uv /usr/local/bin/uv

# Copy and install dependencies
COPY services/ocr-tools/pyproject.toml services/ocr-tools/uv.lock ./
# Install hashed artifacts without resolving, then reject stale project metadata.
# Direct-URL metadata is now cached, so the check can run offline.
RUN uv sync --frozen --no-dev --no-editable && uv lock --check --offline

# Copy the package
COPY services/ocr-tools/stardew_ocr_tools/ ./stardew_ocr_tools/

# Copy assets (layout JSONs, template images, fish sprites, manifest)
COPY services/ocr-tools/assets/ ./assets/

ENV PYTHONPATH=/app
ENV UV_CACHE_DIR=/tmp/.uv
ENV UV_NO_SYNC=1
# PaddleX environment variables
ENV PADDLEX_HOME=/tmp/.paddlex
ENV PADDLEX_CACHE_DIR=/tmp/.paddlex/cache
ENV PADDLE_HUB_HOME=/tmp/.paddlex/hub
# PaddleOCR environment variable
ENV PADDLE_OCR_BASE_DIR=/tmp/.paddleocr
# HuggingFace cache for PaddleX model downloads
ENV HF_HOME=/tmp/.huggingface

EXPOSE 8004
CMD ["uv", "run", "--frozen", "--no-dev", "python", "-m", "uvicorn", "stardew_ocr_tools.app:app", "--host", "0.0.0.0", "--port", "8004"]
