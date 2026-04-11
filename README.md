# BADAC Prototype Code

BADAC is the prototype code release for the paper *Blockchain-Assisted Anonymous Device Authentication with Access Control for Cross-Domain Industrial IoT*.

This repository contains only the core prototype code needed to inspect the scheme, start a local demo, and understand how the protocol is mapped into code. It does not include the paper sources, benchmark result datasets, plotting scripts, or the official Hyperledger Fabric sample repository.

## Scope

- Prototype code only
- Local runnable demo
- Core protocol logic, Fabric bridge, and chaincode
- No paper files
- No benchmark artifacts
- No pre-downloaded third-party Fabric samples

## Requirements

- Docker
- Python 3
- Node.js
- Bash

The demo scripts download Hyperledger Fabric samples on demand into `fabric-samples/`. That directory is treated as a local runtime dependency and is not part of this repository.

## Quick Start

Run the end-to-end demo from the repository root:

```bash
bash scripts/demo.sh
```

The demo performs the following flow:

```text
fab_get -> fab_up -> app_up -> demo -> clean
```

If you want to run the steps manually:

```bash
bash scripts/fab_get.sh
bash scripts/fab_up.sh
bash scripts/app_up.sh
python3 scripts/demo.py
bash scripts/app_down.sh
bash scripts/fab_down.sh
bash scripts/clean.sh
```

## Repository Layout

- `app/`: Python-side protocol prototype, including CP-ABE, ABS, local state, and Flask API routes
- `bridge/`: Node.js Fabric gateway bridge used by the Python app
- `chaincode/auth/`: Hyperledger Fabric chaincode for public parameters, challenge metadata, requests, and results
- `scripts/`: Minimal setup, teardown, cleanup, and demo scripts

## Protocol-to-Code Mapping

The public interface follows the workflow described in the paper.

| Paper stage | Main action | Prototype interface |
| --- | --- | --- |
| Stage 1: Initialization and Key Issuance | KGC runs CP-ABE/ABS setup, publishes public parameters, and issues keys to domains | `POST /init`, `POST /reg`, chaincode `putPp/getPp` |
| Stage 2: Domain-Information Encryption and Publication | Verifier forms domain information, encrypts it, uploads the ciphertext to CSP, and publishes metadata on chain | `POST /pub`, chaincode `putCh/getCh` |
| Stage 3: Domain-Information Decryption and Anonymous Signing | Requester queries metadata, downloads ciphertext, checks integrity, decrypts, signs, and submits the authentication request | `POST /pull`, `POST /sign`, chaincode `putRq/getRq` |
| Stage 4: Verification and Result Recording | Verifier retrieves requests, verifies the ABS proof, records the result, and Requester reads the final result later | `POST /verify`, `POST /result`, chaincode `putRs/getRs` |

## Demo Coverage

`scripts/demo.py` checks the following paths:

- Happy path authentication
- Attribute mismatch rejection
- CSP ciphertext tampering detection
- Signature verification failure
- Duplicate `sid` replay rejection on chain

## Prototype Boundaries

This code is a local research prototype rather than a production system.

- The KGC is trusted during setup and key issuance
- The deployment target is a local prototype environment
- The online orchestration is minimal by design
- Production-grade operations, revocation governance, distributed key management, and hardened deployment concerns are out of scope

## Notes

- The Flask routes remain:
  - `/init`
  - `/reg`
  - `/pub`
  - `/pull`
  - `/sign`
  - `/verify`
  - `/result`
- The chaincode functions remain:
  - `putPp`, `getPp`
  - `putCh`, `getCh`
  - `putRq`, `getRq`
  - `putRs`, `getRs`

This repository is intended to be readable directly on GitHub and suitable for use as the paper's code repository.
