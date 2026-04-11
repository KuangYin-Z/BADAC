#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

cleanup() {
  "$ROOT/scripts/app_down.sh" || true
  "$ROOT/scripts/fab_down.sh" || true
  "$ROOT/scripts/clean.sh" || true
}

trap cleanup EXIT

"$ROOT/scripts/fab_get.sh"
"$ROOT/scripts/fab_up.sh"
"$ROOT/scripts/app_up.sh"
python3 "$ROOT/scripts/demo.py"

