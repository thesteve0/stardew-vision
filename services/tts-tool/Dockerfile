FROM python:3.12-slim

WORKDIR /app

# espeak-ng is required by Kokoro for phonemization
RUN apt-get update && apt-get install -y --no-install-recommends \
    espeak-ng \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency installation
RUN pip install uv

# Copy and install only TTS tool dependencies
COPY services/tts-tool/pyproject.toml .
RUN uv sync --no-dev

# Pre-download spaCy model (needed by Kokoro) to avoid runtime permission errors
RUN uv run python -m spacy download en_core_web_sm

# Copy the TTS tool package
COPY services/tts-tool/stardew_tts/ ./stardew_tts/

ENV PYTHONPATH=/app
ENV UV_CACHE_DIR=/tmp/.uv

EXPOSE 8003
CMD ["uv", "run", "python", "-m", "uvicorn", "stardew_tts.app:app", "--host", "0.0.0.0", "--port", "8003"]
