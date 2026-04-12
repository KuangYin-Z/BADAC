#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -x fabric-samples/bin/peer ]] \
  && docker image inspect hyperledger/fabric-peer:2.5.15 >/dev/null 2>&1 \
  && docker image inspect hyperledger/fabric-orderer:2.5.15 >/dev/null 2>&1 \
  && docker image inspect hyperledger/fabric-ca:1.5.17 >/dev/null 2>&1 \
  && docker image inspect hyperledger/fabric-nodeenv:2.5 >/dev/null 2>&1; then
  exit 0
fi

curl -fsSL https://raw.githubusercontent.com/hyperledger/fabric/v2.5.15/scripts/install-fabric.sh \
  | bash -s -- -f 2.5.15 -c 1.5.17 samples binary docker

docker pull hyperledger/fabric-nodeenv:2.5 >/dev/null
