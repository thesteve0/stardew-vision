#!/bin/bash
# Run this script ON THE HOST MACHINE (not in devcontainer)
# Rebuilds all three microservices with OpenShift compatibility fixes

set -e

VERSION="v0.2.0"
REGISTRY="ghcr.io/thesteve0"

echo "========================================="
echo "Rebuilding All Services for OpenShift"
echo "========================================="
echo ""
echo "Fix: Added UV_CACHE_DIR=/tmp/.uv for non-root containers"
echo ""

# Verify we're in the right directory
if [ ! -f "services/coordinator/Dockerfile" ]; then
    echo "❌ Error: Run this from the stardew-vision repository root"
    exit 1
fi

echo "[1/3] Building coordinator..."
docker build -f services/coordinator/Dockerfile -t ${REGISTRY}/stardew-coordinator:${VERSION} .

echo ""
echo "[2/3] Building pierres-buying-tool..."
docker build -f services/pierres_buying_tool/Dockerfile -t ${REGISTRY}/stardew-pierres-buying-tool:${VERSION} .

echo ""
echo "[3/3] Building tts-tool..."
docker build -f services/tts-tool/Dockerfile -t ${REGISTRY}/stardew-tts-tool:${VERSION} .

echo ""
echo "Tagging as latest..."
docker tag ${REGISTRY}/stardew-coordinator:${VERSION} ${REGISTRY}/stardew-coordinator:latest
docker tag ${REGISTRY}/stardew-pierres-buying-tool:${VERSION} ${REGISTRY}/stardew-pierres-buying-tool:latest
docker tag ${REGISTRY}/stardew-tts-tool:${VERSION} ${REGISTRY}/stardew-tts-tool:latest

echo ""
echo "✅ Build complete!"
echo ""
docker images | grep "stardew-"
echo ""
echo "========================================="
echo "Next: Push to Registry"
echo "========================================="
echo ""
echo "1. Login to GitHub Container Registry:"
echo "   docker login ghcr.io"
echo ""
echo "2. Push all images:"
echo "   docker push ${REGISTRY}/stardew-coordinator:${VERSION}"
echo "   docker push ${REGISTRY}/stardew-pierres-buying-tool:${VERSION}"
echo "   docker push ${REGISTRY}/stardew-tts-tool:${VERSION}"
echo "   docker push ${REGISTRY}/stardew-coordinator:latest"
echo "   docker push ${REGISTRY}/stardew-pierres-buying-tool:latest"
echo "   docker push ${REGISTRY}/stardew-tts-tool:latest"
echo ""
echo "3. Return to devcontainer and redeploy:"
echo "   oc rollout restart deployment/coordinator -n stardew-vision"
echo "   oc rollout restart deployment/pierres-buying-tool -n stardew-vision"
echo "   oc rollout restart deployment/tts-tool -n stardew-vision"
echo ""
