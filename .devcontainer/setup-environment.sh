#!/bin/bash
set -e

echo "Setting up stardew-vision ROCm PyTorch ML environment..."

# Note: No permissions block needed for workspace files!
# By deleting the ubuntu user in the Dockerfile, common-utils creates our user
# with UID/GID that matches the host (1000:1000), giving automatic permission alignment.
# This is simpler than the CUDA template's group-sharing approach.

WORKSPACE_DIR="/workspaces/stardew-vision"

# Fix ownership of AMD's pre-configured venv
# The base container has a venv at /opt/venv owned by root. We need to make it
# writable by the devcontainer user so they can install packages without sudo.
#
# SECURITY NOTE: This devcontainer is designed for DEVELOPMENT ONLY.
# The user has passwordless sudo access (standard for devcontainers) for convenience.
# DO NOT use this configuration for production deployments - production containers should:
#   - Run as non-root user without sudo access
#   - Have read-only filesystems where possible
#   - Follow principle of least privilege
echo "Configuring Python virtual environment permissions..."
sudo chown -R $(whoami):$(whoami) /opt/venv

# Generate rocm-provided.txt
echo "Extracting ROCm-provided packages..."
if [ -f /etc/pip/constraint.txt ]; then
    grep -E "==" /etc/pip/constraint.txt | sort > ${WORKSPACE_DIR}/rocm-provided.txt
else
    uv pip freeze > ${WORKSPACE_DIR}/rocm-provided.txt
fi

# Update system packages
# Note: The ROCm container includes AMD internal repos (compute-artifactory.amd.com)
# that are unreachable outside AMD's network. This is expected and won't affect
# functionality. We preserve the repo files for documentation purposes.
# --allow-releaseinfo-change: Handles repos with updated release info
# --no-upgrade: Only install packages if not already present (preserves ROCm versions)
echo "Updating system packages (AMD internal repos may show errors - this is expected)..."
sudo apt-get update --allow-releaseinfo-change 2>&1 || true

