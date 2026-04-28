#!/bin/bash
set -e

VERSION=${1:-"v0.1.0"}
REGISTRY="ghcr.io/thesteve0"

cd "$(dirname "$0")/.."

echo "========================================="
echo " Stardew Vision Container Image Builder"
echo "========================================="
echo ""
echo "⚠️  IMPORTANT: This script must be run on the HOST machine,"
echo "   NOT inside the devcontainer!"
echo ""
echo "   If you're in the devcontainer, exit first and run this"
echo "   script from your host terminal."
echo ""
read -p "Press ENTER to continue or Ctrl+C to exit..."
echo ""

echo "Building Stardew Vision container images..."
echo "Version: ${VERSION}"
echo "Registry: ${REGISTRY}"
echo ""

# Build all four services
echo "[1/4] Building coordinator..."
docker build -f services/coordinator/Dockerfile -t ${REGISTRY}/stardew-coordinator:${VERSION} .

echo "[2/4] Building pierres-buying-tool..."
docker build -f services/pierres-buying-tool/Dockerfile -t ${REGISTRY}/stardew-pierres-buying-tool:${VERSION} .

echo "[3/4] Building tts-tool..."
docker build -f services/tts-tool/Dockerfile -t ${REGISTRY}/stardew-tts-tool:${VERSION} .

echo "[4/4] Building ocr-tools..."
docker build -f services/ocr-tools/Dockerfile -t ${REGISTRY}/stardew-ocr-tools:${VERSION} .

# Tag as latest
echo ""
echo "Tagging images as 'latest'..."
docker tag ${REGISTRY}/stardew-coordinator:${VERSION} ${REGISTRY}/stardew-coordinator:latest
docker tag ${REGISTRY}/stardew-pierres-buying-tool:${VERSION} ${REGISTRY}/stardew-pierres-buying-tool:latest
docker tag ${REGISTRY}/stardew-tts-tool:${VERSION} ${REGISTRY}/stardew-tts-tool:latest
docker tag ${REGISTRY}/stardew-ocr-tools:${VERSION} ${REGISTRY}/stardew-ocr-tools:latest

echo ""
echo "Build complete! Images:"
docker images | grep "stardew-"

echo ""
echo "========================================="
echo " Next Steps (MUST RUN ON HOST MACHINE)"
echo "========================================="
echo ""
echo "1. Login to GHCR:"
echo "   docker login ghcr.io"
echo ""
echo "2. Push images:"
echo "   docker push ${REGISTRY}/stardew-coordinator:${VERSION}"
echo "   docker push ${REGISTRY}/stardew-pierres-buying-tool:${VERSION}"
echo "   docker push ${REGISTRY}/stardew-tts-tool:${VERSION}"
echo "   docker push ${REGISTRY}/stardew-ocr-tools:${VERSION}"
echo "   docker push ${REGISTRY}/stardew-coordinator:latest"
echo "   docker push ${REGISTRY}/stardew-pierres-buying-tool:latest"
echo "   docker push ${REGISTRY}/stardew-tts-tool:latest"
echo "   docker push ${REGISTRY}/stardew-ocr-tools:latest"
echo ""
echo "3. Make packages public (they're private by default):"
echo "   https://github.com/thesteve0?tab=packages"
echo "   For each package: Settings → Change visibility → Public"
echo ""
echo "⚠️  REMINDER: All push commands must run on HOST, not in devcontainer!"
echo ""
