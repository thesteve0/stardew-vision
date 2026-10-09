#!/usr/bin/env bash
# Intentional source builds only; production deploy uses pinned existing images.
set -euo pipefail
VERSION=${1:?Usage: build-images.sh NEW_UNIQUE_VERSION}
ENGINE=${CONTAINER_ENGINE:-podman}
REGISTRY=ghcr.io/thesteve0
[[ "$VERSION" != latest && "$VERSION" =~ ^[a-zA-Z0-9_][a-zA-Z0-9_.-]*$ ]] || { echo 'Use a unique version, not latest.' >&2; exit 1; }
cd "$(dirname "${BASH_SOURCE[0]}")/.."
for pair in coordinator:coordinator ocr-tools:ocr-tools tts-tool:tts-tool; do
  directory=${pair%%:*}; name=${pair#*:}
  "$ENGINE" build -f "services/$directory/Dockerfile" -t "$REGISTRY/stardew-$name:$VERSION" .
  printf 'After validation, push: %s push %s/stardew-%s:%s\n' "$ENGINE" "$REGISTRY" "$name" "$VERSION"
done
echo 'Audit dependencies and source, test, push unique tags and review pinned digest updates before deploying.'