sudo apt-get install -y --no-upgrade \
    git curl wget build-essential \
    && sudo rm -rf /var/lib/apt/lists/*

# Install development tools
# Note: AMD's ROCm container already includes uv package manager and uses a
# pre-configured venv at /opt/venv. After fixing venv ownership above,
# pip/uv install works without sudo.
# Ruff replaces black (formatter) + flake8 (linter) with a single fast tool
uv pip install --no-cache-dir ruff pre-commit

# Initialize uv project for standalone mode
# The .standalone-project marker is created by setup-project.sh for new projects
if [ -f "${WORKSPACE_DIR}/.standalone-project" ]; then
    echo "Initializing uv project for standalone mode..."
    cd ${WORKSPACE_DIR}

    # Detect /opt/venv Python version for consistency
    CONTAINER_PYTHON_VERSION=$(/opt/venv/bin/python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    echo "Container Python version: $CONTAINER_PYTHON_VERSION"

    # Create venv from /opt/venv's Python for version consistency
    if [ ! -d ".venv" ]; then
        echo "Creating project virtual environment with Python $CONTAINER_PYTHON_VERSION..."
        /opt/venv/bin/python -m venv .venv

        # CRITICAL: Verify the venv uses the same Python version
        VENV_PYTHON_VERSION=$(.venv/bin/python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")

        if [ "$VENV_PYTHON_VERSION" != "$CONTAINER_PYTHON_VERSION" ]; then
            echo "ERROR: venv Python version mismatch!"
            echo "  Container /opt/venv: Python $CONTAINER_PYTHON_VERSION"
            echo "  Created .venv: Python $VENV_PYTHON_VERSION"
            echo "  This will cause binary incompatibility with ROCm packages."
            echo "  Please report this issue at: https://github.com/thesteve0/datascience-template-ROCm/issues"
            exit 1
        fi

        echo "✓ Created .venv with Python $VENV_PYTHON_VERSION"
    fi

    # Create .pth bridge to make ROCm packages accessible
    VENV_SITE_PACKAGES=$(find .venv/lib -type d -name "site-packages" | head -n 1)
    CONTAINER_SITE_PACKAGES="/opt/venv/lib/python${CONTAINER_PYTHON_VERSION}/site-packages"

    if [ -n "$VENV_SITE_PACKAGES" ]; then
        PTH_FILE="$VENV_SITE_PACKAGES/_rocm_bridge.pth"
        echo "$CONTAINER_SITE_PACKAGES" > "$PTH_FILE"
        echo "✓ Created .pth bridge: $VENV_SITE_PACKAGES/_rocm_bridge.pth -> $CONTAINER_SITE_PACKAGES"
    else
        echo "ERROR: Could not find site-packages in .venv"
        exit 1
    fi

    # Initialize project
    if [ ! -f "pyproject.toml" ]; then
        uv init --no-readme
    fi

    # CRITICAL: Generate exclusion list BEFORE any uv add/sync commands
    # This prevents uv from installing PyTorch/numpy/etc from PyPI
    # We use pip to install tomli/tomli-w to avoid triggering a uv sync
    echo "Installing TOML tools (via pip to avoid premature sync)..."
    .venv/bin/pip install --quiet tomli tomli-w

    echo "Generating ROCm package exclusion list..."
    .venv/bin/python << PYEOF
import json
from pathlib import Path
import tomli
import tomli_w

site_packages = Path('/opt/venv/lib/python${CONTAINER_PYTHON_VERSION}/site-packages')
packages = {d.name.split('-')[0].replace('_', '-').lower()
            for d in site_packages.glob('*.dist-info')}

# Read existing pyproject.toml and add exclude-dependencies
with open('pyproject.toml', 'rb') as f:
    config = tomli.load(f)

if 'tool' not in config:
    config['tool'] = {}
if 'uv' not in config['tool']:
    config['tool']['uv'] = {}

config['tool']['uv']['exclude-dependencies'] = sorted(packages)

# Ensure tomli, tomli-w, and ruff are in dependencies if not already
deps = config.get('project', {}).get('dependencies', [])
dep_names = [d.split('>=')[0].split('==')[0].lower() for d in deps]
if 'tomli' not in dep_names:
    deps.append('tomli>=2.0.0')
if 'tomli-w' not in dep_names:
    deps.append('tomli-w>=1.0.0')
if 'ruff' not in dep_names:
    deps.append('ruff>=0.4.0')
if 'project' not in config:
    config['project'] = {}
config['project']['dependencies'] = deps

with open('pyproject.toml', 'wb') as f:
    tomli_w.dump(config, f)

print(f"✓ Protected {len(packages)} ROCm packages from overwrite")
PYEOF

    # Now safe to run uv sync - exclusion list is in place
    echo "Syncing project dependencies..."
    uv sync

    # Verify ROCm packages accessible
    echo "Verifying ROCm package access..."
    if .venv/bin/python -c "import torch" 2>/dev/null; then
        TORCH_VERSION=$(.venv/bin/python -c "import torch; print(torch.__version__)")
        echo "✓ torch $TORCH_VERSION accessible from /opt/venv"
    else
        echo "⚠ Warning: Could not import torch"
    fi

    echo "✓ uv project initialized with ROCm protection"
fi

# Install Claude CLI to user directory
if ! command -v claude &> /dev/null; then
    echo "Installing Claude CLI..."
    curl -fsSL https://claude.ai/install.sh | bash
    echo "✓ Claude CLI installed to ~/.local/bin/claude"
else
    CLAUDE_VERSION=$(claude --version 2>/dev/null || echo "unknown")
    echo "✓ Claude CLI already installed: $CLAUDE_VERSION"
fi

# Configure git identity
echo "Configuring git identity..."
git config --global user.name "Steven Pousty"
git config --global user.email "steve.pousty@gmail.com"
git config --global init.defaultBranch main

# Verify ROCm installation
echo ""
echo "Verifying ROCm installation..."
if command -v amd-smi &> /dev/null; then
    echo "AMD SMI found. GPU status:"
    amd-smi || echo "Warning: amd-smi failed (this is normal if no GPU is available)"
elif command -v rocm-smi &> /dev/null; then
    echo "ROCm SMI found (note: amd-smi is preferred). GPU status:"
    rocm-smi || echo "Warning: rocm-smi failed (this is normal if no GPU is available)"
else
    echo "Warning: Neither amd-smi nor rocm-smi found in PATH"
fi

echo ""
echo "Setup complete!"
echo "Store models in ./models/ and datasets in ./datasets/ - they persist across container rebuilds"