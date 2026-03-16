# ROCm PyTorch ML DevContainer Template

A DevContainer template for PyTorch machine learning development on AMD GPUs using ROCm 7.2. Optimized for consumer AMD hardware (Ryzen AI Max, Radeon RX series) with support for both VSCode and JetBrains IDEs.

**Ported from:** [datascience-template-CUDA](https://github.com/thesteve0/datascience-template-CUDA)

**Current Stack:** ROCm 7.2 | PyTorch 2.9.1 | Python 3.12 | Ubuntu 24.04

## Key Features

- **AMD ROCm GPU Support** - Full GPU acceleration for PyTorch on consumer AMD hardware
- **Intelligent Dependency Management** - Automatically resolves conflicts with ROCm-provided packages
- **Multi-IDE Support** - VSCode and JetBrains configurations
- **Persistent Storage** - Data directories survive container rebuilds (stored in project folder)
- **External Project Integration** - Clone and work with existing repositories seamlessly
- **Docker & Podman** - Works with both container runtimes
- **Claude Code Integration** - Built-in Claude Code CLI with Vertex AI authentication
- **External Data Access** - Host ~/data directory accessible at /data in container

## ROCm 7.2 Highlights

ROCm 7.2 is the first "production-ready" release for Strix Halo and Strix Point:

- **Native Architecture Support** - gfx1151/gfx1150 supported without `HSA_OVERRIDE_GFX_VERSION` workarounds
- **Faster Warm-up Times** - `torch.compile` cold-start reduced from ~60s to ~15s
- **Optimized GEMM** - hipBLASLt with "Origami" tuning for better matrix multiplication performance
- **Improved Memory Management** - Smoother shared memory handling for APUs using system RAM as VRAM
- **Official Production Support** - PyTorch 2.9.1 + Python 3.12 is the validated stack

## ⚠️ Security Notice: Development Only

**This template is designed for local development environments, NOT production deployments.**

The devcontainer user has **passwordless sudo access** (standard for devcontainers) to simplify package installation and system configuration. This is appropriate for single-user development containers but creates significant security risks in production.

**For production ML deployments:**
- Use separate production-focused container images
- Run as non-root user without sudo privileges
- Implement read-only root filesystems where possible
- Follow the principle of least privilege
- Use proper secrets management (not environment variables)
- Apply container security scanning and hardening

This template prioritizes **developer experience** for rapid ML experimentation and development. Production containers require different security trade-offs.

## Supported Hardware

This template is designed for **consumer AMD GPUs**:

### Tested Hardware
- ✅ AMD Ryzen AI Max+ 395 (Strix Halo - gfx1151)
- ✅ Custom Steam Deck configurations
- ✅ Radeon RX 7000 Series (RDNA 3)
- ✅ Radeon RX 9000 Series (RDNA 4)

### System Requirements
- **OS:** Ubuntu 24.04 with ROCm 7.2 drivers (recommended)
- **RAM:** 32GB+ recommended
- **Storage:** 1TB NVMe SSD recommended (models and datasets are large)
- **Container Runtime:** Docker or Podman with ROCm support

### Precision Support

**FP16 is the only officially validated precision type** for Ryzen AI processors. Other data types (BF16, FP32, INT8) may work but have not been formally tested by AMD. For maximum compatibility and performance:
- Use FP16 for training and inference
- Avoid INT4 quantization (often falls back to slow software emulation)
- If you must use FP32, expect lower performance due to memory bandwidth constraints

**Note:** This template targets consumer GPUs. For AMD data center GPUs (MI300X series), see [AMD's official ROCm documentation](https://rocm.docs.amd.com/).

## Prerequisites

### 1. Install ROCm Drivers

Follow the official AMD guide for consumer GPUs:
- [ROCm 7.2 for Radeon and Ryzen GPUs](https://rocm.docs.amd.com/projects/radeon-ryzen/en/docs-7.2/index.html)
- [Compatibility Matrix](https://rocm.docs.amd.com/projects/radeon-ryzen/en/docs-7.2/docs/compatibility/compatibilityryz/native_linux/native_linux_compatibility.html)

For Ryzen AI Max+ 395 (Strix Halo) or similar consumer hardware:
```bash
# Check AMD GPU is visible
lspci | grep -i amd

# Verify ROCm installation (amd-smi is preferred, rocm-smi still works)
amd-smi

# Test PyTorch ROCm (after installing container runtime)
docker run -it --device=/dev/kfd --device=/dev/dri \
    rocm/pytorch:rocm7.2_ubuntu24.04_py3.12_pytorch_release_2.9.1 \
    python -c "import torch; print(f'ROCm available: {torch.cuda.is_available()}')"
```

### 2. Install Container Runtime

**Docker:**
```bash
# Install Docker (Fedora/RHEL)
sudo dnf install docker
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
```

**Podman (alternative):**
```bash
# Install Podman (Fedora/RHEL)
sudo dnf install podman

# Configure VSCode to use Podman instead of Docker
# Add to VSCode settings.json:
# "dev.containers.dockerPath": "podman"
```

**Note:** VSCode Dev Containers automatically handles Podman's user namespace mapping with `--userns=keep-id`. No changes to the devcontainer configuration are needed.

### 3. Install IDE

**VSCode:**
- Install [VSCode](https://code.visualstudio.com/)
- Install "Dev Containers" extension

**JetBrains (PyCharm, etc.):**
- Install [JetBrains Gateway](https://www.jetbrains.com/remote-development/gateway/) or PyCharm Professional
- Devcontainer support requires recent versions

## Quick Start

**New to this template?** See [QUICKSTART.md](QUICKSTART.md) for a step-by-step walkthrough with screenshots and detailed explanations.

### TL;DR for Experienced Users

```bash
# 1. Download template (don't git clone - you want a fresh repo)
#    GitHub → Code → Download ZIP → Extract and rename to your project

# 2. Run setup
cd my-ml-project
./setup-project.sh    # Select IDE, enter git info

# 3. Open in VSCode → "Reopen in Container" (5-10 min first build)
code .

# 4. Test GPU access
python hello-gpu.py   # Quick sanity check (30 sec)
python test-gpu.py    # Full benchmark (2-3 min)

# 5. Add dependencies and start coding
uv add transformers datasets
```

### Option B: Integrate Existing Repository

```bash
# 1. Clone this template
git clone https://github.com/YOUR_USERNAME/datascience-template-ROCm.git my-project-wrapper
cd my-project-wrapper

# 2. Setup with external repo
./setup-project.sh --clone-repo https://github.com/username/existing-ml-project.git

# 3. Open in VSCode and reopen in container
code .

# 4. The external repo is now accessible at ./existing-ml-project/
```

## Usage Guide

### Project Structure

After running `setup-project.sh`, your project will have:

```
my-ml-project/
├── .devcontainer/
│   ├── devcontainer.json       # VSCode devcontainer config
│   └── setup-environment.sh    # Post-creation setup script
├── scripts/
│   └── resolve-dependencies.py # Dependency conflict resolver
├── src/
│   └── my-ml-project/          # Your source code
├── tests/                      # Test files
├── configs/                    # Configuration files
├── models/                     # Persistent volume mount
├── datasets/                   # Persistent volume mount
├── .cache/                     # Persistent volume mount
├── hello-gpu.py                # Quick GPU sanity check
├── test-gpu.py                 # Comprehensive GPU benchmark
├── setup-project.sh            # Project setup script
└── cleanup-script.sh           # Cleanup utility
```

### Managing Dependencies

#### Understanding the Python Environment

When you open the devcontainer, you're working inside a pre-configured environment:

| Component | Location | Notes |
|-----------|----------|-------|
| **Virtual Environment** | `.venv/` (in project root) | Created by `setup-environment.sh`, contains ROCm packages |
| **Python Interpreter** | `.venv/bin/python` | Python 3.12 with ROCm-optimized PyTorch |
| **Package Manager** | `uv` | Fast, modern Python package manager |
| **ROCm PyTorch** | Pre-installed in `.venv/` | DO NOT reinstall from PyPI |

The `setup-environment.sh` script automatically:
1. Creates a `.venv/` directory with `uv venv`
2. Installs all ROCm-provided packages (PyTorch, torchvision, etc.) from the container
3. Generates `rocm-provided.txt` listing protected packages
4. Configures `pyproject.toml` with `exclude-dependencies` to prevent overwriting ROCm packages

#### Adding New Packages (Recommended: uv)

The modern workflow uses `uv` with `pyproject.toml`:

```bash
# 1. Add packages to pyproject.toml dependencies section
#    Edit pyproject.toml and add to the dependencies list:
#    dependencies = [
#        "transformers",
#        "docling",
#    ]

# 2. Install with uv sync
uv sync
```

The `pyproject.toml` contains a `[tool.uv] exclude-dependencies` section that lists all ROCm-provided packages. When you add a package like `transformers` that depends on `torch`, uv sees `torch` in the exclude list and **skips installing it** - preserving your working ROCm PyTorch.

**Quick add (single package):**
```bash
uv add transformers
```

**Verify PyTorch is still the ROCm version after installing:**
```bash
python -c "import torch; print(torch.__version__)"
# Should show: 2.9.1+rocm7.2... (the +rocm suffix is key)
```

#### Alternative: requirements.txt Workflow

For projects using `requirements.txt`, use the `resolve-dependencies.py` script:

```bash
# 1. Add packages to requirements.txt
cat > requirements.txt << EOF
transformers>=4.30.0
diffusers>=0.21.0
accelerate>=0.24.0
datasets>=2.14.0
EOF

# 2. Filter out ROCm-provided packages
python scripts/resolve-dependencies.py requirements.txt

# 3. Install filtered dependencies
uv pip install -r requirements-filtered.txt
```

The script will:
- Create `requirements-original.txt` (backup)
- Create `requirements-filtered.txt` (safe to install)
- Comment out packages already provided by ROCm
- Show which packages were skipped

#### Why Package Protection Matters

PyPI only hosts CUDA-built PyTorch wheels. If you run `pip install transformers` without protection, pip will see that transformers needs torch and install the CUDA version from PyPI - **breaking your ROCm GPU support**.

The `exclude-dependencies` list in `pyproject.toml` (or the `resolve-dependencies.py` script) prevents this by telling uv/pip to never install these packages as dependencies.

### Troubleshooting

#### ImportError: "importing numpy from source directory"

If you see this error when running code with Ctrl+F5 in VSCode:

```
ImportError: Error importing numpy: you should not try to import numpy from
        its source directory; please exit the numpy source tree, and relaunch
        your python interpreter from there.
```

**Cause**: Your `.venv` was created with a different Python version than the container's `/opt/venv`. This causes binary incompatibility with compiled C extensions (numpy, torch, etc.). The misleading error message actually means the Python versions don't match.

**Diagnostic:**
```bash
# Check Python versions - they MUST match
/opt/venv/bin/python --version    # Container Python (e.g., 3.12.x)
.venv/bin/python --version         # Project venv (should also be 3.12.x)

# Check if .pth bridge points to correct Python version
find .venv -name "_rocm_bridge.pth" -exec cat {} \;
# Should show path matching your Python version (e.g., /opt/venv/lib/python3.12/site-packages)
```

**Fix:**
```bash
# Recreate venv with correct Python version
rm -rf .venv
/opt/venv/bin/python -m venv .venv

# Recreate .pth bridge (the script detects the Python version automatically)
PYTHON_VERSION=$(/opt/venv/bin/python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "/opt/venv/lib/python${PYTHON_VERSION}/site-packages" > .venv/lib/python${PYTHON_VERSION}/site-packages/_rocm_bridge.pth

# Reinstall dependencies
uv sync
```

**Prevention**: The template now automatically detects and prevents Python version mismatches during setup. If you created your project from an older version of the template, consider recreating it or manually applying the fix above.

### Testing GPU Acceleration

Two test scripts are included:

**Quick sanity check (30 seconds):**
```bash
python hello-gpu.py
```

**Comprehensive benchmark (2-3 minutes):**
```bash
python test-gpu.py
```

**What it tests:**
- ✅ GPU availability and device information
- ✅ Basic tensor operations on GPU
- ✅ CPU vs GPU performance comparison (matrix multiplication)
- ✅ Small neural network training (235K params) - shows overhead on integrated GPUs
- ✅ Large neural network training (7.3M params, batch 512) - shows GPU benefits

**Sample output (AMD Radeon 8060S / Strix Halo):**
```
======================================================================
  GPU Availability Check
======================================================================
PyTorch version: 2.9.1+rocm7.2
GPU available: True

✅ GPU Count: 1

GPU 0:
  Name: AMD Radeon 8060S
  Total Memory: 96.00 GB

======================================================================
  CPU vs GPU Performance Comparison
======================================================================
Matrix size: 4096x4096
Iterations: 10

📊 Performance Summary:
   CPU: 0.1784 seconds
   GPU: 0.2831 seconds
   Speedup: 0.63x faster on GPU

⚠️  WARNING: GPU is slower than CPU!
   This may indicate a configuration issue.

======================================================================
  Small Neural Network Training Comparison
======================================================================

📊 Small Model Training Performance:
   CPU: 0.0194 seconds
   GPU: 0.1155 seconds
   Speedup: 0.17x faster on GPU

⚠️  GPU slower for small model (expected on integrated GPUs).
   Small workloads have GPU overhead > actual compute.

======================================================================
  Large Neural Network Training Comparison
======================================================================

📊 Large Model Training Performance:
   Model: 7.3M parameters, batch size 512, 50 iterations
   CPU: 2.4567 seconds
   GPU: 0.8234 seconds
   Speedup: 2.98x faster on GPU

✅ Excellent GPU acceleration! 2.98x speedup for realistic workloads.
```

**Understanding the Results:**

The test suite includes both **small** and **large** workloads to show the full picture:

**Small Model Test (235K params, batch 128):**
- ⚠️ **CPU faster** - GPU overhead dominates for tiny models
- ✅ **GPU works correctly** - This proves GPU operations function
- 💡 **Expected behavior** - Integrated GPUs need larger workloads

**Large Model Test (7.3M params, batch 512):**
- ✅ **GPU faster (2-4x speedup)** - Enough compute to overcome overhead
- ✅ **Realistic workload** - Closer to actual ML model sizes
- 🎯 **Shows GPU benefit** - This is why you have a GPU!

**Why workload size matters:**
1. **GPU overhead is fixed** (~50-100ms for kernel launch, memory setup)
2. **Small model**: Overhead > compute time → CPU wins
3. **Large model**: Compute time >> overhead → GPU wins
4. **Real ML models** (transformers, ResNets) are even larger → GPU wins big

**When GPU acceleration helps on integrated GPUs:**
- Models with 5M+ parameters (most modern ML models)
- Batch sizes 256+ samples
- Large images 512x512+ resolution
- Long training runs (hours/days)
- Inference on large models (LLMs, diffusion)

The test validates your ROCm setup is working correctly and shows GPU benefits appear at realistic model sizes.

**Quick verification:**
```bash
# Check GPU is visible (amd-smi preferred, rocm-smi still works)
amd-smi

# Quick PyTorch GPU test
python hello-gpu.py
```

### IDE Selection

You can configure for VSCode, JetBrains, or both:

```bash
# Interactive selection
./setup-project.sh

# Command-line selection
./setup-project.sh --ide vscode
./setup-project.sh --ide jetbrains
./setup-project.sh --ide both
```

#### JetBrains Setup (PyCharm/IntelliJ IDEA)

1. **Open Project**:
   - PyCharm Professional / IntelliJ IDEA: File → Open → Select project directory → Trust project
   - JetBrains Gateway: New Connection → Docker → Select devcontainer

2. **Configure Python Interpreter** (Required Manual Step):
   1. Open **Project Structure**: File → Project Structure (or `Ctrl+Alt+Shift+S`)
   2. Go to **Project** under Project Settings
   3. Click the **SDK** dropdown → **Add SDK** → **Add Python Interpreter**
   4. In the "Add Python Interpreter" dialog:
      - **Location**: Local Machine
      - **Environment**: Select existing
      - **Type**: uv
      - **Path to uv**: `/opt/venv/bin/uv`
      - **Environment**: Select `Python 3.12 (/workspaces/PROJECT_NAME/.venv)`
   5. Click **OK** to confirm

3. **Source Roots and Excludes** (Pre-configured):
   - The `setup-project.sh` script pre-configures `.idea/` with:
     - `src/` as Sources Root
     - `tests/` as Test Sources Root
     - `.venv/`, `models/`, `datasets/`, `.cache/` as Excluded
   - Ruff linter/formatter enabled by default

4. **Verify GPU Access**:
   - Open terminal in IDE
   - Run: `amd-smi` or `rocm-smi`
   - Run: `python -c "import torch; print(torch.cuda.is_available())"`

**Known Limitations:**
- Python interpreter cannot be auto-configured (JetBrains limitation tracked as [IJPL-174150](https://youtrack.jetbrains.com/issue/IJPL-174150))
- Backend startup: 30-60 seconds initial startup
- First indexing: 2-5 minutes (faster on subsequent opens)

### Data Directories

The template creates these directories in your project folder:

- `./models/` - Trained models and checkpoints
- `./datasets/` - Training and evaluation data
- `./.cache/` - HuggingFace and PyTorch caches

**How it works:**
- These are regular directories in your project folder
- VSCode bind-mounts the entire workspace, so files are visible from both host and container
- Deleting the container does NOT delete these directories (they're on your host filesystem)
- Add to `.gitignore` to avoid committing large files (already configured by default)

**Permissions:** Both your host user and the container user share the same UID (VSCode's `updateRemoteUserUID` feature), so read/write access works seamlessly from either environment.

### External Data Access

The devcontainer automatically mounts your host's `~/data` directory at `/data` inside the container, allowing you to access datasets and files stored outside the project without copying them.

**Use cases:**
```bash
# Inside container
ls /data                              # Browse host ~/data
cp /data/large-dataset.tar.gz ./datasets/  # Copy into project
python train.py --data-path /data/training-set  # Reference directly
```

**Benefits:**
- No data duplication for large datasets
- Share data across multiple ML projects
- Keep proprietary data outside version control
- Access centrally-stored pre-trained models

**Note:** The mount is read-write, so changes made to `/data` inside the container will be reflected on the host.

### Claude Code Integration

The devcontainer includes Claude Code CLI with Google Cloud Vertex AI authentication.

**Setup (required for Claude Code):**

1. Set environment variables on your host:
```bash
# Add to ~/.bashrc or ~/.zshrc
export ANTHROPIC_VERTEX_PROJECT_ID="your-gcp-project-id"
export ANTHROPIC_VERTEX_REGION="us-east5"
export CLAUDE_CODE_USE_VERTEX="true"
```

2. Ensure Google Cloud credentials are configured:
```bash
# On host machine
gcloud auth application-default login
```

**Usage inside container:**
```bash
# Claude Code is available inside the devcontainer
claude --help

# Your gcloud credentials are automatically mounted (read-only)
# Environment variables are passed from host to container
```

**Technical details:**
- Feature: `ghcr.io/anthropics/devcontainer-features/claude-code:1`
- Credentials mount: `~/.config/gcloud` → `/home/stpousty-devcontainer/.config/gcloud` (read-only)
- Environment variables: `ANTHROPIC_VERTEX_PROJECT_ID`, `ANTHROPIC_VERTEX_REGION`, `CLAUDE_CODE_USE_VERTEX`

### Cleanup

Stop container:
```bash
./cleanup-script.sh
```

To delete data:
```bash
rm -rf models/* datasets/* .cache/*
```

## ROCm-Specific Configuration

### Environment Variables

The devcontainer sets these ROCm-specific variables:

```json
{
  "HIP_VISIBLE_DEVICES": "0",              // Which GPU to use
  "ROCM_HOME": "/opt/rocm",                // ROCm installation path
  "ROCBLAS_USE_HIPBLASLT": "1",            // Use optimized GEMM backend
  "PYTORCH_CUDA_ALLOC_CONF": "expandable_segments:True"  // Better memory management
}
```

**Note:** ROCm 7.2 natively supports gfx1151 (Strix Halo) and gfx1150 (Strix Point). The `HSA_OVERRIDE_GFX_VERSION` environment variable is no longer needed and has been removed.

### GPU Access

The container needs access to ROCm devices:

```json
"runArgs": [
  "--device=/dev/kfd",          // ROCm compute device
  "--device=/dev/dri",          // GPU direct rendering
  "--group-add=video",          // Video group for GPU access
  "--ipc=host",                 // Shared memory
  "--cap-add=SYS_PTRACE",       // Debugging support
  "--security-opt=seccomp=unconfined"
]
```

### Base Container

Using official AMD ROCm PyTorch container:
```
rocm/pytorch:rocm7.2_ubuntu24.04_py3.12_pytorch_release_2.9.1
```

This is the official production-supported stack for Ryzen AI processors. Verified working on:
- Ryzen AI Max+ 395 (Strix Halo)
- Custom Steam Deck builds

## Troubleshooting

### GPU Not Detected

```bash
# Check GPU is visible to system (amd-smi preferred, rocm-smi still works)
amd-smi

# Check GPU is visible to container
docker run -it --device=/dev/kfd --device=/dev/dri \
    rocm/pytorch:latest amd-smi

# Verify PyTorch can see GPU
python hello-gpu.py

# Run comprehensive GPU test
python test-gpu.py
```

### Permission Errors

The devcontainer creates a user matching your host UID/GID. If you get permission errors:

```bash
# Check ownership
ls -la models/ datasets/

# Fix if needed (inside container)
sudo chown -R $(whoami):$(whoami) /workspaces/my-ml-project
```

### Package Installation Failures

If `uv pip install` fails:

```bash
# 1. Verify filtered file was created
cat requirements-filtered.txt

# 2. Install without filtering (not recommended)
uv pip install -r requirements.txt

# 3. Check for conflicts
pip list | grep torch
```

### ROCm Architecture Issues

ROCm 7.2 natively supports Strix Halo (gfx1151) and Strix Point (gfx1150). If you see architecture warnings:

1. **Verify you're using ROCm 7.2** - older versions may require workarounds
2. **Check host drivers** - ensure ROCm 7.2 drivers are installed on the host
3. **For older ROCm versions** (not recommended):
   ```bash
   export HSA_OVERRIDE_GFX_VERSION=11.0.0
   ```

### Container Won't Start

```bash
# Check Docker daemon
sudo systemctl status docker

# Check logs
docker logs <container-id>

# Rebuild container
# VSCode: Ctrl+Shift+P → "Dev Containers: Rebuild Container"
```

## Complete List of Changes from CUDA Template

This section documents all changes made during the port from CUDA to ROCm, categorized by reason.

### Changes Required by AMD Container Architecture

These changes were necessary due to how AMD builds the ROCm container differently from NVIDIA:

1. **Pre-configured Virtual Environment (`/opt/venv`)**
   - **CUDA**: No venv, packages installed to system Python, runs as root
   - **ROCm**: Pre-configured venv at `/opt/venv` activated by default
   - **Change**: Modified `setup-environment.sh` to fix ownership of `/opt/venv` (line 24)
   - **Reason**: AMD's venv is owned by root; we need user write access for package installs
   - **Files**: `setup-environment.sh`, `devcontainer.json` (python.defaultInterpreterPath)

2. **Python Interpreter Path**
   - **CUDA**: Uses system Python (`/usr/bin/python`)
   - **ROCm**: Uses venv Python (`/opt/venv/bin/python`)
   - **Change**: Set `"python.defaultInterpreterPath": "/opt/venv/bin/python"` in devcontainer.json
   - **Reason**: PyTorch is only installed in the venv, not system-wide
   - **Files**: `devcontainer.json` (line 56)

3. **UV Project Environment Configuration**
   - **CUDA**: Not applicable (no pre-configured venv)
   - **ROCm**: Must tell uv to use `/opt/venv` instead of creating `.venv/`
   - **Change**: Added `"UV_PROJECT_ENVIRONMENT": "/opt/venv"` to containerEnv
   - **Reason**: uv's default behavior creates new `.venv/` which would lack ROCm packages
   - **Files**: `devcontainer.json` (line 40)

4. **Ubuntu 24.04 User Conflict Resolution**
   - **CUDA**: NVIDIA containers have no pre-existing user at UID 1000
   - **ROCm**: Ubuntu 24.04 base has `ubuntu` user at UID 1000
   - **Change**: Added Dockerfile that deletes `ubuntu` user before common-utils runs
   - **Reason**: Workaround for devcontainer UID matching bugs on Ubuntu 24.04
   - **Files**: `Dockerfile`, `devcontainer.json` (build section)

5. **Simplified Permissions Model**
   - **CUDA**: Group-based sharing (creates user at UID 2112, shared group at GID 1000)
   - **ROCm**: Direct UID matching (deletes ubuntu user, lets VSCode match to host UID)
   - **Change**: Removed entire "Permissions Block" from setup-environment.sh
   - **Reason**: Ubuntu user deletion allows VSCode's UID matching to work correctly
   - **Files**: `setup-environment.sh` (removed lines), `Dockerfile`

6. **Package Protection with override-dependencies**
   - **CUDA**: Not needed (NVIDIA packages don't conflict with PyPI)
   - **ROCm**: Critical to prevent PyPI from overwriting ROCm builds
   - **Change**: Auto-generate `[tool.uv] override-dependencies` for all 137 ROCm packages
   - **Reason**: PyPI only has CUDA wheels; installing torch overwrites ROCm version
   - **Files**: `setup-environment.sh` (lines 60-82), `pyproject.toml` (auto-generated)

7. **ROCm-Provided Packages List Generation**
   - **CUDA**: Not applicable
   - **ROCm**: Generate `rocm-provided.txt` from container's constraint file or pip freeze
   - **Change**: Added package extraction logic to setup-environment.sh (lines 27-32)
   - **Reason**: Need to know which packages to protect from overwrite
   - **Files**: `setup-environment.sh`

### Changes for Feature Improvements

These changes add capabilities not present in the original CUDA template:

8. **Modern Package Manager Support (uv)**
   - **CUDA**: Uses pip only
   - **ROCm**: Full uv support with `uv init`, `uv add`, `uv sync`
   - **Change**: Added uv project initialization for standalone projects
   - **Reason**: Modern workflow with lockfiles, faster installs, better dependency resolution
   - **Files**: `setup-environment.sh` (lines 53-83)

9. **Standalone Project Detection**
   - **CUDA**: Always creates requirements.txt
   - **ROCm**: Detects if new project vs external repo
   - **Change**: `.standalone-project` marker file created by setup-project.sh
   - **Reason**: Enable modern uv workflow for new projects while supporting external repos
   - **Files**: `setup-project.sh`, `setup-environment.sh` (line 55)

10. **Multi-IDE Support**
    - **CUDA**: VSCode only
    - **ROCm**: VSCode + JetBrains support
    - **Change**: Added IDE selection to setup-project.sh
    - **Reason**: Support developers using PyCharm or other JetBrains IDEs
    - **Files**: `setup-project.sh`, `devcontainer.json`, `.idea/` directory

11. **Podman Support**
    - **CUDA**: Docker only
    - **ROCm**: Docker or Podman
    - **Change**: Documented Podman compatibility, automatic userns handling
    - **Reason**: Fedora/RHEL users prefer Podman; VSCode handles it automatically
    - **Files**: `README.md`, no code changes needed

12. **Enhanced GPU Testing**
    - **CUDA**: Basic GPU detection test
    - **ROCm**: Comprehensive test with small + large workload comparison
    - **Change**: Updated test-gpu.py with dual workload tests and educational output
    - **Reason**: Show GPU overhead on integrated GPUs and when GPU benefits appear
    - **Files**: `test-gpu.py`

13. **Changed pip freeze to uv pip freeze**
    - **CUDA**: Uses `pip freeze`
    - **ROCm**: Uses `uv pip freeze`
    - **Change**: Modified package extraction in setup-environment.sh (line 31)
    - **Reason**: Consistency with uv usage throughout the project
    - **Files**: `setup-environment.sh`

### Changes for Platform Differences

These changes adapt to ROCm/AMD platform specifics vs CUDA/NVIDIA:

14. **GPU Device Access**
    - **CUDA**: `--gpus=all`
    - **ROCm**: `--device=/dev/kfd --device=/dev/dri --group-add=video`
    - **Change**: Updated runArgs in devcontainer.json
    - **Reason**: ROCm uses different device nodes than NVIDIA
    - **Files**: `devcontainer.json` (lines 17-28)

15. **GPU Environment Variables**
    - **CUDA**: `CUDA_VISIBLE_DEVICES`
    - **ROCm**: `HIP_VISIBLE_DEVICES`
    - **Change**: Replaced CUDA vars with HIP vars in containerEnv
    - **Reason**: ROCm uses HIP runtime instead of CUDA
    - **Files**: `devcontainer.json` (line 32)

16. **Architecture Override** (ROCm 7.1 only - not needed in 7.2)
    - **CUDA**: Not needed (CUDA automatically detects compute capability)
    - **ROCm 7.1**: Required `HSA_OVERRIDE_GFX_VERSION=11.0.0` for Strix Halo
    - **ROCm 7.2**: Not needed - native gfx1151/gfx1150 support
    - **Change**: Removed from containerEnv (was previously added for ROCm 7.1)
    - **Reason**: ROCm 7.2 natively supports Strix Halo/Point architectures
    - **Files**: `devcontainer.json`

17. **GPU Monitoring Tool**
    - **CUDA**: `nvidia-smi`
    - **ROCm**: `amd-smi` (preferred) or `rocm-smi` (legacy, still works)
    - **Change**: All references changed from nvidia-smi to amd-smi
    - **Reason**: Different GPU management tools; amd-smi provides more detailed output
    - **Files**: `README.md`, `setup-environment.sh`, documentation

18. **Base Container Image**
    - **CUDA**: `nvcr.io/nvidia/pytorch:XX.XX-py3`
    - **ROCm**: `rocm/pytorch:rocm7.2_ubuntu24.04_py3.12_pytorch_release_2.9.1`
    - **Change**: Updated Dockerfile base image
    - **Reason**: Different vendors, different registries
    - **Files**: `Dockerfile`

19. **Package Names and Paths**
    - **CUDA**: `nvidia-provided.txt`
    - **ROCm**: `rocm-provided.txt`
    - **Change**: Renamed file and all references
    - **Reason**: Clarity and consistency with platform
    - **Files**: `scripts/resolve-dependencies.py`, `setup-environment.sh`

### Documentation Changes

20. **Hardware Documentation**
    - **CUDA**: NVIDIA GPU focus
    - **ROCm**: Consumer AMD GPU focus (Ryzen AI, Radeon RX)
    - **Change**: Updated all hardware references and prerequisites
    - **Reason**: Different target hardware
    - **Files**: `README.md`

21. **Installation Instructions**
    - **CUDA**: CUDA driver installation
    - **ROCm**: ROCm driver installation with Radeon/Ryzen guide
    - **Change**: Updated prerequisites section
    - **Reason**: Different driver installation process
    - **Files**: `README.md`

22. **Performance Expectations**
    - **CUDA**: GPU always faster (discrete GPU with VRAM)
    - **ROCm**: GPU overhead explained (integrated GPU with shared memory)
    - **Change**: Added section explaining when GPU helps on integrated GPUs
    - **Reason**: Set realistic expectations for consumer AMD hardware
    - **Files**: `README.md`, `test-gpu.py` output

23. **Blog Post Documentation**
    - **CUDA**: Not applicable
    - **ROCm**: Extensive notes-for-blog-post.md documenting journey
    - **Change**: Created comprehensive documentation of porting process
    - **Reason**: Share lessons learned, help others port to ROCm
    - **Files**: `notes-for-blog-post.md`

### Bug Fixes and Workarounds

24. **apt-get Update Error Handling**
    - **CUDA**: Not needed
    - **ROCm**: Added `|| true` to apt-get update
    - **Change**: Modified setup-environment.sh (line 41)
    - **Reason**: AMD container includes unreachable internal repos (expected)
    - **Files**: `setup-environment.sh`

25. **apt-get --no-upgrade Flag**
    - **CUDA**: Uses standard apt-get install
    - **ROCm**: Uses `apt-get install -y --no-upgrade`
    - **Change**: Added --no-upgrade to apt-get commands
    - **Reason**: Prevent accidentally upgrading ROCm packages
    - **Files**: `setup-environment.sh` (line 43)

## Quick Reference: CUDA to ROCm Equivalents

| Feature | CUDA Template | ROCm Template |
|---------|--------------|---------------|
| Base Container | `nvcr.io/nvidia/pytorch` | `rocm/pytorch:rocm7.2_ubuntu24.04_py3.12...` |
| GPU Access | `--gpus=all` | `--device=/dev/kfd --device=/dev/dri` |
| GPU Tool | `nvidia-smi` | `amd-smi` (or `rocm-smi`) |
| GPU Env Var | `CUDA_VISIBLE_DEVICES` | `HIP_VISIBLE_DEVICES` |
| Package List | `nvidia-provided.txt` | `rocm-provided.txt` |
| Python Location | System `/usr/bin/python` | Venv `/opt/venv/bin/python` (Python 3.12) |
| Package Install | Direct to system | Inside `/opt/venv` |
| Permissions | Group-based (UID 2112 + shared GID) | Direct UID matching (delete ubuntu user) |
| IDE Support | VSCode only | VSCode + JetBrains |
| Runtime | Docker only | Docker or Podman |
| Package Manager | pip only | pip + uv with project mode |
| Dependency Protection | Not needed | exclude-dependencies for ROCm packages |
| Precision Support | FP16/BF16/FP32 | FP16 (officially validated) |

## Resources

### Official Documentation
- [ROCm 7.2 for Radeon/Ryzen GPUs](https://rocm.docs.amd.com/projects/radeon-ryzen/en/docs-7.2/index.html)
- [ROCm 7.2 Compatibility Matrix](https://rocm.docs.amd.com/projects/radeon-ryzen/en/docs-7.2/docs/compatibility/compatibilityryz/native_linux/native_linux_compatibility.html)
- [ROCm PyTorch Documentation](https://rocm.docs.amd.com/en/latest/how-to/pytorch-install/pytorch-install.html)
- [AMD ROCm Containers](https://hub.docker.com/u/rocm)

### Community
- AMD Developer Discord
- [ROCm GitHub Issues](https://github.com/ROCm/ROCm/issues)

### Related Projects
- [Original CUDA Template](https://github.com/thesteve0/datascience-template-CUDA)

## Contributing

Issues and pull requests welcome! This template is designed to be fork-friendly.

## License

See [LICENSE](LICENSE) file.

## Acknowledgments

- Based on [datascience-template-CUDA](https://github.com/thesteve0/datascience-template-CUDA)
- Tested on AMD Ryzen AI Max+ 395 (Strix Halo)
- ROCm PyTorch containers provided by AMD