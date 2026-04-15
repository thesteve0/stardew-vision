FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for OpenCV and PaddleOCR
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency installation
RUN pip install uv

# Copy and install only OCR tool dependencies
COPY services/ocr-tool/pyproject.toml .
RUN uv sync --no-dev

# Copy the OCR tool package
COPY services/ocr-tool/stardew_ocr/ ./stardew_ocr/

# Copy OpenCV template images (self-contained service)
COPY services/ocr-tool/assets/ ./assets/

ENV PYTHONPATH=/app
ENV UV_CACHE_DIR=/tmp/.uv
# PaddleX environment variables (PaddleX is a dependency of PaddleOCR 3.0+)
ENV PADDLEX_HOME=/tmp/.paddlex
ENV PADDLEX_CACHE_DIR=/tmp/.paddlex/cache
ENV PADDLE_HUB_HOME=/tmp/.paddlex/hub
# PaddleOCR environment variable
ENV PADDLE_OCR_BASE_DIR=/tmp/.paddleocr
# HuggingFace cache for PaddleX model downloads
ENV HF_HOME=/tmp/.huggingface

EXPOSE 8002
CMD ["uv", "run", "python", "-m", "uvicorn", "stardew_ocr.app:app", "--host", "0.0.0.0", "--port", "8002"]
