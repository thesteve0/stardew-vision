#!/bin/bash
set -e

# ==============================================================================
# ROCm Data Science DevContainer Setup Script
# Ported from: https://github.com/thesteve0/datascience-template-CUDA
# ==============================================================================

# Parse arguments
CLONE_REPO=""
IDE_CHOICE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --clone-repo)
            CLONE_REPO="$2"
            shift 2
            ;;
        --ide)
            IDE_CHOICE="$2"
            shift 2
            ;;
        *)
            echo "Usage: $0 [--clone-repo <git-url>] [--ide <vscode|jetbrains|both>]"
            exit 1
            ;;
    esac
done

# ==============================================================================
# --- Configuration ---
# All project constants are defined here. Edit these values to change the setup.
# ==============================================================================

# Set the project name equal to the directory name
PROJECT_NAME=$(basename "$PWD")

# Automatically get Git identity from your global .gitconfig
GIT_NAME=$(git config user.name 2>/dev/null || echo "Your Name")
GIT_EMAIL=$(git config user.email 2>/dev/null || echo "your.email@example.com")

# Define the username and user ID for inside the container.
# Strategy: We delete the 'ubuntu' user (UID 1000) in the Dockerfile, then create
# our user with UID 2112 via common-utils. VSCode's automatic UID matching will
# then adjust it to match your host UID, giving automatic permission alignment.
DEV_USER=$(whoami)-devcontainer
DEV_UID=2112

# ==============================================================================
# --- IDE Selection ---
# ==============================================================================

if [ -z "$IDE_CHOICE" ]; then
    echo "Which IDE(s) do you want to configure?"
    echo "1) VSCode only"
    echo "2) JetBrains only"
    echo "3) Both VSCode and JetBrains"
    read -p "Enter choice [1-3]: " ide_num

    case $ide_num in
        1) IDE_CHOICE="vscode" ;;
        2) IDE_CHOICE="jetbrains" ;;
        3) IDE_CHOICE="both" ;;
        *)
            echo "Invalid choice. Defaulting to VSCode."
            IDE_CHOICE="vscode"
            ;;
    esac
fi

echo "IDE configuration: $IDE_CHOICE"

# ==============================================================================
# --- Script Logic ---
# ==============================================================================

echo "Setting up $PROJECT_NAME ROCm development environment..."

# Replace template placeholders in all relevant files
find . -name "*.json" -o -name "*.sh" -o -name "*.py" 2>/dev/null | xargs -r sed -i \
    -e "s/stardew-vision/$PROJECT_NAME/g" \
    -e "s/Steven Pousty/$GIT_NAME/g" \
    -e "s/steve.pousty@gmail.com/$GIT_EMAIL/g" \
    -e "s/stpousty-devcontainer/$DEV_USER/g" \
    -e "s/2112/$DEV_UID/g"

# Create base directories
mkdir -p scripts

# Setup devcontainer directory (shared by both VSCode and JetBrains)
echo "Setting up devcontainer configuration..."
mkdir -p .devcontainer

# Move devcontainer files into .devcontainer/ directory
# These files are shared by both VSCode and JetBrains
if [ -f "devcontainer.json" ]; then
    mv devcontainer.json .devcontainer/
fi
if [ -f "Dockerfile" ]; then
    mv Dockerfile .devcontainer/
fi
if [ -f "setup-environment.sh" ]; then
    mv setup-environment.sh .devcontainer/
    chmod 755 .devcontainer/setup-environment.sh
fi

# IDE-specific setup
if [ "$IDE_CHOICE" = "vscode" ]; then
    echo "✓ VSCode devcontainer configured"
elif [ "$IDE_CHOICE" = "jetbrains" ] || [ "$IDE_CHOICE" = "both" ]; then
    echo "✓ JetBrains devcontainer configured"

    # Create .idea/ with proper Python module configuration
    # Without this, JetBrains defaults to JAVA_MODULE and won't allow Python interpreter setup
    echo "  Creating .idea/ with Python module configuration..."

    # Remove any existing .idea/ from template to start fresh
    rm -rf .idea
    mkdir -p .idea

    # Create module file with PYTHON_MODULE type
    cat > ".idea/${PROJECT_NAME}.iml" << IDEA_IML_EOF
