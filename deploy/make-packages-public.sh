#!/bin/bash
set -e

echo "========================================="
echo " Make Stardew Vision Packages Public"
echo "========================================="
echo ""

PACKAGES=(
    "stardew-coordinator"
    "stardew-pierres-buying-tool"
    "stardew-tts-tool"
)

echo "Checking package status..."
echo ""

for package in "${PACKAGES[@]}"; do
    # Check if package exists
    if gh api "user/packages/container/${package}" > /dev/null 2>&1; then
        # Get current visibility
        VISIBILITY=$(gh api "user/packages/container/${package}" --jq '.visibility')

        if [ "$VISIBILITY" = "public" ]; then
            echo "✓ ${package}: Already public"
        else
            echo "⚠ ${package}: Private - needs manual update"
            echo "  → https://github.com/users/thesteve0/packages/container/${package}/settings"
        fi
    else
        echo "○ ${package}: Does not exist yet (will be created on first push)"
    fi
done

echo ""
echo "========================================="
echo " How to Make Packages Public"
echo "========================================="
echo ""
echo "GitHub Container Registry packages must be made public via the web UI."
echo "The GitHub API does not support this operation for container packages."
echo ""
echo "For each package above that shows as 'Private', visit the settings URL and:"
echo "  1. Scroll to 'Danger Zone'"
echo "  2. Click 'Change visibility'"
echo "  3. Select 'Public'"
echo "  4. Confirm the change"
echo ""
echo "All packages: https://github.com/thesteve0?tab=packages"
echo ""
