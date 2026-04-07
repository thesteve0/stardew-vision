FROM python:3.12-slim

WORKDIR /app

# Install uv for fast dependency installation
RUN pip install uv

# Copy and install only OCR tool dependencies
COPY services/ocr-tool/pyproject.toml .
RUN uv sync --no-dev

# Copy the OCR tool package
COPY services/ocr-tool/stardew_ocr/ ./stardew_ocr/

# Assets must be mounted at runtime (template files live in datasets/)
# docker run -v /path/to/datasets:/datasets ...
ENV PYTHONPATH=/app

EXPOSE 8002
CMD ["uv", "run", "python", "-m", "uvicorn", "stardew_ocr.app:app", "--host", "0.0.0.0", "--port", "8002"]
