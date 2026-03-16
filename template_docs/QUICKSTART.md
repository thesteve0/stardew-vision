# ROCm DevContainer Quick Reference

## Verify GPU Access

```bash
amd-smi                    # Check GPU status (preferred)
rocm-smi                   # Legacy GPU status (still works)
python test-gpu.py         # Comprehensive GPU test
```

## Add Dependencies

**Modern workflow (uv with pyproject.toml)**:
```bash
# Edit pyproject.toml dependencies section, then:
uv sync

# Or quick add:
uv add transformers diffusers
```

**Legacy workflow (requirements.txt)**:
```bash
# Edit requirements.txt, then:
python scripts/resolve-dependencies.py requirements.txt
uv pip install -r requirements-filtered.txt
```

## Common Issues

**Import error "importing numpy from source directory"**:
```bash
# Python version mismatch - recreate venv
rm -rf .venv
/opt/venv/bin/python -m venv .venv
# Recreate .pth bridge
PYTHON_VERSION=$(/opt/venv/bin/python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "/opt/venv/lib/python${PYTHON_VERSION}/site-packages" > .venv/lib/python${PYTHON_VERSION}/site-packages/_rocm_bridge.pth
uv sync
```

**GPU not detected**:
```bash
# Check host GPU visibility
amd-smi

# Check container can access GPU
docker run -it --device=/dev/kfd --device=/dev/dri rocm/pytorch:latest amd-smi

# Verify PyTorch sees GPU
python -c "import torch; print(torch.cuda.is_available())"
```

## Data Directories

- `./models/` - Model checkpoints (persists across rebuilds)
- `./datasets/` - Training data (persists across rebuilds)
- `./.cache/` - HuggingFace/PyTorch caches (persists across rebuilds)
- `/data/` - Mounted from `~/data` on host (for external datasets)

## IDE Tips

**VSCode**: Ctrl+Shift+P → "Dev Containers: Rebuild Container"

**JetBrains**: See template_docs/README.md for Gateway setup

For detailed documentation, see `template_docs/README.md` and `template_docs/CLAUDE.md`.
