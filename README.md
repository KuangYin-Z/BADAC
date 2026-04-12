# BADAC Prototype Code

BADAC is the prototype code release for the paper *Blockchain-Assisted Anonymous Device Authentication with Access Control for Cross-Domain Industrial IoT*.

This repository is intended to serve as the paper-companion code repository. It contains the core prototype implementation needed to inspect the scheme, start a local demo, and understand how the protocol is mapped into code.

## Scope

What is included:

- Core BADAC prototype code
- Local runnable demo
- Python-side protocol logic
- Fabric gateway bridge
- Hyperledger Fabric chaincode

What is not included:

- Paper source files
- Benchmark raw-result datasets
- Plotting scripts
- Pre-downloaded third-party Fabric samples

This separation is intentional: the repository is a code companion for the protocol prototype, not a full artifact bundle for the paper evaluation.

## Tested Environment

The repository has been tested in a local Linux/WSL2 workflow with:

- Docker 29.1.5
- Node.js 20.18.1
- Python 3.12.3
- Bash

The application container is built from `node:20-bookworm` and installs:

- Python 3
- `Flask==3.1.3`
- `cryptography==46.0.5`
- `charm-crypto-framework==0.62`
- PBC 1.0.0

The Fabric demo path is pinned to:

- Hyperledger Fabric peer/orderer 2.5.15
- Hyperledger Fabric CA 1.5.17
- Fabric nodeenv 2.5

## External Dependency Note

The demo scripts download Hyperledger Fabric samples on demand into `fabric-samples/`. That directory is treated as a local runtime dependency and is not part of this repository.

To reduce upstream drift, `scripts/fab_get.sh` fetches the official Fabric install script from the pinned `v2.5.15` branch rather than from the moving `main` branch.

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

## Citation and Versioning

This repository should be cited as a software companion to the BADAC paper. The first paper-companion release is `v1.0.0`.

GitHub can expose repository citation metadata through `CITATION.cff`. If you cite the code in a paper, please cite a tagged release rather than a moving branch tip.

A BibTeX entry consistent with the current repository metadata is:

```bibtex
@misc{mao2026badaccode,
  author       = {Mao, Ziyan},
  title        = {{BADAC}: Prototype Implementation for Blockchain-Assisted Anonymous Device Authentication with Access Control for Cross-Domain Industrial IoT},
  year         = {2026},
  howpublished = {\url{https://github.com/KuangYin-Z/BADAC}},
  note         = {GitHub repository, version v1.0.0}
}
```

## Prototype Boundaries

This code is a local research prototype rather than a production system.

- The KGC is trusted during setup and key issuance
- The deployment target is a local prototype environment
- The online orchestration is minimal by design
- Production-grade operations, revocation governance, distributed key management, benchmark packaging, and hardened deployment concerns are out of scope

## Interface Summary

The Flask routes are:

- `/init`
- `/reg`
- `/pub`
- `/pull`
- `/sign`
- `/verify`
- `/result`

The chaincode functions are:

- `putPp`, `getPp`
- `putCh`, `getCh`
- `putRq`, `getRq`
- `putRs`, `getRs`