<?xml version="1.0" encoding="UTF-8"?>
<module type="PYTHON_MODULE" version="4">
  <component name="NewModuleRootManager">
    <content url="file://\$MODULE_DIR\$">
      <sourceFolder url="file://\$MODULE_DIR\$/src" isTestSource="false" />
      <sourceFolder url="file://\$MODULE_DIR\$/tests" isTestSource="true" />
      <excludeFolder url="file://\$MODULE_DIR\$/.venv" />
      <excludeFolder url="file://\$MODULE_DIR\$/.cache" />
      <excludeFolder url="file://\$MODULE_DIR\$/models" />
      <excludeFolder url="file://\$MODULE_DIR\$/datasets" />
    </content>
    <orderEntry type="jdk" jdkName="Python 3.12 (${PROJECT_NAME})" jdkType="Python SDK" />
    <orderEntry type="sourceFolder" forTests="false" />
  </component>
</module>
IDEA_IML_EOF

    # Create misc.xml with Python SDK reference
    cat > .idea/misc.xml << 'IDEA_MISC_EOF'
<?xml version="1.0" encoding="UTF-8"?>
<project version="4">
  <component name="ProjectRootManager" version="2" project-jdk-name="Python 3.12 (${PROJECT_NAME})" project-jdk-type="Python SDK" />
</project>
IDEA_MISC_EOF
    # Replace placeholder with actual project name
    sed -i "s/\${PROJECT_NAME}/${PROJECT_NAME}/g" .idea/misc.xml

    # Create modules.xml
    cat > .idea/modules.xml << IDEA_MODULES_EOF
<?xml version="1.0" encoding="UTF-8"?>
<project version="4">
  <component name="ProjectModuleManager">
    <modules>
      <module fileurl="file://\$PROJECT_DIR\$/.idea/${PROJECT_NAME}.iml" filepath="\$PROJECT_DIR\$/.idea/${PROJECT_NAME}.iml" />
    </modules>
  </component>
</project>
IDEA_MODULES_EOF

    # Create vcs.xml for git
    cat > .idea/vcs.xml << 'IDEA_VCS_EOF'
<?xml version="1.0" encoding="UTF-8"?>
<project version="4">
  <component name="VcsDirectoryMappings">
    <mapping directory="" vcs="Git" />
  </component>
</project>
IDEA_VCS_EOF

    # Create .gitignore for .idea/
    cat > .idea/.gitignore << 'IDEA_GITIGNORE_EOF'
# User-specific settings
workspace.xml
tasks.xml
usage.statistics.xml
dictionaries
shelf

# AWS/Cloud credentials (do not commit)
aws.xml

# Datasource local storage
dataSources/
dataSources.local.xml

# IDE-specific cache
caches/
IDEA_GITIGNORE_EOF

    # Create ruff.xml to enable Ruff linter/formatter by default
    cat > .idea/ruff.xml << 'IDEA_RUFF_EOF'
<?xml version="1.0" encoding="UTF-8"?>
<project version="4">
  <component name="RuffConfigService">
    <option name="enableRuff" value="true" />
    <option name="useRuffFormat" value="true" />
    <option name="runRuffOnSave" value="true" />
    <option name="showRuleCode" value="true" />
  </component>
</project>
IDEA_RUFF_EOF

    echo "  ✓ .idea/ configured as Python project"
    echo "  ✓ Ruff linter/formatter enabled by default"
    echo "  Note: You may need to configure the Python interpreter path manually:"
    echo "        /workspaces/${PROJECT_NAME}/.venv/bin/python"

    if [ "$IDE_CHOICE" = "both" ]; then
        echo "✓ VSCode devcontainer also configured"
    fi
fi

# Move resolve-dependencies script
if [ -f "resolve-dependencies.py" ]; then
    mv resolve-dependencies.py scripts/
fi

# Create data directories in project folder
# These are regular directories visible from both host and container
mkdir -p models datasets .cache

