# Local LLM Gateway — Documentation

**Stage:** Phase 1 — Basic LLM Gateway (Complete)
**Next Stage:** Phase 2 — API Key Authentication (Designed, pending implementation)

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture](#2-architecture)
3. [Project Structure](#3-project-structure)
4. [File Reference](#4-file-reference)
5. [API Reference](#5-api-reference)
6. [Request Lifecycle](#6-request-lifecycle)
7. [Dependency Graph](#7-dependency-graph)
8. [Setup and Installation](#8-setup-and-installation)
9. [Running the Server](#9-running-the-server)
10. [Testing the API](#10-testing-the-api)
11. [Error Reference](#11-error-reference)
12. [Design Decisions](#12-design-decisions)
13. [Known Issues and Future Work](#13-known-issues-and-future-work)

---

## 1. Project Overview

A minimal, async LLM gateway built with FastAPI that forwards chat requests to a locally running Ollama instance and returns the model's response.

### Goal

```
Client
  ↓
POST /chat
  ↓
FastAPI
  ↓
Ollama
  ↓
Qwen (or any Ollama model)
  ↓
Response
```

### What This Is

- A thin HTTP proxy between any HTTP client and Ollama
- A foundation for adding API Key authentication, streaming, and OpenAI compatibility in later phases

### What This Is Not

- An OpenAI-compatible API (Phase 3)
- A RAG system
- A multi-user platform with authentication (Phase 2, designed but not yet implemented)

---

## 2. Architecture

### Layer Diagram

```
┌─────────────────────────────────────┐
│             CLIENT                  │
│  (curl, HTTP client, any app)       │
└────────────────┬────────────────────┘
                 │  HTTP POST /chat
                 ▼
┌─────────────────────────────────────┐
│           UVICORN (ASGI)            │
│         Entry: app/main.py          │
└────────────────┬────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│         FASTAPI ROUTER              │
│       app/routers/chat.py           │
│                                     │
│  Validates input via Pydantic       │
│  (app/schemas/chat.py)              │
└────────────────┬────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│          SERVICE LAYER              │
│    app/services/ollama_service.py   │
│                                     │
│  Builds Ollama payload              │
│  Sends async HTTP request (httpx)   │
│  Parses response                    │
│  Reads config from app/config.py    │
└────────────────┬────────────────────┘
                 │  HTTP POST /api/chat
                 ▼
┌─────────────────────────────────────┐
│         OLLAMA (local)              │
│      localhost:11434                │
│                                     │
│  Loads and runs the model           │
│  (e.g. qwen2.5:7b)                  │
└────────────────┬────────────────────┘
                 │  JSON response
                 ▼
             (unwound back up the chain)
                 │
                 ▼
┌─────────────────────────────────────┐
│             CLIENT                  │
│  { "response": "Hello!" }           │
└─────────────────────────────────────┘
```

### Design Principles

- **Single Responsibility**: every file has exactly one job
- **Dependency direction**: high-level layers call low-level layers, never the reverse
- **No logic in main.py**: it only wires components together
- **No HTTP in routers**: routers coordinate, services communicate
- **Async throughout**: all I/O operations use `async/await` to avoid blocking

---

## 3. Project Structure

```
local-LLM/
├── app/
│   ├── __init__.py
│   ├── main.py                  # App entry point, router registration
│   ├── config.py                # Environment-based configuration
│   ├── routers/
│   │   ├── __init__.py
│   │   └── chat.py              # POST /chat endpoint
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── chat.py              # Request and response Pydantic models
│   └── services/
│       ├── __init__.py
│       └── ollama_service.py    # HTTP communication with Ollama
├── .env                         # Local config (not committed)
├── .env.example                 # Config template (committed)
├── requirements.txt             # Python dependencies
└── documentation.md             # This file
```

---

## 4. File Reference

### `app/main.py`

**Role:** Application entry point. Creates the FastAPI instance and registers all routers.

**Responsibilities:**
- Instantiate `FastAPI()`
- Call `app.include_router()` for each router module

**Does not:** handle requests, validate input, talk to Ollama, read config.

```python
from fastapi import FastAPI
from app.routers import chat

app = FastAPI()
app.include_router(chat.router)
```

---

### `app/config.py`

**Role:** Single source of truth for all configuration values. Reads from `.env` file.

**Responsibilities:**
- Define `Settings` class with typed fields
- Expose a single `settings` instance imported by the rest of the app

**Environment variables:**

| Variable | Default | Description |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Base URL of the running Ollama instance |

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    ollama_base_url: str = "http://localhost:11434"

    class Config:
        env_file = ".env"

settings = Settings()
```

---

### `app/schemas/chat.py`

**Role:** Defines the contract between the client and the API. Enforces input and output shapes using Pydantic.

**Models:**

| Model | Direction | Fields |
|---|---|---|
| `ChatRequest` | Incoming (client → API) | `model: str`, `message: str` |
| `ChatResponse` | Outgoing (API → client) | `response: str` |

If the client sends an invalid body (missing field, wrong type), FastAPI automatically returns `422 Unprocessable Entity` before the route handler runs.

---

### `app/routers/chat.py`

**Role:** Defines the `POST /chat` HTTP endpoint. Coordinates between the schema layer and the service layer.

**Responsibilities:**
- Register route with FastAPI
- Receive validated `ChatRequest` from Pydantic
- Call `ask_ollama()` from the service layer
- Return `ChatResponse`

**Does not:** know about Ollama's API format, read `.env`, make HTTP calls.

---

### `app/services/ollama_service.py`

**Role:** The only file that communicates with Ollama. Handles all Ollama-specific logic including request formatting, HTTP transport, and response parsing.

**Responsibilities:**
- Build the Ollama `/api/chat` payload
- Send async HTTP POST via `httpx`
- Parse the response and extract the reply text
- Translate Ollama errors into `HTTPException` responses

**Error handling:**

| Exception | HTTP Status | Detail |
|---|---|---|
| `httpx.ConnectError` | 503 | Ollama is not reachable |
| `httpx.TimeoutException` | 504 | Ollama did not respond in time |
| `httpx.HTTPStatusError` | 502 | Ollama returned an error: `{status_code}` |
| `KeyError` | 502 | Unexpected response structure from Ollama |

---

## 5. API Reference

### `POST /chat`

Send a message to a local LLM via Ollama.

**Request**

```
POST /chat
Content-Type: application/json
```

```json
{
    "model": "qwen2.5:7b",
    "message": "Hello"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `model` | string | Yes | The Ollama model name to use |
| `message` | string | Yes | The user's message text |

**Response — 200 OK**

```json
{
    "response": "Hello! How can I help you today?"
}
```

| Field | Type | Description |
|---|---|---|
| `response` | string | The model's reply text |

**Response — 422 Unprocessable Entity**

Returned when the request body is malformed or missing required fields.

```json
{
    "detail": [
        {
            "type": "missing",
            "loc": ["body", "message"],
            "msg": "Field required"
        }
    ]
}
```

**Response — 503 Service Unavailable**

Returned when Ollama is not running or unreachable.

```json
{
    "detail": "Ollama is not reachable"
}
```

**Response — 504 Gateway Timeout**

Returned when Ollama does not respond within 120 seconds.

```json
{
    "detail": "Ollama did not respond in time"
}
```

**Response — 502 Bad Gateway**

Returned when Ollama responds with an error or unexpected format.

```json
{
    "detail": "Ollama returned an error: 404"
}
```

---

## 6. Request Lifecycle

```
1. Client sends POST /chat with JSON body
        │
2. Uvicorn receives TCP connection
   Wraps it as ASGI scope, passes to FastAPI
        │
3. FastAPI matches route: POST /chat → chat()
        │
4. Pydantic parses and validates request body
   against ChatRequest schema
   → FAIL: returns 422, handler never runs
   → PASS: ChatRequest object created
        │
5. chat() handler in routers/chat.py is called
   with validated ChatRequest
        │
6. ask_ollama(model, message) is called
   in services/ollama_service.py
        │
7. URL built from settings.ollama_base_url
   Payload formatted for Ollama /api/chat
        │
8. httpx.AsyncClient sends POST to Ollama
   *** AWAIT — event loop free for other requests ***
        │
9. Ollama receives request
   Loads model (if not already in memory)
   Runs inference, generates reply tokens
        │
10. Ollama returns JSON response
    Event loop resumes ask_ollama()
        │
11. response.raise_for_status() — checks for errors
    data = response.json() — parse body
    return data["message"]["content"] — extract text
        │
12. chat() wraps text in ChatResponse
    FastAPI serializes to JSON
        │
13. Uvicorn sends HTTP 200 response
    Client receives { "response": "..." }
```

---

## 7. Dependency Graph

```
Uvicorn
  └── main.py
        └── routers/chat.py
              ├── schemas/chat.py          (no dependencies)
              └── services/ollama_service.py
                    └── config.py
                          └── .env         (no dependencies)

External dependency:
  services/ollama_service.py → Ollama (localhost:11434) → model
```

**Dependency direction rule:** every arrow points downward only. No file imports from a file above it in the chain.

---

## 8. Setup and Installation

### Prerequisites

| Requirement | Version | Check |
|---|---|---|
| Python | 3.12+ | `python --version` |
| Ollama | Latest | `ollama --version` |

### Step 1 — Clone and navigate

```powershell
cd d:\Sisindokom\local-LLM
```

### Step 2 — Create virtual environment

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### Step 3 — Install dependencies

```powershell
pip install -r requirements.txt
```

### Step 4 — Create `.env` file

```powershell
Copy-Item .env.example .env
```

Contents of `.env`:
```
OLLAMA_BASE_URL=http://localhost:11434
```

### Step 5 — Pull the model

```powershell
ollama pull qwen2.5:7b
```

### Dependencies Explained

| Package | Version | Purpose |
|---|---|---|
| `fastapi` | 0.115.13 | Web framework — routing, validation, serialization |
| `uvicorn` | 0.34.3 | ASGI server — runs the FastAPI app, handles TCP |
| `httpx` | 0.28.1 | Async HTTP client — sends requests to Ollama |
| `pydantic-settings` | 2.9.1 | Reads `.env` file into typed `Settings` class |

---

## 9. Running the Server

### Development (with auto-reload)

```powershell
uvicorn app.main:app --reload
```

### Production (without auto-reload)

```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Expected startup output

```
INFO:     Will watch for changes in these directories: [...]
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Application startup complete.
```

### Auto-generated API docs

Once the server is running, open in a browser:

| URL | Description |
|---|---|
| `http://localhost:8000/docs` | Swagger UI — interactive API explorer |
| `http://localhost:8000/redoc` | ReDoc — clean API reference |

---

## 10. Testing the API

### Happy path

```powershell
curl -X POST http://localhost:8000/chat `
  -H "Content-Type: application/json" `
  -d '{"model": "qwen2.5:7b", "message": "Hello"}'
```

Expected:
```json
{ "response": "Hello! How can I help you today?" }
```

---

### Missing required field

```powershell
curl -X POST http://localhost:8000/chat `
  -H "Content-Type: application/json" `
  -d '{"model": "qwen2.5:7b"}'
```

Expected: `422 Unprocessable Entity` — `message` field required.

---

### Wrong field name

```powershell
curl -X POST http://localhost:8000/chat `
  -H "Content-Type: application/json" `
  -d '{"model": "qwen2.5:7b", "msg": "Hello"}'
```

Expected: `422 Unprocessable Entity` — `message` field required.

---

### Ollama not running

Stop Ollama, then:

```powershell
curl -X POST http://localhost:8000/chat `
  -H "Content-Type: application/json" `
  -d '{"model": "qwen2.5:7b", "message": "Hello"}'
```

Expected:
```json
HTTP 503
{ "detail": "Ollama is not reachable" }
```

---

### Model does not exist

```powershell
curl -X POST http://localhost:8000/chat `
  -H "Content-Type: application/json" `
  -d '{"model": "does-not-exist:latest", "message": "Hello"}'
```

Expected:
```json
HTTP 502
{ "detail": "Ollama returned an error: 404" }
```

---

## 11. Error Reference

| HTTP Status | When | Meaning |
|---|---|---|
| `200 OK` | Request succeeded | Response contains model reply |
| `422 Unprocessable Entity` | Invalid request body | Missing or wrong-type fields — caught by Pydantic before handler runs |
| `502 Bad Gateway` | Ollama error | Ollama responded but with an error status or unexpected JSON |
| `503 Service Unavailable` | Ollama unreachable | Ollama process is not running or URL is wrong |
| `504 Gateway Timeout` | Ollama too slow | Model did not respond within 120 seconds |

---

## 12. Design Decisions

### Why FastAPI over Flask

FastAPI is natively async, has built-in Pydantic validation, and auto-generates OpenAPI documentation. For an LLM gateway — where every request involves waiting for inference — async is not optional, it is a requirement.

### Why Ollama over direct model loading

Ollama manages model loading, VRAM allocation, and quantization automatically. It exposes a simple HTTP API, so the gateway remains model-agnostic. Swapping from `qwen2.5:7b` to `llama3:8b` requires no code changes — only a different value in the request body.

### Why httpx over requests

`requests` is synchronous. Inside an `async def` function, a synchronous blocking call would freeze the entire event loop for the duration of the Ollama inference (potentially seconds). `httpx.AsyncClient` uses `await` and allows the event loop to handle other requests during that wait.

### Why only the hash is stored (Phase 2 design)

Storing plain API keys means a database leak instantly compromises all clients. Storing SHA-256 hashes means a leaked database contains nothing usable — hashes cannot be reversed. This follows the same principle as password hashing.

### Why pydantic-settings over python-dotenv

`python-dotenv` loads variables into `os.environ` as strings and provides no type validation. `pydantic-settings` maps env vars directly onto typed Python fields, validates them at startup, and raises clear errors if required values are missing or malformed.

---

## 13. Known Issues and Future Work

### Known Issues (from code review)

| # | File | Severity | Issue | Status |
|---|---|---|---|---|
| 3 | `config.py` | Low | `class Config` inner class is deprecated Pydantic v1 syntax | Pending |
| 4 | `ollama_service.py` | Medium | New `AsyncClient` created per request instead of shared instance | Pending |
| 5 | `routers/chat.py` | Low | Explicitly constructs `ChatResponse(...)` instead of returning a dict | Pending |
| 6 | Project root | Low | No `pyproject.toml` — imports depend on running from correct directory | Pending |

Issues 1 and 2 from the review have been applied.

---

### Upcoming Phases

#### Phase 2 — API Key Authentication (Designed)

Add SQLite-backed API key generation and validation.

**New files:**
- `app/database.py` — SQLite connection and table initialization
- `app/schemas/key.py` — Request/response shapes for key management
- `app/services/key_service.py` — Key generation and revocation logic
- `app/dependencies/auth.py` — FastAPI dependency for request validation
- `app/routers/keys.py` — `POST /keys`, `GET /keys`, `DELETE /keys/{id}`

**New endpoints:**

| Method | Path | Description |
|---|---|---|
| `POST` | `/keys` | Generate a new API key |
| `GET` | `/keys` | List all keys (without plain values) |
| `DELETE` | `/keys/{id}` | Revoke a key by ID |

**Database schema:**
```sql
CREATE TABLE api_keys (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    NOT NULL,
    key_hash   TEXT    NOT NULL UNIQUE,
    is_active  INTEGER NOT NULL DEFAULT 1,
    created_at TEXT    NOT NULL
);
```

---

#### Phase 3 — OpenAI-Compatible API (Planned)

Expose `POST /v1/chat/completions` matching the OpenAI API specification so any OpenAI SDK can use the gateway without modification.
