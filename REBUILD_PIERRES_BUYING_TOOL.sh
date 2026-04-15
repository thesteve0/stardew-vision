#!/bin/bash
# Run this script ON THE HOST MACHINE (not in devcontainer)
# This rebuilds the Pierre's Buying Tool image with templates baked in

set -e

VERSION="v0.2.0"
REGISTRY="ghcr.io/thesteve0"

echo "========================================="
echo "Rebuilding Pierre's Buying Tool"
echo "========================================="
echo ""

# Verify we're in the right directory
if [ ! -f "services/pierres_buying_tool/Dockerfile" ]; then
    echo "❌ Error: Run this from the stardew-vision repository root"
    exit 1
fi

# Verify templates exist
if [ ! -d "services/pierres_buying_tool/assets/templates" ]; then
    echo "❌ Error: services/pierres_buying_tool/assets/templates directory not found"
    exit 1
fi

echo "✅ Templates directory found:"
ls -lh services/pierres_buying_tool/assets/templates/

echo ""
echo "Building Pierre's Buying Tool image..."
docker build -f services/pierres_buying_tool/Dockerfile -t ${REGISTRY}/stardew-pierres-buying-tool:${VERSION} .

echo ""
echo "Tagging as latest..."
docker tag ${REGISTRY}/stardew-pierres-buying-tool:${VERSION} ${REGISTRY}/stardew-pierres-buying-tool:latest

echo ""
echo "✅ Build complete!"
echo ""
echo "Image: ${REGISTRY}/stardew-pierres-buying-tool:${VERSION}"
echo "Size: $(docker images ${REGISTRY}/stardew-pierres-buying-tool:${VERSION} --format '{{.Size}}')"
echo ""
echo "========================================="
echo "Next: Push to Registry"
echo "========================================="
echo ""
echo "1. Login to GitHub Container Registry:"
echo "   docker login ghcr.io"
echo ""
echo "2. Push the image:"
echo "   docker push ${REGISTRY}/stardew-pierres-buying-tool:${VERSION}"
echo "   docker push ${REGISTRY}/stardew-pierres-buying-tool:latest"
echo ""
echo "3. Verify templates are in the image:"
echo "   docker run --rm ${REGISTRY}/stardew-pierres-buying-tool:${VERSION} ls -la /app/assets/templates/"
echo ""
