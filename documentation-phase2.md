# Local LLM Gateway — Documentation Phase 2

**Phase:** Phase 2 — API Key Authentication (Complete)
**Previous Phase:** Phase 1 — Basic LLM Gateway (`documentation.md`)
**Next Phase:** Phase 3 — OpenAI-Compatible API (Planned)

---

## Table of Contents

1. [What Changed From Phase 1](#1-what-changed-from-phase-1)
2. [Architecture Overview](#2-architecture-overview)
3. [Updated Project Structure](#3-updated-project-structure)
4. [New File Reference](#4-new-file-reference)
5. [Modified File Reference](#5-modified-file-reference)
6. [Database Design](#6-database-design)
7. [API Key Lifecycle](#7-api-key-lifecycle)
8. [API Reference](#8-api-reference)
9. [Authentication Flow](#9-authentication-flow)
10. [Complete Request Lifecycle](#10-complete-request-lifecycle)
11. [Complete Dependency Graph](#11-complete-dependency-graph)
12. [Startup Sequence](#12-startup-sequence)
13. [Testing the API End-to-End](#13-testing-the-api-end-to-end)
14. [Error Reference](#14-error-reference)
15. [Security Decisions](#15-security-decisions)
16. [Known Limitations and Future Work](#16-known-limitations-and-future-work)

---

## 1. What Changed From Phase 1

Phase 1 had no authentication. Any client could call `POST /chat` freely.

Phase 2 adds:

| Addition | Description |
|---|---|
| `app/database.py` | SQLite connection layer — creates `keys.db` and the `api_keys` table |
| `app/schemas/key.py` | Pydantic models for key creation and listing |
| `app/services/key_service.py` | Key generation, hashing, storage, revocation, and validation logic |
| `app/dependencies/auth.py` | FastAPI dependency that extracts and validates Bearer tokens |
| `app/routers/keys.py` | Admin endpoints for managing API keys |
| `app/routers/chat.py` | **Modified** — `POST /chat` is now protected by `Depends(verify_api_key)` |
| `app/main.py` | **Modified** — database initialized at startup, keys router registered |

**Phase 1 files that are completely unchanged:**
- `app/config.py`
- `app/schemas/chat.py`
- `app/services/ollama_service.py`

---

## 2. Architecture Overview

```
┌───────────────────────────────────────────────────────────────┐
│                         CLIENT                                │
│   Authorization: Bearer sk_local_...                         │
│   POST /chat  { "model": "...", "message": "..." }            │
└──────────────────────────┬────────────────────────────────────┘
                           │
                           ▼
┌───────────────────────────────────────────────────────────────┐
│                  UVICORN  /  FASTAPI                          │
│                    app/main.py                                │
│   lifespan startup: init_db()                                 │
│   routes: POST /chat, POST/GET/DELETE /keys                   │
└──────────────────────────┬────────────────────────────────────┘
                           │
             ┌─────────────┴──────────────┐
             │                            │
             ▼                            ▼
┌────────────────────────┐   ┌────────────────────────────────┐
│   AUTH DEPENDENCY      │   │    KEY MANAGEMENT              │
│  app/dependencies/     │   │    app/routers/keys.py         │
│     auth.py            │   │                                │
│                        │   │  POST   /keys  → create_key()  │
│  Extracts Bearer token │   │  GET    /keys  → list_keys()   │
│  Calls validate_key()  │   │  DELETE /keys/{id}             │
└───────────┬────────────┘   │              → revoke_key()    │
            │                └──────────────┬─────────────────┘
            │                               │
            ▼                               ▼
┌───────────────────────────────────────────────────────────────┐
│                   SERVICE LAYER                               │
│              app/services/key_service.py                      │
│                                                               │
│  _hash_key()     — SHA-256 hashing (private)                  │
│  create_key()    — generate, hash, store, return plain key    │
│  list_keys()     — read metadata rows                         │
│  revoke_key()    — set is_active = 0                          │
│  validate_key()  — hash incoming key, check database          │
└──────────────────────────┬────────────────────────────────────┘
                           │
                           ▼
┌───────────────────────────────────────────────────────────────┐
│                   DATABASE LAYER                              │
│                  app/database.py                              │
│                                                               │
│  DB_PATH         — absolute path to keys.db                   │
│  get_connection() — returns sqlite3.Connection per call       │
│  init_db()       — CREATE TABLE IF NOT EXISTS api_keys        │
└──────────────────────────┬────────────────────────────────────┘
                           │
                           ▼
                      keys.db (SQLite file)
                   project root / keys.db
```

---

## 3. Updated Project Structure

```
local-LLM/
├── app/
│   ├── __init__.py
│   ├── main.py                       # MODIFIED — lifespan + keys router
│   ├── config.py                     # unchanged
│   ├── database.py                   # NEW — SQLite layer
│   ├── dependencies/
│   │   ├── __init__.py
│   │   └── auth.py                   # NEW — Bearer token dependency
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── chat.py                   # MODIFIED — auth dependency added
│   │   └── keys.py                   # NEW — key management endpoints
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── chat.py                   # unchanged
│   │   └── key.py                    # NEW — key request/response models
│   └── services/
│       ├── __init__.py
│       ├── ollama_service.py         # unchanged
│       └── key_service.py            # NEW — key business logic
├── keys.db                           # AUTO-CREATED at first startup
├── .env
├── .env.example
├── requirements.txt
├── documentation.md                  # Phase 1
└── documentation-phase2.md          # Phase 2 (this file)
```

---

## 4. New File Reference

---

### `app/database.py`

**Role:** The lowest layer of the new stack. Owns the SQLite connection and table initialization. Has no project imports — depends on nothing except the Python standard library.

**Why a separate file:** Database infrastructure is not business logic. `key_service.py` should not know how to open a file or create a table. Separating these concerns means you can swap the database engine (e.g. to PostgreSQL) by changing only this file.

**Key decisions:**
- `get_connection()` returns a **new connection per call** — not a global shared connection. SQLite connections are not thread-safe by default. A per-call connection ensures complete isolation between concurrent requests.
- `connection.row_factory = sqlite3.Row` — makes rows accessible by column name (`row["name"]`) instead of index (`row[1]`), improving readability and safety.
- `CREATE TABLE IF NOT EXISTS` — safe to run on every startup. Creates the table on first run, silently does nothing on subsequent runs.
- `DB_PATH` uses `Path(__file__).parent.parent` — resolves to the project root regardless of where you run the server from.

```python
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "keys.db"

def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection

def init_db() -> None:
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS api_keys (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                name       TEXT    NOT NULL,
                key_hash   TEXT    NOT NULL UNIQUE,
                is_active  INTEGER NOT NULL DEFAULT 1,
                created_at TEXT    NOT NULL
            )
        """)
        connection.commit()
```

---

### `app/schemas/key.py`

**Role:** Defines the HTTP contract for key management endpoints. Three models, each with a specific direction and security boundary.

| Model | Direction | Fields | Security note |
|---|---|---|---|
| `CreateKeyRequest` | Client → API | `name: str` | Client provides only the label |
| `CreateKeyResponse` | API → Client (once) | `id`, `name`, `key` | Plain key shown here and never again |
| `KeyInfoResponse` | API → Client (any time) | `id`, `name`, `is_active`, `created_at` | No `key_hash`, no plain key |

**Why `key_hash` is never in any schema:** The hash is the security-sensitive equivalent of a password digest. Exposing it in an HTTP response would allow offline brute-force attacks. It exists only inside the database and inside `key_service.py` during a single request.

```python
from pydantic import BaseModel

class CreateKeyRequest(BaseModel):
    name: str

class CreateKeyResponse(BaseModel):
    id: int
    name: str
    key: str          # plain key — shown ONCE only

class KeyInfoResponse(BaseModel):
    id: int
    name: str
    is_active: bool   # SQLite INTEGER 0/1 coerced to bool by Pydantic
    created_at: str
```

---

### `app/services/key_service.py`

**Role:** All business logic related to API keys. The only file that hashes keys, generates keys, and makes validation decisions. Imports `database.py` for storage. Imports `schemas/key.py` for return types.

**Functions:**

| Function | Input | Output | Description |
|---|---|---|---|
| `_hash_key(plain_key)` | `str` | `str` (hex) | SHA-256 hash — private, used internally only |
| `create_key(name)` | `str` | `CreateKeyResponse` | Generates key, stores hash, returns plain key once |
| `list_keys()` | — | `list[KeyInfoResponse]` | Reads all rows, excludes hash from query |
| `revoke_key(key_id)` | `int` | `bool` | Sets `is_active=0`, returns False if ID not found |
| `validate_key(plain_key)` | `str` | `None` or raises | Hashes input, compares to DB, raises 401/403 |

**Key generation:**
```
secrets.token_urlsafe(32)     → 43 URL-safe base64 chars (256 bits entropy)
"sk_local_" + token           → "sk_local_xK9mP2qR..."
hashlib.sha256(key.encode())  → 64-char hex digest stored in DB
```

`secrets.token_urlsafe` is used instead of `random` because it draws from the OS's cryptographically secure entropy source. The `sk_local_` prefix makes keys immediately identifiable.

**Validation logic (inside `validate_key`):**
```
incoming plain key
    → hash it (same SHA-256 function used at creation)
    → SELECT is_active FROM api_keys WHERE key_hash = ?
    → no row found  → raise 401 "Invalid API key"
    → is_active = 0 → raise 403 "API key has been revoked"
    → is_active = 1 → return None (success)
```

The plain key is never stored anywhere. Only the hash reaches the database.

---

### `app/dependencies/auth.py`

**Role:** Thin HTTP adapter between the `Authorization` header and `key_service.validate_key()`. Contains no business logic, no hashing, no SQL.

**Why `HTTPBearer` instead of manual header parsing:**
- `HTTPBearer` handles `Authorization: Bearer <token>` parsing automatically
- Returns `None` (not an error) when the header is absent, because `auto_error=False` gives `verify_api_key` full control over error messages
- Registers the Bearer security scheme in Swagger `/docs` automatically — a padlock icon appears

**Why synchronous `def` instead of `async def`:**
`validate_key()` is synchronous (sqlite3 calls, no `await`). Declaring `verify_api_key` as `async def` with nothing to `await` would be misleading. FastAPI dispatches synchronous dependencies to a thread pool correctly.

```python
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.services.key_service import validate_key

_bearer_scheme = HTTPBearer(auto_error=False)

def verify_api_key(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> None:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    validate_key(credentials.credentials)
    # credentials.credentials = the token after "Bearer "
```

---

### `app/routers/keys.py`

**Role:** Exposes three admin HTTP endpoints for API key management. Intentionally unprotected (bootstrap problem — see [Security Decisions](#15-security-decisions)).

**Endpoints:**

| Decorator | Path | Status | Service call |
|---|---|---|---|
| `@router.post("")` | `POST /keys` | 201 Created | `key_service.create_key(name)` |
| `@router.get("")` | `GET /keys` | 200 OK | `key_service.list_keys()` |
| `@router.delete("/{key_id}")` | `DELETE /keys/{id}` | 204 No Content | `key_service.revoke_key(key_id)` |

Router is created with `prefix="/keys"` so paths are declared relative to that prefix. `tags=["API Keys"]` groups them in Swagger UI.

`DELETE` returns `204 No Content` (empty body) on success. Returns `404` if the `key_id` does not exist in the database — detected via `revoke_key()` returning `False` (zero rows updated).

```python
router = APIRouter(prefix="/keys", tags=["API Keys"])

@router.post("", response_model=CreateKeyResponse, status_code=201)
def create_new_key(body: CreateKeyRequest) -> CreateKeyResponse:
    return key_service.create_key(name=body.name)

@router.get("", response_model=list[KeyInfoResponse])
def get_all_keys() -> list[KeyInfoResponse]:
    return key_service.list_keys()

@router.delete("/{key_id}", status_code=204)
def delete_key(key_id: int) -> None:
    revoked = key_service.revoke_key(key_id=key_id)
    if not revoked:
        raise HTTPException(status_code=404, detail="API key not found")
```

---

## 5. Modified File Reference

---

### `app/main.py` — Changes

Two additions from Phase 1:

**1. Lifespan context manager:**
```python
from contextlib import asynccontextmanager
from app.database import init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()     # runs before first request
    try:
        yield     # server runs here
    finally:
        pass      # cleanup placeholder

app = FastAPI(lifespan=lifespan)
```

`init_db()` runs at startup, not on the first request. If the database cannot be created (permissions issue, disk full), the server fails to start immediately — not silently on the first user's request.

**2. Keys router registration:**
```python
from app.routers import chat, keys
app.include_router(keys.router)   # adds POST/GET/DELETE /keys
```

---

### `app/routers/chat.py` — Changes

One line added to the route decorator. The handler body is completely unchanged:

```python
# Before:
@router.post("/chat", response_model=ChatResponse)

# After:
@router.post("/chat", response_model=ChatResponse, dependencies=[Depends(verify_api_key)])
```

`dependencies=[Depends(verify_api_key)]` is used instead of a function parameter because `verify_api_key` returns `None` — the handler does not receive or use any value from it. It is a pure gate: allow or block.

---

## 6. Database Design

### Table: `api_keys`

```sql
CREATE TABLE IF NOT EXISTS api_keys (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    NOT NULL,
    key_hash   TEXT    NOT NULL UNIQUE,
    is_active  INTEGER NOT NULL DEFAULT 1,
    created_at TEXT    NOT NULL
);
```

| Column | Type | Constraint | Purpose |
|---|---|---|---|
| `id` | INTEGER | PK, AUTOINCREMENT | Stable reference for revocation (`DELETE /keys/1`) |
| `name` | TEXT | NOT NULL | Human label — identifies which app owns the key |
| `key_hash` | TEXT | NOT NULL, UNIQUE | SHA-256 of the plain key — used for validation lookups |
| `is_active` | INTEGER | NOT NULL, DEFAULT 1 | `1` = active, `0` = revoked. Row kept for audit trail |
| `created_at` | TEXT | NOT NULL | ISO 8601 UTC string — stored as TEXT (SQLite has no datetime type) |

**Intentionally omitted columns:**

| Column | Reason omitted |
|---|---|
| `expires_at` | Requires per-request date comparison and cleanup jobs |
| `last_used_at` | Requires a DB write on every request — write contention |
| `usage_count` | Same reason as `last_used_at` |
| `scopes` | All keys have equal access in MVP |
| `key_prefix` | UX improvement, not required for correctness |

**Sample row after key creation:**
```
id | name    | key_hash             | is_active | created_at
 1 | my-app  | a3f1c9d7...(64 hex)  |     1     | 2026-06-25T10:00:00+00:00
```

**Sample row after revocation:**
```
id | name    | key_hash             | is_active | created_at
 1 | my-app  | a3f1c9d7...(64 hex)  |     0     | 2026-06-25T10:00:00+00:00
```

The row is never deleted. Revocation is always a soft delete (`is_active = 0`).

---

## 7. API Key Lifecycle

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CREATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  1. secrets.token_urlsafe(32)
     → 43 chars of cryptographically random URL-safe base64

  2. plain_key = "sk_local_" + token
     → "sk_local_xK9mP2qR..."

  3. key_hash = SHA-256(plain_key)
     → "a3f1c9d7..." (64 hex chars)

  4. INSERT INTO api_keys (name, key_hash, is_active, created_at)
     → id = 1 (auto-assigned)

  5. Return CreateKeyResponse(id=1, name=..., key="sk_local_...")
     → plain key returned to caller ONCE
     → plain key discarded from memory

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
VALIDATION (every protected request)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  1. Extract "sk_local_xK9mP2qR..." from Authorization header

  2. incoming_hash = SHA-256("sk_local_xK9mP2qR...")
     → "a3f1c9d7..."  ← same hash as stored

  3. SELECT is_active FROM api_keys WHERE key_hash = "a3f1..."
     → no row   → 401 "Invalid API key"
     → row, is_active=0 → 403 "API key has been revoked"
     → row, is_active=1 → pass, request continues

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REVOCATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  1. DELETE /keys/1

  2. UPDATE api_keys SET is_active = 0 WHERE id = 1

  3. Row preserved (audit trail)
     Any future request with this key → 403 immediately

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WHY ONLY THE HASH IS STORED

  Plain key in DB → single DB leak = all clients compromised
  Hash in DB      → single DB leak = nothing usable
  SHA-256 is one-way: hash cannot be reversed to the plain key
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 8. API Reference

### `POST /keys` — Create API Key

**No authentication required** (bootstrap endpoint)

**Request**
```
POST /keys
Content-Type: application/json
{ "name": "my-app" }
```

**Response — 201 Created**
```json
{
    "id": 1,
    "name": "my-app",
    "key": "sk_local_xK9mP2qR..."
}
```
> Save the `key` value immediately. It is never shown again.

---

### `GET /keys` — List API Keys

**No authentication required**

**Request**
```
GET /keys
```

**Response — 200 OK**
```json
[
    {
        "id": 1,
        "name": "my-app",
        "is_active": true,
        "created_at": "2026-06-25T10:00:00+00:00"
    }
]
```

---

### `DELETE /keys/{id}` — Revoke API Key

**No authentication required**

**Request**
```
DELETE /keys/1
```

**Response — 204 No Content** (empty body)

**Response — 404 Not Found**
```json
{ "detail": "API key not found" }
```

---

### `POST /chat` — Chat (Protected)

**Authentication required** — `Authorization: Bearer <key>`

**Request**
```
POST /chat
Authorization: Bearer sk_local_xK9mP2qR...
Content-Type: application/json

{
    "model": "qwen2.5:7b",
    "message": "Hello"
}
```

**Response — 200 OK**
```json
{ "response": "Hello! How can I help you today?" }
```

**Response — 401 Unauthorized**
```json
{ "detail": "Authorization header missing" }
{ "detail": "Invalid API key" }
```

**Response — 403 Forbidden**
```json
{ "detail": "API key has been revoked" }
```

---

## 9. Authentication Flow

```
Header: Authorization: Bearer sk_local_xK9mP2qR...
        │
        ▼
app/dependencies/auth.py
  HTTPBearer extracts credentials object
  credentials.credentials = "sk_local_xK9mP2qR..."
        │
  credentials is None? → 401 "Authorization header missing"
        │
        ▼
app/services/key_service.py → validate_key("sk_local_xK9mP2qR...")
  _hash_key("sk_local_xK9mP2qR...") → "a3f1c9d7..."
        │
        ▼
app/database.py → get_connection()
  SELECT is_active FROM api_keys WHERE key_hash = "a3f1..."
        │
  No row found   → 401 "Invalid API key"
  is_active = 0  → 403 "API key has been revoked"
  is_active = 1  → return None
        │
        ▼
Route handler runs (auth guaranteed)
```

---

## 10. Complete Request Lifecycle

```
CLIENT
  POST /chat
  Authorization: Bearer sk_local_xK9mP2qR...
  { "model": "qwen2.5:7b", "message": "Hello" }
        │
        ▼
Uvicorn → FastAPI: route matched POST /chat
        │
        ▼
[1] Depends(verify_api_key) executes
    → validates Bearer token against SQLite
    → pass or raise 401/403
        │
        ▼
[2] Pydantic: validates body → ChatRequest object
    → invalid? 422 returned
        │
        ▼
[3] chat() handler called
        │
        ▼
[4] ask_ollama(model, message)
    → httpx POST → Ollama → Qwen
    → await response
        │
        ▼
[5] ChatResponse(response=reply)
    → FastAPI serializes → HTTP 200
        │
        ▼
CLIENT: { "response": "..." }
```

---

## 11. Complete Dependency Graph

```
Uvicorn
  └── app/main.py
        │  (startup: init_db)
        │
        ├── app/database.py ◄──────────────────────────┐
        │     └── keys.db                              │ shared
        │                                              │
        ├── app/routers/chat.py                        │
        │     ├── app/dependencies/auth.py             │
        │     │     └── app/services/key_service.py ───┤
        │     │           ├── app/database.py          │
        │     │           └── app/schemas/key.py       │
        │     │                                        │
        │     ├── app/schemas/chat.py                  │
        │     └── app/services/ollama_service.py       │
        │           └── app/config.py                  │
        │                 └── .env                     │
        │                                              │
        └── app/routers/keys.py                        │
              ├── app/schemas/key.py                   │
              └── app/services/key_service.py ─────────┘


External:
  ollama_service.py ──HTTP──► Ollama (localhost:11434) ──► Qwen model
```

**Rule:** every arrow points downward. No file imports from a layer above it. `key_service.py` is imported by both `auth.py` and `routers/keys.py` — Python's import system initializes it once.

---

## 12. Startup Sequence

```
$ uvicorn app.main:app --reload
        │
        ▼
Python imports app/main.py
  → all dependencies resolved and imported
  → DB_PATH computed: project_root/keys.db
  → settings.ollama_base_url loaded from .env
        │
        ▼
app = FastAPI(lifespan=lifespan)
  → ASGI app created, routing table empty
        │
        ▼
app.include_router(chat.router)
  → POST /chat registered (protected)

app.include_router(keys.router)
  → POST /keys registered
  → GET  /keys registered
  → DELETE /keys/{key_id} registered
        │
        ▼
Uvicorn triggers lifespan startup
  → init_db() called
  → sqlite3 opens/creates keys.db
  → CREATE TABLE IF NOT EXISTS api_keys (...)
  → committed, connection closed
        │
        ▼
Uvicorn binds to 0.0.0.0:8000
INFO: Application startup complete.
All routes active. Database ready.
```

---

## 13. Testing the API End-to-End

### Step 1 — Start Ollama

```powershell
ollama serve
# in another terminal:
ollama pull qwen2.5:7b
```

### Step 2 — Start the server

```powershell
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

On first run, `keys.db` is created automatically. You will see no errors in the console.

---

### Step 3 — Create an API Key

```powershell
curl -X POST http://localhost:8000/keys `
  -H "Content-Type: application/json" `
  -d '{"name": "test-key"}'
```

Expected — `201 Created`:
```json
{
    "id": 1,
    "name": "test-key",
    "key": "sk_local_xK9mP2qR..."
}
```

**Save the `key` value. It will not be shown again.**

---

### Step 4 — List Keys

```powershell
curl http://localhost:8000/keys
```

Expected — `200 OK`:
```json
[{ "id": 1, "name": "test-key", "is_active": true, "created_at": "..." }]
```

---

### Step 5 — Send an Authenticated Chat Request

```powershell
curl -X POST http://localhost:8000/chat `
  -H "Content-Type: application/json" `
  -H "Authorization: Bearer sk_local_xK9mP2qR..." `
  -d '{"model": "qwen2.5:7b", "message": "Hello"}'
```

Expected — `200 OK`:
```json
{ "response": "Hello! How can I help you today?" }
```

---

### Step 6 — Test Unauthenticated Request (should fail)

```powershell
curl -X POST http://localhost:8000/chat `
  -H "Content-Type: application/json" `
  -d '{"model": "qwen2.5:7b", "message": "Hello"}'
```

Expected — `401 Unauthorized`:
```json
{ "detail": "Authorization header missing" }
```

---

### Step 7 — Test Invalid Key

```powershell
curl -X POST http://localhost:8000/chat `
  -H "Content-Type: application/json" `
  -H "Authorization: Bearer sk_local_fakekey123" `
  -d '{"model": "qwen2.5:7b", "message": "Hello"}'
```

Expected — `401 Unauthorized`:
```json
{ "detail": "Invalid API key" }
```

---

### Step 8 — Revoke the Key and Retry

```powershell
# Revoke
curl -X DELETE http://localhost:8000/keys/1
# Expected: HTTP 204 (empty body)

# Retry chat with revoked key
curl -X POST http://localhost:8000/chat `
  -H "Content-Type: application/json" `
  -H "Authorization: Bearer sk_local_xK9mP2qR..." `
  -d '{"model": "qwen2.5:7b", "message": "Hello"}'
```

Expected — `403 Forbidden`:
```json
{ "detail": "API key has been revoked" }
```

---

## 14. Error Reference

### Authentication Errors

| Status | Detail | Cause |
|---|---|---|
| `401` | Authorization header missing | No `Authorization` header sent |
| `401` | Invalid API key | Key does not exist in database |
| `403` | API key has been revoked | Key exists but `is_active = 0` |

### Key Management Errors

| Status | Detail | Cause |
|---|---|---|
| `404` | API key not found | `DELETE /keys/{id}` with non-existent ID |
| `422` | Field required | `POST /keys` sent without `name` field |

### Inherited From Phase 1 (chat endpoint)

| Status | Detail | Cause |
|---|---|---|
| `422` | Field required | Missing `model` or `message` in request body |
| `503` | Ollama is not reachable | Ollama process not running |
| `504` | Ollama did not respond in time | Inference timeout (120s) |
| `502` | Ollama returned an error: `{code}` | Model not found or Ollama internal error |

---

## 15. Security Decisions

### Why Only the Hash Is Stored

If the database is leaked, the attacker gets a list of SHA-256 hashes. SHA-256 is a one-way function — you cannot reverse a hash to the original key. The attacker cannot authenticate using hashes alone. The plain keys, which were only ever in memory momentarily, are gone.

### Why the Plain Key Is Returned Only Once

After the `POST /keys` response is sent, the plain key is garbage collected. It is never written to disk, never logged, never stored in the database. If the caller loses it, the only option is to revoke and regenerate. This is identical to GitHub, Stripe, and OpenAI's key issuance model.

### Why `secrets.token_urlsafe` Is Used

`secrets` draws from the OS's cryptographically secure entropy source (`/dev/urandom` on Linux, `CryptGenRandom` on Windows). The `random` module is deterministic given a seed and is not suitable for security tokens. `token_urlsafe(32)` produces 32 bytes = 256 bits of entropy — well above the threshold needed to make brute-force impractical.

### The Bootstrap Problem — Why `/keys` Is Unprotected in the MVP

Protecting `POST /keys` with an API key creates a paradox: you need a key to create a key, but no keys exist yet. This is the bootstrap problem. Three production solutions exist:

| Solution | Description |
|---|---|
| **Option A — Admin env key** | `ADMIN_KEY` in `.env` protects `/keys` via a separate dependency |
| **Option B — First-run endpoint** | `POST /setup` works only when 0 keys exist, then disables itself |
| **Option C — Separate admin surface** | Admin operations on a different port or behind a VPN |

For this MVP (localhost only, single developer), leaving `/keys` unprotected is an acceptable and documented trade-off. The correct production path is Option A.

---

## 16. Known Limitations and Future Work

### Remaining Code Review Issues (from Phase 1)

| # | File | Issue | Status |
|---|---|---|---|
| 3 | `config.py` | Deprecated Pydantic v1 `class Config` syntax | Pending |
| 4 | `ollama_service.py` | New `AsyncClient` per request | Pending |
| 5 | `routers/chat.py` | Explicit `ChatResponse(...)` instead of dict | Pending |
| 6 | Project root | No `pyproject.toml` | Pending |

### Phase 2 Specific Limitations

| Limitation | Impact | Future fix |
|---|---|---|
| `/keys` endpoints unprotected | Anyone on the network can create/revoke keys | Add `ADMIN_KEY` env var + separate dependency |
| No key expiry | Compromised keys valid forever until manually revoked | Add `expires_at` column + check in `validate_key()` |
| Synchronous SQLite calls | Blocks thread pool on every auth check | Switch to `aiosqlite` for full async DB access |
| No key prefix in list | Cannot identify a key by its prefix without plain value | Add `key_prefix` column (first 8 chars, safe to store) |

---

## Upcoming: Phase 3 — OpenAI-Compatible API

Add `POST /v1/chat/completions` matching the OpenAI specification so any OpenAI SDK, OpenWebUI, or LiteLLM instance can point to this gateway without modification.

**New files planned:**
- `app/routers/v1/chat.py` — `/v1/chat/completions` endpoint
- `app/schemas/openai.py` — OpenAI-compatible request and response models

**Authentication:** Phase 3 will reuse the same `Depends(verify_api_key)` from Phase 2 — the Bearer token format is already OpenAI-compatible.
