FROM python:3.12-slim

WORKDIR /app

# Install uv for fast dependency installation
RUN pip install uv

# Copy and install only coordinator dependencies
COPY services/coordinator/pyproject.toml .
RUN uv sync --no-dev

# Copy the coordinator package + static assets
COPY services/coordinator/stardew_coordinator/ ./stardew_coordinator/

ENV PYTHONPATH=/app
ENV UV_CACHE_DIR=/tmp/.uv

EXPOSE 8000
CMD ["uv", "run", "python", "-m", "uvicorn", "stardew_coordinator.app:app", "--host", "0.0.0.0", "--port", "8000"]
