#!/bin/bash
# Run this script ON THE HOST MACHINE (not in devcontainer)
# This rebuilds the OCR tool image with templates baked in

set -e

VERSION="v0.2.0"
REGISTRY="ghcr.io/thesteve0"

echo "========================================="
echo "Rebuilding OCR Tool with Templates"
echo "========================================="
echo ""

# Verify we're in the right directory
if [ ! -f "services/ocr-tool/Dockerfile" ]; then
    echo "❌ Error: Run this from the stardew-vision repository root"
    exit 1
fi

# Verify templates exist
if [ ! -d "datasets/assets/templates" ]; then
    echo "❌ Error: datasets/assets/templates directory not found"
    exit 1
fi

echo "✅ Templates directory found:"
ls -lh datasets/assets/templates/

echo ""
echo "Building OCR tool image..."
docker build -f services/ocr-tool/Dockerfile -t ${REGISTRY}/stardew-ocr-tool:${VERSION} .

echo ""
echo "Tagging as latest..."
docker tag ${REGISTRY}/stardew-ocr-tool:${VERSION} ${REGISTRY}/stardew-ocr-tool:latest

echo ""
echo "✅ Build complete!"
echo ""
echo "Image: ${REGISTRY}/stardew-ocr-tool:${VERSION}"
echo "Size: $(docker images ${REGISTRY}/stardew-ocr-tool:${VERSION} --format '{{.Size}}')"
echo ""
echo "========================================="
echo "Next: Push to Registry"
echo "========================================="
echo ""
echo "1. Login to GitHub Container Registry:"
echo "   docker login ghcr.io"
echo ""
echo "2. Push the image:"
echo "   docker push ${REGISTRY}/stardew-ocr-tool:${VERSION}"
echo "   docker push ${REGISTRY}/stardew-ocr-tool:latest"
echo ""
echo "3. Verify templates are in the image:"
echo "   docker run --rm ${REGISTRY}/stardew-ocr-tool:${VERSION} ls -la /app/datasets/assets/templates/"
echo ""
