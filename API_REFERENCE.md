# Blockchain Demo — API Reference for Frontend

This document provides exact schemas, field types, and example payloads for all backend endpoints.

## Authentication (`/api/auth`)

Authentication is simplified. No endpoints require an `Authorization` header.

### 1. Login
- **URL**: `POST /api/auth/login`
- **Request Body**:
  | Field | Type | Required | Description |
  |---|---|---|---|
  | `username` | `string` | Yes | Valid username (e.g., `alice`, `admin`) |
  | `password` | `string` | Yes | Corresponding password |
- **Success Response (200 OK)**:
  ```json
  {
    "message": "string",
    "user": {
      "username": "string",
      "wallet_address": "string (0x...)",
      "msp_id": "string",
      "org": "string",
      "role": "string",
      "created_at": "ISO8601 string"
    }
  }
  ```
- **Error Response (401 Unauthorized)**:
  ```json
  { "error": "Invalid username or password" }
  ```

### 2. Get Current Profile
- **URL**: `GET /api/auth/me?username=alice`
- **Response (200 OK)**:
  ```json
  {
    "username": "string",
    "wallet_address": "string",
    "msp_id": "string",
    "org": "string",
    "role": "string",
    "created_at": "ISO8601 string"
  }
  ```

---

## Evidence Management (`/api/evidence`)

### 1. Submit Evidence (JSON Only)
- **URL**: `POST /api/evidence`
- **Request Body**:
  | Field | Type | Required | Description |
  |---|---|---|---|
  | `content` | `string` | Yes | The text or log content to store |
  | `evidenceId` | `string` | No | Unique ID; generated if missing |
  | `honeypotId` | `string` | No | ID of source honeypot |
  | `attackType` | `string` | No | e.g., "SQLi", "Brute Force" |
  | `sourceIpHash`| `string` | No | Hashed IP of attacker |
  | `mitreTechnique`| `string`| No | MITRE ATT&CK identifier |
- **Success Response (211 Created)**:
  ```json
  {
    "status": "success",
    "tx_id": "string (SHA256)",
    "block_number": "int",
    "evidence_id": "string",
    "content_hash": "string (SHA256)"
  }
  ```

### 2. Submit Evidence (File Upload)
- **URL**: `POST /api/evidence`
- **Content-Type**: `multipart/form-data`
- **Body**: 
  - `file`: The actual file to upload.
  - Plus any of the fields from the JSON version (in form-data).

### 3. List All Evidence
- **URL**: `GET /api/evidence?include_content=false`
- **Query Params**:
  | Param | Type | Required | Description |
  |---|---|---|---|
  | `include_content` | `boolean` | No | If true, returns full content for each record |
- **Response (200 OK)**:
  ```json
  {
    "status": "success",
    "total_records": "int",
    "data": [
      {
        "evidence_id": "string",
        "filename": "string",
        "content_hash": "string",
        "content_size_bytes": "int",
        "created_at": "ISO8601 string"
      }
    ]
  }
  ```

### 4. Cumulative Statistics
- **URL**: `GET /api/evidence/stats`
- **Response (200 OK)**:
  ```json
  {
    "status": "success",
    "total_files_submitted": "int",
    "total_bytes_stored": "int",
    "total_kb_stored": "float",
    "active_records": "int",
    "archived_records": "int"
  }
  ```

### 5. Download Evidence File
- **URL**: `GET /api/evidence/<evidence_id>/download`
- **Response (200 OK)**: File download (`text/plain`)

### 6. Latest Lines (All Records)
- **URL**: `GET /api/evidence/latest-lines?limit=100`
- **Query Params**:
  | Param | Type | Required | Description |
  |---|---|---|---|
  | `limit` | `integer` | No | Max records to return (1-500) |
- **Response (200 OK)**:
  ```json
  {
    "status": "success",
    "count": "int",
    "data": [
      {
        "evidence_id": "string",
        "filename": "string",
        "tx_id": "string",
        "last_line": "string",
        "timestamp": "ISO8601 string"
      }
    ]
  }
  ```

### 7. Timeline Latest Command
- **URL**: `GET /api/evidence/latest-command`
- **Response (200 OK)**:
  ```json
  {
    "status": "success",
    "command": "string (The last line of the latest submission)",
    "evidence_id": "string",
    "tx_id": "string",
    "timestamp": "ISO8601 string"
  }
  ```

---

## Blockchain Explorer (`/api/chain`)

### 1. Paginated Blocks
- **URL**: `GET /api/chain?page=1&per_page=10`
- **Response (200 OK)**:
  ```json
  {
    "status": "success",
    "data": {
      "blocks": [
        {
          "block_number": "int",
          "hash": "string",
          "previous_hash": "string",
          "data_hash": "string",
          "timestamp": "ISO8601 string",
          "transactions": [
             {
               "tx_id": "string",
               "submitter": "string",
               "function": "string",
               "payload_hash": "string",
               "status": "VALID"
             }
          ]
        }
      ],
      "total_blocks": "int",
      "pages": "int"
    }
  }
  ```

### 2. Chain Integrity Verification
- **URL**: `GET /api/chain/verify`
- **Response (200 OK)**:
  ```json
  {
    "status": "success",
    "data": {
      "verified": "boolean",
      "blocks_checked": "int",
      "issues": "list"
    }
  }
  ```

---

## Network Status (`/api/network`)

### 1. Overview
- **URL**: `GET /api/network/status`
- **Response (200 OK)**:
  ```json
  {
    "status": "success",
    "data": {
      "network_name": "string",
      "channel": "string",
      "chaincode": {
        "name": "string",
        "version": "string",
        "status": "string"
      },
      "organizations": [
        {
          "name": "string",
          "msp_id": "string",
          "peers": [{"id": "string", "status": "ONLINE"}]
        }
      ]
    }
  }
  ```
