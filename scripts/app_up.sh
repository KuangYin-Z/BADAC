#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

mkdir -p data/csp
docker rm -f badac-app >/dev/null 2>&1 || true
docker build -t badac-app-img -f Dockerfile.app .
docker run -d \
  --name badac-app \
  --network fabric_test \
  -p 8000:8000 \
  -e APP_PORT=8000 \
  -e APP_URL=http://localhost:8000 \
  -e DATA_DIR=/work/data \
  -e APP_ROOT=/work \
  -e GW_PATH=/work/bridge/gw.js \
  -e ABS_TMAX=16 \
  -v "$ROOT/data:/work/data" \
  -v "$ROOT/fabric-samples:/work/fabric-samples:ro" \
  badac-app-img >/dev/null
