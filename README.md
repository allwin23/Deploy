# Blockchain Demo Backend

A production-grade Flask backend that simulates a Hyperledger Fabric blockchain network. This project is designed for rapid deployment as a "digital twin" or mock of a real permissioned blockchain for demo/review purposes.

## Key Features

- **Blockchain Simulation**: Real SHA-256 hash-chained blocks, transactions, and deterministic wallet addresses.
- **Evidence Management**: Securely store evidence text/files with automatic hashing and timestamping.
- **JWT Authentication**: Secure login system with role-based access control.
- **Chain Explorer**: Dedicated endpoints to view the block history and verify cryptographic integrity.
- **Render Ready**: Includes `render.yaml` for one-click deployment with PostgreSQL.

## Core Endpoints

### Auth
- `POST /api/auth/login` — Login and get JWT access token.
- `GET /api/auth/me` — Get current user and wallet info.

### Evidence
- `POST /api/evidence` — Submit new evidence (supports JSON or file upload).
- `GET /api/evidence/stats` — View total files and data accumulated.
- `GET /api/evidence/all` — List all evidence records.

### Blockchain
- `GET /api/chain` — View the full blockchain (blocks & transactions).
- `GET /api/chain/verify` — Run a cryptographic audit of the chain.

### Network
- `GET /api/network/status` — View simulated status of peers, orderers, and chaincode.

## Quick Start (Local)

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Setup environment**:
   Copy `.env.example` to `.env` and configure accordingly.

3. **Run the server**:
   ```bash
   python app.py
   ```

## Deployment

Deploy directly to **Render** using the included `render.yaml`. It will automatically provision a PostgreSQL database and wire it to the application.
