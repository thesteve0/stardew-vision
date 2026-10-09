#!/usr/bin/env bash
# Canonical fine-tuned production deployment; no base/legacy fallback.
set -euo pipefail
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/configs/serving/openshift/deploy.sh" "$@"
