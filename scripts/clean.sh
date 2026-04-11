#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

rm -f "$ROOT/data/state.json"
rm -f "$ROOT/data/csp/"*.json 2>/dev/null || true

if [[ -d "$ROOT/fabric-samples/test-network" ]]; then
  find "$ROOT/fabric-samples/test-network" -maxdepth 1 \( -name "*.log" -o -name "*.txt" -o -name "*.tar.gz" \) -type f -delete
fi

