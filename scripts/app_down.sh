#!/usr/bin/env bash
set -euo pipefail

docker rm -f badac-app >/dev/null 2>&1 || true