# Handle repository modes
if [ -n "$CLONE_REPO" ]; then
    # External repo mode
    CLONED_REPO_NAME=$(basename "$CLONE_REPO" .git)
    echo "External repo mode: integrating $CLONED_REPO_NAME"

    # Check for naming conflicts
    if [ -d "$CLONED_REPO_NAME" ]; then
        echo "Error: Directory $CLONED_REPO_NAME already exists"
        exit 1
    fi

    # Update PYTHONPATH in devcontainer.json for external repo (if VSCode)
    if [ -f ".devcontainer/devcontainer.json" ]; then
        sed -i "s|\"PYTHONPATH\": \"/workspaces/$PROJECT_NAME/src\"|\"PYTHONPATH\": \"/workspaces/$PROJECT_NAME/$CLONED_REPO_NAME\"|g" .devcontainer/devcontainer.json
    fi

    # Clone repo
    git clone "$CLONE_REPO" "$CLONED_REPO_NAME"

    # Add to .gitignore
    echo "$CLONED_REPO_NAME/" >> .gitignore

    echo "Setup complete! External repo cloned to ./$CLONED_REPO_NAME"
    echo "PYTHONPATH set to /workspaces/$PROJECT_NAME/$CLONED_REPO_NAME"

else
    # Standalone mode
    echo "Standalone mode: creating project structure"

    # Create additional directories for standalone
    mkdir -p src/${PROJECT_NAME} configs tests

    # Create Python structure
    touch src/__init__.py src/${PROJECT_NAME}/__init__.py tests/__init__.py

    # Create marker file to indicate standalone project
    # This will be used by setup-environment.sh to initialize uv project in the container
    touch .standalone-project
fi

# ==============================================================================
# --- Template Cleanup and Documentation Organization ---
# ==============================================================================

echo ""
echo "Setting up project documentation..."

# 1. Create template_docs directory
mkdir -p template_docs

# 2. Move ONLY README.md and CLAUDE.md to template_docs (preserve reference docs)
if [ -f "README.md" ]; then
    mv README.md template_docs/README.md
    echo "✓ Moved README.md to template_docs/"
fi
if [ -f "CLAUDE.md" ]; then
    mv CLAUDE.md template_docs/CLAUDE.md
    echo "✓ Moved CLAUDE.md to template_docs/"
fi

# 3. Remove template development artifacts
# Remove .claude directory (template-specific settings)
if [ -d ".claude" ]; then
    rm -rf .claude
    echo "✓ Removed .claude/ (template development settings)"
fi

# Remove .idea directory (template-specific IDE settings)
# Only remove if VSCode-only mode; JetBrains/both modes create fresh .idea/ earlier in script
if [ "$IDE_CHOICE" = "vscode" ] && [ -d ".idea" ]; then
    rm -rf .idea
    echo "✓ Removed .idea/ (template IDE settings)"
fi

# Remove all other .md files (template development docs)
for mdfile in *.md; do
    if [ -f "$mdfile" ]; then
        rm "$mdfile"
        echo "✓ Removed $mdfile (template development doc)"
    fi
done

# 4. Create template_docs/QUICKSTART.md (quick reference for common tasks)
cat > template_docs/QUICKSTART.md << 'QUICKSTART_EOF'
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
QUICKSTART_EOF

# 5. Create skeleton README.md for user's project
cat > README.md << 'README_EOF'
# [Project Name]

> Replace this with a one-sentence description of what this project does and why it exists.

## Problem Statement

Describe the problem this project solves. What question are you trying to answer? What business need does this address?

## Dataset

- **Data Source**: Where does the data come from? (e.g., public dataset, company database, web scraping)
- **Size**: How much data? (e.g., "10GB of images", "1M text samples")
- **Location**: Where is the data stored? (`./datasets/`, `/data/external-source`, etc.)

If using external data mounted at `/data`, explain how to access it.

## Methodology

Describe your approach:
- What models or algorithms are you using?
- What preprocessing steps are required?
- What are the key experiments or analyses?

## Project Structure

```
project-name/
├── src/              # Source code for models, data processing, utilities
├── configs/          # Configuration files (hyperparameters, paths, etc.)
├── datasets/         # Training and evaluation data
├── models/           # Trained model checkpoints
├── notebooks/        # Jupyter notebooks for exploration and visualization
├── tests/            # Unit and integration tests
└── .cache/           # HuggingFace and PyTorch caches
```

## Setup

This project runs in a ROCm devcontainer. Prerequisites and setup are already complete if you're reading this inside the container.

**First-time setup** (if not already done):
1. Clone this repository
2. Open in VSCode and reopen in container (or use JetBrains Gateway)
3. Wait for container build and environment setup to complete

