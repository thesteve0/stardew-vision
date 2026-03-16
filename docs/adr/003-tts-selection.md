# ADR-003: Text-to-Speech (TTS) Model Selection

**Date**: 2026-03-03 (updated 2026-03-03)
**Status**: Accepted
**Deciders**: Project team

## Context

The pipeline ends with converting a natural language description of loot box contents into an audio file returned to the user. The TTS step must:
- Run locally (no internet required for the demo or for the user)
- Produce intelligible, pleasant-sounding speech appropriate for an accessibility use case
- Respond quickly enough to feel responsive in a web app (target: < 2 seconds for a typical loot box description)
- Install cleanly in the devcontainer alongside the ROCm PyTorch stack
- Be fully open-source and permissively licensed (public GitHub repo)
- Work on AMD Strix Halo (ROCm 7.2) development environment
- Deploy to OpenShift AI (NVIDIA GPUs) production environment
- Avoid vendor lock-in where possible

## Decision

**Primary**: [MeloTTS-English](https://huggingface.co/myshell-ai/MeloTTS-English) — Python package via [MeloTTS GitHub](https://github.com/myshell-ai/MeloTTS)

```python
from melo.api import TTS
import io

# Initialize once at module load
model = TTS(language='EN', device='auto')  # auto = GPU if available, else CPU
speaker_id = model.hps.data.spk2id['EN-US']  # American English accent

def text_to_audio_bytes(description: str, speed: float = 1.0) -> bytes:
    """Generate audio using MeloTTS."""
    buffer = io.BytesIO()
    model.tts_to_file(description, speaker_id, buffer, speed=speed, format='wav')
    return buffer.getvalue()
```

**Key Features**:
- CPU real-time inference (no GPU required)
- Optional GPU acceleration (auto-detected)
- Multiple English accents: US, UK, Australian, Indian
- High-quality audio output
- 225k+ downloads/month (well-tested, active community)
- MIT license

## Alternatives Considered

| Option | Why not selected |
|--------|----------------|
| **Kokoro TTS** | Originally selected but lower audio quality (more robotic than MeloTTS); fixed voice (no accent options); smaller community (less popular); Apache 2.0 license is good but MeloTTS offers better overall value |
| **faster-qwen3-tts** | State-of-the-art quality and ultra-low latency (156-174ms on GPU), but **NVIDIA CUDA only** — does not work on AMD Strix Halo dev machine; vendor lock-in violates project principle; competes with VLM for GPU memory; cannot test TTS during development without separate NVIDIA machine |
| **Coqui TTS / XTTS-v2** | Higher quality, multi-speaker, but significantly heavier (separate model download ~1.8GB); slower inference; installation conflicts with ROCm stack reported; post-MVP upgrade path |
| **Bark** | Creative and expressive but very slow on CPU, unpredictable performance on ROCm, not suitable for real-time web responses |
| **StyleTTS2** | High quality but complex installation; limited HuggingFace ecosystem integration |
| **ElevenLabs API** | Excellent quality but requires internet, API key, and costs money per character; not appropriate for a fully local demo or for teaching the open-source stack |
| **OpenAI TTS API** | Same concerns as ElevenLabs; also requires OpenAI account |
| **pyttsx3 (permanent)** | Works immediately but robotic quality; acceptable as development placeholder, not for production or demo |

## Consequences

**Gets easier**:
- CPU real-time inference for typical loot box descriptions (~200 characters) - meets <2s latency requirement
- Platform independence - works on AMD (dev) and NVIDIA (prod), no vendor lock-in
- Multiple English accent options (US, UK, AU, IN) - can choose based on user preference
- High-quality audio output - better than Kokoro, good enough for accessibility use case
- Very popular model (225k+ downloads/month) - well-tested, active community support
- MIT license - permissive for commercial use
- Optional GPU acceleration - can leverage NVIDIA GPUs in production if desired, but doesn't require it
- Keeps GPU free for VLM in development (CPU-only mode)

**Gets harder**:
- Installation slightly more complex than Kokoro (requires following [GitHub install guide](https://github.com/myshell-ai/MeloTTS/blob/main/docs/install.md))
- Model size and sample rate not fully documented in HuggingFace model card
- Need to manage accent selection (4 options vs. 1 fixed voice in Kokoro)

**We are committing to**:
- WAV audio output (sample rate TBD based on MeloTTS defaults)
- American English (`EN-US`) accent as default (can be changed to UK/AU/IN if needed)
- `device='auto'` mode - uses GPU if available in production, CPU in development
- MeloTTS API as the audio I/O interface

## Deployment

**Development (AMD Strix Halo, ROCm 7.2)**: MeloTTS runs on CPU - no GPU required, no conflicts with VLM GPU usage.

**Production (OpenShift AI, NVIDIA GPUs)**: Two deployment options:
1. **Integrated** (recommended): MeloTTS runs inside FastAPI webapp pod on CPU (simple, one service)
2. **Separate microservice**: MeloTTS as standalone service on CPU (can scale independently)

Optional: GPU acceleration can be enabled in production by setting `device='cuda'` and allocating GPU resources to the pod. Not required for <2s latency target.

**Docker**: MeloTTS model can be pre-downloaded at Docker build time for faster pod startup (~5-10s vs. first-request download).

## Upgrade Path

After MVP, XTTS-v2 (Coqui) remains the natural next step for even higher-quality, more natural-sounding speech with full voice cloning. The `synthesize.py` interface (`text_to_audio_bytes(description: str) -> bytes`) is designed to be drop-in replaceable — swapping TTS models requires only changes inside `src/stardew_vision/tts/synthesize.py`, not in the rest of the pipeline.
