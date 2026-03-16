# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a ROCm-based data science devcontainer template, ported from the CUDA version at https://github.com/thesteve0/datascience-template-CUDA. It provides development container configurations optimized for machine learning and data science work on AMD GPUs using ROCm.

### Key Objectives

1. **Port from CUDA to ROCm**: Adapt the NVIDIA PyTorch container setup to use AMD ROCm containers
2. **Incorporate Improvements**: Apply lessons learned from using the CUDA template in production
3. **Enhanced Dependency Management**: Better handling of conflicts between container-provided libraries and project requirements
4. **Multi-IDE Support**: Provide devcontainer configurations for both VSCode and JetBrains IDEs

## Architecture Overview

The template follows a fork-friendly devcontainer design with these core components:

### Core Components

- **Base Container**: Official AMD `rocm/pytorch:rocm7.2_ubuntu24.04_py3.12_pytorch_release_2.9.1` (user-verified working on Strix Halo and Steam Deck)
- **Multi-IDE Devcontainers**: Full development environment configurations for both VSCode and JetBrains (created by setup script)
- **GPU Access**: Direct AMD GPU access inside containers
- **Persistent Volumes**: Separate named volumes for models, datasets, and caches to survive container rebuilds
- **Dependency Resolution**: Smart filtering of requirements to avoid conflicts with ROCm-provided packages
- **Claude Code Integration**: Built-in support for Claude Code CLI via devcontainer feature
- **External Data Access**: Host ~/data directory mounted at /data in container for accessing datasets outside project

### Repository Structure

Template files in the repository root:
```
datascience-template-ROCm/
├── devcontainer.json          # Template for VSCode devcontainer
├── setup-project.sh           # Initial project setup script
├── setup-environment.sh       # Post-creation environment configuration
├── resolve-dependencies.py    # Filters dependencies to avoid package conflicts
├── cleanup-script.sh          # Clean up Docker resources
├── CLAUDE.md                  # This file
├── TODO.md                    # Project roadmap and task tracking
└── README.md
```

### Target Hardware

This template is specifically designed for **consumer AMD GPUs**:
- AMD Ryzen AI Max+ 395 (Strix Halo - gfx1151 architecture)
- AMD Ryzen AI 300 Series (Strix Point - gfx1150 architecture)
- Custom Steam Deck configurations
- Similar consumer-grade AMD APUs with integrated graphics

