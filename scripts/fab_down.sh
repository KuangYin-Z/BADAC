#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [[ ! -d "$ROOT/fabric-samples/test-network" ]]; then
  exit 0
fi

cd "$ROOT/fabric-samples/test-network"
./network.sh down

