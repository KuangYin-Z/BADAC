#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/fabric-samples/test-network"

./network.sh down
./network.sh up createChannel -ca
./network.sh deployCC -ccn auth -ccp ../../chaincode/auth -ccl javascript