**Official Documentation for Consumer GPUs**:
- [ROCm 7.2 for Radeon and Ryzen](https://rocm.docs.amd.com/projects/radeon-ryzen/en/docs-7.2/index.html)
  - ROCm 7.2 is the first "production-ready" release for Strix Halo/Point
  - Native gfx1151/gfx1150 support (no HSA_OVERRIDE_GFX_VERSION needed)
  - PyTorch 2.9.1 with official production support
  - Up to 128GB shared memory on Ryzen APUs
- [Compatibility Matrix](https://rocm.docs.amd.com/projects/radeon-ryzen/en/docs-7.2/docs/compatibility/compatibilityryz/native_linux/native_linux_compatibility.html)

**Precision Support**: FP16 is the only officially validated precision type. Other data types (BF16, FP32, INT8) may work but have not been formally tested by AMD.

**Note**: While AMD's general ROCm documentation focuses on data center GPUs (MI300X series), the consumer GPU guide above and the `rocm/pytorch` image have been verified to work on Ryzen/Radeon hardware.

### Project Structure (created by setup-project.sh)

When `setup-project.sh` is run, it creates:
```
my-ml-project/
├── .devcontainer/
│   ├── devcontainer.json      # VSCode devcontainer configuration
│   └── ...                    # Additional VSCode-specific files
├── .idea/                     # JetBrains configuration (if selected)
├── configs/                   # Configuration files
├── scripts/                   # Utility scripts
├── src/                       # Source code
├── tests/                     # Test files
├── models/                    # Model storage (volume mount)
├── datasets/                  # Dataset storage (volume mount)
└── .cache/                    # Cache directory (volume mount)
```

## Dependency Management Philosophy

### The Problem

ROCm containers (like NVIDIA containers) come with pre-installed optimized libraries. Installing packages from PyPI that conflict with these can break GPU support or introduce version conflicts.

### The Solution

The `resolve-dependencies.py` script:
- Reads `requirements.txt` or `pyproject.toml`
- Compares against ROCm-provided packages
- Creates filtered versions that skip conflicting packages
- Installs remaining dependencies using `uv` into the system environment

This preserves ROCm optimizations while allowing additional package installation.

### Virtual Environment Design - CRITICAL: Python Version Matching

The template uses a `.pth` bridge file approach (NOT `--system-site-packages`) to make container packages accessible while preventing accidental overwrites.

**Why .pth instead of --system-site-packages:**
- `--system-site-packages` would allow `pip install torch` to overwrite ROCm packages, even with uv's `exclude-dependencies`
- The `.pth` file makes packages importable but doesn't affect pip's package resolution
- This provides stronger protection against accidental overwrites via direct pip usage

**CRITICAL REQUIREMENT: Python Version Must Match**

The `.venv` MUST be created with `/opt/venv/bin/python` to ensure Python version consistency:

- Container's `/opt/venv` uses Python 3.12 (as of ROCm 7.2 containers)
- If `.venv` is created with a different system Python version, **binary incompatibility** breaks numpy/torch imports
- The misleading error "importing numpy from source directory" actually means "C extension binary incompatibility"
- Python versions cannot load `.so` files compiled for different Python versions

**How It Works:**

1. `setup-environment.sh` detects container Python version: `/opt/venv/bin/python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"`
2. Creates `.venv` using that Python: `/opt/venv/bin/python -m venv .venv`
3. Verifies versions match after creation (exits with error if mismatch detected)
4. Creates dynamic `.pth` bridge: `.venv/lib/python3.12/site-packages/_rocm_bridge.pth` → `/opt/venv/lib/python3.12/site-packages`
5. Python loads the .pth file and adds `/opt/venv` to sys.path
6. Container packages (torch, numpy) become importable
7. uv's `exclude-dependencies` still prevents installing excluded packages

**Version Mismatch Detection:**

The template now automatically verifies Python versions match during venv creation and will error with a clear message if they don't. This prevents the silent failure mode that causes confusing import errors later.

**Common Scenario That Triggers Mismatch:**

- Manually running `python3 -m venv .venv` instead of `/opt/venv/bin/python -m venv .venv`
- The system `python3` might be a different version than the container's Python
- This creates a venv with the wrong Python version, breaking the .pth bridge

**Why This Matters for Claude Code:**

When working on this template or projects created from it, remember that:
- VSCode's Ctrl+F5 runner uses `.venv/bin/python` to execute code
- If Python versions don't match, imports of container packages will fail
- The error message is misleading ("importing from source directory") but the root cause is binary incompatibility
- Always check Python versions first when debugging import errors

## ROCm-Specific Considerations

### Key Differences from CUDA

- **Base Images**: Use AMD ROCm containers (e.g., `rocm/pytorch`) instead of NVIDIA
- **GPU Detection**: Use `amd-smi` (preferred) or `rocm-smi` instead of `nvidia-smi`
- **Driver Requirements**: ROCm drivers and ROCm runtime instead of NVIDIA drivers and CUDA toolkit
- **Environment Variables**: ROCm-specific variables (e.g., `HIP_VISIBLE_DEVICES` instead of `CUDA_VISIBLE_DEVICES`)
- **PyTorch Differences**: ROCm PyTorch builds may have different package names and dependencies
- **Container Runtime**: May require additional Docker configuration for ROCm GPU access

### Hardware Requirements

**Supported Consumer Hardware**:
- Ryzen AI Max 300 Series (includes AI Max+ 395 Strix Halo)
- Radeon RX 7000 Series (RDNA 3) and RX 9000 Series (RDNA 4)
- Custom configurations (e.g., Steam Deck with custom Ryzen chips)

**System Requirements**:
- Linux host with ROCm 7.2+ drivers installed (production release for consumer GPUs)
- Docker with proper ROCm container support
- Recommended: 32GB+ RAM, 1TB NVMe SSD
- Check [ROCm Radeon/Ryzen compatibility matrix](https://rocm.docs.amd.com/projects/radeon-ryzen/en/latest/index.html) for your specific hardware

## IDE Support

### VSCode

- Configuration in `.devcontainer/devcontainer.json` (created by setup script)
- Automatically detects and prompts to reopen in container
- Extensions auto-installed (Python, Jupyter, linting, formatting)
- Integrated terminal runs inside container with GPU access

### JetBrains (PyCharm/Gateway)

- Uses same `devcontainer.json` as VSCode (shared configuration)
- Backend specified in `customizations.jetbrains.backend: "IU"` (IntelliJ IDEA Ultimate)
- `.idea/` directory pre-configured by `setup-project.sh` with `PYTHON_MODULE` type
  - Source roots: `src/` pre-configured as Sources, `tests/` as Test Sources
  - Excludes: `.venv/`, `models/`, `datasets/`, `.cache/` pre-configured as Excluded
- **Manual configuration still required for Python interpreter**:
  1. File → Project Structure (`Ctrl+Alt+Shift+S`)
  2. Project → SDK dropdown → Add SDK → Add Python Interpreter
  3. Location: Local Machine, Environment: Select existing, Type: **uv**
  4. Path to uv: `/opt/venv/bin/uv`
  5. Environment: Select `Python 3.12 (/workspaces/PROJECT_NAME/.venv)`
- Ruff linter/formatter enabled by default via `.idea/ruff.xml`

**Python Interpreter Limitation**: JetBrains does not support automatic interpreter configuration in devcontainers ([IJPL-174150](https://youtrack.jetbrains.com/issue/IJPL-174150)). The `setup-project.sh` pre-creates `.idea/` with correct `PYTHON_MODULE` type (not `JAVA_MODULE`) so the interpreter dialog works correctly, but users must still manually configure the interpreter using the uv type.

### Shared Infrastructure

Both VSCode and JetBrains use:
- Same `devcontainer.json` configuration
- Same ROCm container, GPU access, environment variables
- Same `setup-environment.sh` script (IDE-agnostic)
- Same Python venv with .pth bridge for ROCm packages

## Development Workflow

### Initial Setup

1. Run `setup-project.sh` to initialize the project structure and create `.devcontainer/` directory
2. Choose your IDE:
   - **VSCode**: Open project, reopen in container when prompted
   - **JetBrains**: Use Gateway or IDE's devcontainer feature
3. Container builds and runs `setup-environment.sh` automatically

### Working with Dependencies

1. Add packages to `requirements.txt` or `pyproject.toml`
2. Run `resolve-dependencies.py` to filter conflicts
3. Install using `uv pip install` with filtered file
4. Verify GPU access still works with `amd-smi` (or `rocm-smi`) or PyTorch GPU check

### Verifying GPU Access

```bash
# Check GPU visibility (amd-smi is preferred, rocm-smi still works)
amd-smi

# Test PyTorch GPU access
python -c "import torch; print(f'GPU available: {torch.cuda.is_available()}'); print(f'GPU count: {torch.cuda.device_count()}')"
```

### External Repository Integration

The template supports cloning external projects into the workspace while maintaining the devcontainer benefits.

## Known Considerations and Challenges

1. **Base Container Decision**: ✅ Decided to use `rocm/pytorch` (user-verified on target hardware)
2. **Consumer GPU Documentation Gap**: AMD docs focus on MI300X data center GPUs, but `rocm/pytorch` works on consumer hardware - will document real-world results
3. **Package Name Differences**: ROCm package names may differ from CUDA versions
4. **Library Compatibility**: Some ML libraries have better CUDA than ROCm support - will test and document
5. **gfx1151-Specific Issues**: Some features may have limitations (hipBLASLt, AOTriton) - will document workarounds
6. **JetBrains ROCm Support**: May require additional configuration vs VSCode

## Docker Image Research Findings

Comparison of AMD ROCm Docker images:

- **rocm/pytorch**: General-purpose, training and inference, actively maintained ✅ **SELECTED**
  - Works on Strix Halo and Steam Deck (user-verified)
  - Handles both training and inference
  - ROCm 7.2 with Python 3.12 and PyTorch 2.9.1

- **rocm/pytorch-training**: Training-focused, ⚠️ being deprecated in favor of primus
  - Not recommended for new projects

- **rocm/primus**: New unified training framework
  - Data center GPUs only (MI300X, MI325X, etc.)
  - Overkill for single-GPU consumer hardware
  - Designed for multi-node distributed training

## Current Status

Template is feature-complete with ROCm 7.2 support. Ready for end-to-end testing and release preparation.

## Important Resources

### Official AMD Documentation
- **[ROCm 7.2 for Radeon and Ryzen GPUs](https://rocm.docs.amd.com/projects/radeon-ryzen/en/docs-7.2/index.html)** - Primary documentation for consumer GPU support
  - ROCm 7.2 production release notes
  - PyTorch 2.9.1 installation for Ryzen APUs
  - Compatibility matrices for Radeon/Ryzen hardware
  - Framework support (PyTorch, TensorFlow, JAX, ONNX Runtime)
- **[ROCm 7.2 Compatibility Matrix](https://rocm.docs.amd.com/projects/radeon-ryzen/en/docs-7.2/docs/compatibility/compatibilityryz/native_linux/native_linux_compatibility.html)** - Supported precision types and hardware

- **[ROCm General Documentation](https://rocm.docs.amd.com/)** - Data center GPU focused (MI300X series)
  - Training and inference guides
  - Container documentation
  - Framework compatibility matrices

### Base Template
- **[CUDA Template Repository](https://github.com/thesteve0/datascience-template-CUDA)** - Original NVIDIA-based template being ported

### Community Resources
- AMD Developer Discord (for consumer GPU support questions)
- [ROCm GitHub Issues](https://github.com/ROCm/ROCm/issues) - For reporting bugs and tracking gfx1151-specific issues

## Claude Code Integration

### Claude Code Feature

The devcontainer includes the Claude Code feature (`ghcr.io/anthropics/devcontainer-features/claude-code:1`), which provides:

- Claude Code CLI available inside the devcontainer
- Google Cloud credentials mounted from host for Vertex AI authentication
- Environment variables passed from host to container

### Required Configuration

**Host Environment Variables** (set on your host machine):
```bash
export ANTHROPIC_VERTEX_PROJECT_ID="your-gcp-project-id"
export ANTHROPIC_VERTEX_REGION="us-east5"  # or your preferred region
export CLAUDE_CODE_USE_VERTEX="true"
```

**Mounted Credentials:**
- Host `~/.config/gcloud` → Container `/home/stpousty-devcontainer/.config/gcloud` (read-only)

### External Data Mount

The devcontainer mounts your host's `~/data` directory at `/data` in the container. This allows access to datasets and files outside the project directory without copying them into the workspace.

**Usage:**
```bash
# Inside container
ls /data                    # Access host ~/data directory
cp /data/dataset.csv ./datasets/  # Copy data into project
ln -s /data/models ./models/external  # Link to external models
```

**Use Cases:**
- Access large datasets stored on host without duplication
- Share data between multiple projects
- Keep proprietary data outside version control
- Reference pre-trained models stored centrally

## Claude Code Working Notes

**Testing Limitations**: Claude Code cannot run or test this project directly since it requires execution inside a devcontainer with GPU access. Only host-level commands (file operations, git, etc.) can be executed. For GPU tests, Docker commands, or devcontainer operations, provide the commands for the user to run manually.

**Claude Code Availability**: When working inside the devcontainer, Claude Code is available via the CLI. The integration includes authentication via Google Cloud Vertex AI and can be used for AI-assisted development within the container environment.