**Install project dependencies**:
```bash
# Add your dependencies to pyproject.toml dependencies section
# Then run:
uv sync
```

## Usage

### Training
```bash
# Replace with your actual training command
python src/train.py --config configs/training.yaml
```

### Inference
```bash
# Replace with your actual inference command
python src/inference.py --model models/best-model.pth --input data/sample.jpg
```

### Jupyter Notebooks
```bash
# Launch Jupyter (if configured)
jupyter lab
```

## Results

Document your findings here:
- Model performance metrics (accuracy, F1, loss curves, etc.)
- Key insights from data analysis
- Visualizations and plots (consider adding to `results/` directory)
- Links to experiment tracking (MLflow, W&B, etc.)

## Known Issues

List any known limitations, bugs, or areas for improvement.

## Contributing

If this is a team project, describe:
- How to submit changes (PR process, code review requirements)
- Coding standards (linting, formatting, testing requirements)
- Branch naming conventions

## License

Specify your license or "Proprietary" if not open source.

## Acknowledgments

Credit data sources, pre-trained models, papers, or team members.

---

**Template Info**: This project was created from [datascience-template-ROCm](https://github.com/thesteve0/datascience-template-ROCm). For ROCm setup, troubleshooting, or template infrastructure details, see `template_docs/`.
README_EOF

# 6. Create skeleton CLAUDE.md for user's project
cat > CLAUDE.md << 'CLAUDE_EOF'
# CLAUDE.md

This file provides context to Claude Code when working on this project.

## Project Overview

**Purpose**: [One-sentence description of what this project does]

**Problem Domain**: [e.g., "Computer vision for medical imaging", "NLP for customer support", "Time series forecasting for energy demand"]

**Key Technologies**:
- PyTorch (ROCm-accelerated via devcontainer)
- [Add your frameworks: transformers, diffusers, scikit-learn, etc.]
- [Add your tools: Jupyter, MLflow, Ray, etc.]

## Codebase Structure

```
src/
├── data/           # Data loading, preprocessing, augmentation
├── models/         # Model architectures and training logic
├── utils/          # Helper functions, logging, visualization
└── experiments/    # Experiment scripts and configurations
```

**Key files**:
- `src/models/model.py` - Main model architecture
- `configs/base_config.yaml` - Default configuration
- [Add your critical files with brief descriptions]

## Development Workflow

**Common commands**:
```bash
# Training
python src/train.py --config configs/experiment1.yaml

# Evaluation
python src/evaluate.py --checkpoint models/best-model.pth

# Data preprocessing
python src/data/preprocess.py --input datasets/raw --output datasets/processed
```

**Testing**:
```bash
pytest tests/
```

**Linting/Formatting** (if configured):
```bash
black src/
flake8 src/
```

## Architectural Decisions

Document key design choices that Claude should understand:

- **Data loading strategy**: [e.g., "Using PyTorch DataLoader with custom Dataset class", "Streaming large datasets from /data"]
- **Model architecture**: [e.g., "Fine-tuning BERT-base", "Custom CNN with ResNet backbone"]
- **Training approach**: [e.g., "Mixed precision training with gradient accumulation", "Distributed training across 2 GPUs"]
- **Experiment tracking**: [e.g., "MLflow for metrics, model versioning in models/"]

## Important Patterns

**Configuration management**:
[Explain how configs work - YAML files, Hydra, argparse, etc.]

**Model checkpointing**:
[Explain checkpoint naming convention, where they're saved, how to load them]

**Data pipeline**:
[Explain data flow from raw → preprocessed → DataLoader → model]

## Known Issues and Gotchas

- [e.g., "Dataset has class imbalance - must use weighted loss"]
- [e.g., "Large models may OOM on integrated GPU - reduce batch size"]
- [e.g., "Preprocessing requires 32GB RAM - run on host if container OOMs"]

## External Dependencies

- **Data sources**: [Where data comes from, how to refresh it]
- **Pretrained models**: [Which models are downloaded, where cached]
- **APIs/Services**: [Any external services the project calls]

## Testing Strategy

[Describe test coverage, what's tested, what's not]

---

**Note**: This is a ROCm devcontainer project. For ROCm-specific troubleshooting (GPU access, dependency conflicts, Python version issues), see `template_docs/CLAUDE.md`.
CLAUDE_EOF

# 7. Create GETTING_STARTED.md checklist
cat > GETTING_STARTED.md << 'GETTING_STARTED_EOF'
# Welcome to Your ROCm ML Project!

Your devcontainer is ready. Follow this checklist to customize your project:

## Immediate Next Steps

### 1. Customize Documentation

- [ ] **Edit `README.md`**
  - Replace project name and description
  - Fill in Problem Statement, Dataset, Methodology sections
  - Update Setup and Usage commands for your project
  - Document your results as you go

- [ ] **Edit `CLAUDE.md`**
  - Add your project's purpose and problem domain
  - Document your key files and directory structure
  - Add common commands for training, evaluation, etc.
  - Document architectural decisions and important patterns

### 2. Set Up Your Project

- [ ] **Add Dependencies**
  ```bash
  # Edit pyproject.toml to add your packages
  # Then install:
  uv sync
  ```

- [ ] **Verify GPU Access**
  ```bash
  amd-smi                    # Check GPU is visible
  python test-gpu.py         # Run comprehensive GPU test
  ```

- [ ] **Organize Your Code**
  - Move existing code to appropriate directories (`src/`, `configs/`, etc.)
  - Create initial model/data processing scripts
  - Set up any configuration files

### 3. Configure Version Control

- [ ] **Update `.gitignore`**
  - Add any project-specific patterns
  - Verify large files (models, datasets) are ignored

- [ ] **Initial Commit**
  ```bash
  git add .
  git commit -m "Initial project setup from datascience-template-ROCm"
  ```

## Template Documentation Reference

For help with ROCm-specific issues, see `template_docs/`:

- **`template_docs/README.md`** - ROCm setup, dependency management, troubleshooting
- **`template_docs/CLAUDE.md`** - Template architecture, .pth bridge design, Python versioning
- **`template_docs/QUICKSTART.md`** - Common tasks and commands

## Need Help?

**GPU not detected?** See `template_docs/README.md` → "Troubleshooting" → "GPU Not Detected"

**Package installation issues?** See `template_docs/README.md` → "Managing Dependencies"

**Import errors?** See `template_docs/README.md` → "Troubleshooting" → "ImportError"

---

**Delete this file** once you've completed the checklist!
GETTING_STARTED_EOF

echo "✓ Template documentation organized in template_docs/"
echo "✓ Skeleton README.md and CLAUDE.md created"
echo "✓ GETTING_STARTED.md created for first-time setup guidance"

# ==============================================================================
# --- Next Steps ---
# ==============================================================================

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "IDE: $IDE_CHOICE"
echo "Project: $PROJECT_NAME"
echo ""

if [ "$IDE_CHOICE" = "vscode" ] || [ "$IDE_CHOICE" = "both" ]; then
    echo "VSCode Next Steps:"
    echo "  1. Open in VSCode: code ."
    echo "  2. Reopen in Container when prompted"
fi

if [ "$IDE_CHOICE" = "jetbrains" ] || [ "$IDE_CHOICE" = "both" ]; then
    echo ""
    echo "JetBrains Next Steps:"
    echo "  1. Open with JetBrains Gateway or PyCharm"
    echo "  2. Configure devcontainer support"
fi

echo ""
if [ -n "$CLONE_REPO" ]; then
    echo "Dependency Management (External Repo):"
    echo "  Your cloned repo may have requirements.txt or pyproject.toml."
    echo "  If using requirements.txt:"
    echo "    1. In container: python scripts/resolve-dependencies.py requirements.txt"
    echo "    2. In container: uv pip install -r requirements-filtered.txt"
    echo "  If using pyproject.toml:"
    echo "    - In container: uv sync"
else
    echo "Dependency Management (uv Project):"
    echo "  This project uses uv for modern Python dependency management."
    echo "  Add dependencies:"
    echo "    - uv add <package>              # Add a dependency"
    echo "    - uv add --dev <package>        # Add a dev dependency"
    echo "    - uv sync                       # Install all dependencies"
    echo "  Note: ROCm-provided packages (PyTorch, etc.) are already available."
fi

echo ""
echo "Verify GPU Access:"
echo "  - amd-smi  (preferred, more detailed output)"
echo "  - rocm-smi (legacy, still works)"
echo "  - python -c 'import torch; print(torch.cuda.is_available())'"
echo ""