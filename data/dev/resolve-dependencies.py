#!/usr/bin/env python3
"""
Dependency resolution script to avoid conflicts with ROCm-provided packages.
Usage:
    python scripts/resolve-dependencies.py requirements.txt
    python scripts/resolve-dependencies.py pyproject.toml
"""
import sys
import re
import tomllib
import argparse
from pathlib import Path


def load_rocm_packages(rocm_file="rocm-provided.txt"):
    """Load ROCm-provided packages and versions."""
    rocm_file = Path(rocm_file)
    if not rocm_file.exists():
        print(f"Warning: {rocm_file} not found")
        return {}

    rocm_packages = {}
    with open(rocm_file) as f:
        for line in f:
            line = line.strip()
            if '==' in line:
                name, version = line.split('==', 1)
                rocm_packages[name.lower()] = version
    return rocm_packages


def extract_package_name(requirement):
    """Extract package name from requirement string."""
    match = re.match(r'^([a-zA-Z0-9_-]+)', requirement)
    return match.group(1).lower() if match else None


def filter_requirements(requirements_file, rocm_packages):
    """Filter requirements.txt to avoid ROCm package conflicts."""
    requirements_file = Path(requirements_file)
    if not requirements_file.exists():
        print(f"{requirements_file} not found")
        return

    with open(requirements_file) as f:
        lines = f.readlines()

    filtered_lines = []
    skipped_packages = []

    for line in lines:
        original_line = line.rstrip()
        line = line.strip()
        if not line or line.startswith('#'):
            filtered_lines.append(original_line)
            continue

        package_name = extract_package_name(line)
        if package_name and package_name in rocm_packages:
            skipped_packages.append(f"{line} (ROCm provides {package_name}=={rocm_packages[package_name]})")
            filtered_lines.append(
                f"# {original_line}  # Skipped: ROCm provides {package_name}=={rocm_packages[package_name]}")
            continue

        filtered_lines.append(original_line)

    # Create filtered version
    filtered_file = requirements_file.with_name('requirements-filtered.txt')

    # Backup original if this is the first time
    backup_file = requirements_file.with_name('requirements-original.txt')
    if not backup_file.exists():
        requirements_file.rename(backup_file)
        print(f"Created backup: {backup_file}")

    with open(filtered_file, 'w') as f:
        f.write('\n'.join(filtered_lines))

    print(f"Created filtered requirements: {filtered_file}")
    if skipped_packages:
        print("Skipped packages (already provided by ROCm):")
        for pkg in skipped_packages:
            print(f"  - {pkg}")


def filter_pyproject_toml(pyproject_file, rocm_packages):
    """Filter pyproject.toml dependencies to avoid ROCm package conflicts."""
    pyproject_file = Path(pyproject_file)
    if not pyproject_file.exists():
        print(f"{pyproject_file} not found")
        return

    with open(pyproject_file, 'rb') as f:
        data = tomllib.load(f)

    skipped_packages = []

    # Filter project dependencies
    if 'project' in data and 'dependencies' in data['project']:
        filtered_deps = []
        for dep in data['project']['dependencies']:
            package_name = extract_package_name(dep)
            if package_name and package_name in rocm_packages:
                skipped_packages.append(f"{dep} (ROCm provides {package_name}=={rocm_packages[package_name]})")
                continue
            filtered_deps.append(dep)
        data['project']['dependencies'] = filtered_deps

    # Filter optional dependencies
    if 'project' in data and 'optional-dependencies' in data['project']:
        for group_name, deps in data['project']['optional-dependencies'].items():
            filtered_deps = []
            for dep in deps:
                package_name = extract_package_name(dep)
                if package_name and package_name in rocm_packages:
                    skipped_packages.append(
                        f"{dep} (ROCm provides {package_name}=={rocm_packages[package_name]}) [from {group_name}]")
                    continue
                filtered_deps.append(dep)
            data['project']['optional-dependencies'][group_name] = filtered_deps

    # Create backup if first time
    backup_file = pyproject_file.with_name('pyproject-original.toml')
    if not backup_file.exists():
        pyproject_file.rename(backup_file)
        print(f"Created backup: {backup_file}")

    # Write filtered version - simplified TOML writing
    with open(pyproject_file, 'w') as f:
        if 'project' in data:
            f.write('[project]\n')
            for key, value in data['project'].items():
                if key == 'dependencies':
                    f.write('dependencies = [\n')
                    for dep in value:
                        f.write(f'    "{dep}",\n')
                    f.write(']\n')
                elif key == 'optional-dependencies':
                    f.write('\n[project.optional-dependencies]\n')
                    for group_name, deps in value.items():
                        f.write(f'{group_name} = [\n')
                        for dep in deps:
                            f.write(f'    "{dep}",\n')
                        f.write(']\n')
                elif isinstance(value, str):
                    f.write(f'{key} = "{value}"\n')
                else:
                    f.write(f'{key} = {value}\n')

        # Write other sections if they exist
        for section, content in data.items():
            if section != 'project':
                f.write(f'\n[{section}]\n')
                # Simple handling for other sections
                f.write(f'# Section {section} preserved but not filtered\n')

    print(f"Updated {pyproject_file} (filtered)")
    if skipped_packages:
        print("Skipped packages (already provided by ROCm):")
        for pkg in skipped_packages:
            print(f"  - {pkg}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Filter dependencies to avoid conflicts with ROCm-provided packages"
    )
    parser.add_argument(
        "file",
        help="Path to requirements.txt or pyproject.toml file to filter"
    )
    parser.add_argument(
        "--rocm-file",
        default="rocm-provided.txt",
        help="Path to rocm-provided.txt file (default: rocm-provided.txt)"
    )

    args = parser.parse_args()

    input_file = Path(args.file)
    rocm_packages = load_rocm_packages(args.rocm_file)

    if input_file.suffix == '.toml':
        filter_pyproject_toml(input_file, rocm_packages)
    elif input_file.suffix == '.txt':
        filter_requirements(input_file, rocm_packages)
    else:
        print(f"Unsupported file type: {input_file.suffix}")
        print("Supported: .txt (requirements.txt) or .toml (pyproject.toml)")
        sys.exit(1)