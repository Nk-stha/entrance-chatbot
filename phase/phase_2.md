# Phase 2 — Async FastAPI Core Backend

## Status

Phase 2 core backend foundation is **implemented and verified**.

The backend now has a cleaner modular FastAPI structure with:

- API routers
- structured JSON logging
- request ID middleware
- access logging middleware
- centralized JSON exception handling
- shared Pydantic schemas
- retry utility
- typed health/readiness routes

---

## 1. Goal of Phase 2

The goal of Phase 2 is to move from a minimal FastAPI app to a production-ready backend skeleton.

This phase prepares the backend for future modules:

- ingestion
- webhook processing
- retrieval
- generation
- chat streaming
- admin refresh APIs

---

## 2. Files Created or Updated

| File | Purpose |
|---|---|
| `backend/api/__init__.py` | API package marker |
| `backend/api/health.py` | Health/readiness API router |
| `backend/core/__init__.py` | Core package marker |
| `backend/core/logging.py` | Structured JSON logging setup |
| `backend/core/middleware.py` | Request ID and access logging middleware |
| `backend/core/exceptions.py` | Central error classes and handlers |
| `backend/core/retry.py` | Async retry helper |
| `backend/models/__init__.py` | Models package marker |
| `backend/models/schemas.py` | Shared Pydantic response schemas |
| `backend/main.py` | Refactored app entrypoint |

---

## 3. `backend/api/health.py`

This file now owns the health endpoints.

Endpoints:

```http
GET /health
GET /health/ready
GET /api/v1/health
GET /api/v1/health/ready
```

### `/health`

Checks only whether FastAPI is alive.

Response:

```json
{"status":"ok"}
```

### `/health/ready`

Checks whether dependent services are reachable:

- Redis
- ChromaDB
- Ollama

Example response:

```json
{
  "status": "ready",
  "components": {
    "redis": {"status": "ok", "detail": null},
    "chromadb": {"status": "ok", "detail": null},
    "ollama": {"status": "ok", "detail": null}
  }
}
```

---

## 4. `backend/core/logging.py`

This configures structured JSON logging using `structlog`.

Example log:

```json
{
  "method": "GET",
  "path": "/health",
  "status_code": 200,
  "duration_ms": 0.72,
  "event": "http_request",
  "request_id": "uuid",
  "level": "info",
  "timestamp": "2026-05-24T15:16:22Z"
}
```

Why this matters:

- easier debugging
- better production logs
- request tracing through `request_id`

---

## 5. `backend/core/middleware.py`

This file adds two middleware classes.

### `RequestIDMiddleware`

Adds a unique request ID to every request.

It reads existing header:

```http
X-Request-ID
```

or generates a new UUID.

It also returns the ID in response headers:

```http
X-Request-ID: <uuid>
```

### `AccessLogMiddleware`

Logs:

- HTTP method
- request path
- status code
- duration in milliseconds

It also adds:

```http
X-Response-Time-MS: <duration>
```

---

## 6. `backend/core/exceptions.py`

This file centralizes API error handling.

Created error classes:

| Class | Purpose |
|---|---|
| `AppError` | Base application error |
| `ConfigurationError` | Missing/invalid configuration |
| `ExternalServiceError` | Redis/Chroma/Ollama/Spring API failure |

It also registers handlers for:

- custom app errors
- validation errors
- HTTP errors
- unexpected errors

Standard error shape:

```json
{
  "success": false,
  "error": {
    "code": "validation_error",
    "message": "Request validation failed.",
    "request_id": "uuid"
  }
}
```

---

## 7. `backend/core/retry.py`

This file provides:

```python
retry_async(...)
```

It retries failed async operations with exponential backoff.

Future use cases:

- Spring Boot API calls
- Ollama API calls
- ChromaDB operations
- webhook refresh jobs

---

## 8. `backend/models/schemas.py`

This file defines shared Pydantic response schemas.

Current schemas:

| Schema | Purpose |
|---|---|
| `ComponentHealth` | Individual dependency health |
| `HealthResponse` | Liveness response |
| `ReadinessResponse` | Readiness response |
| `ErrorDetail` | Error body details |
| `ErrorResponse` | Standard error response wrapper |

---

## 9. `backend/main.py`

The app entrypoint now:

1. loads settings
2. configures logging
3. creates shared HTTP and Redis clients during lifespan
4. adds CORS middleware
5. adds request/access middleware
6. registers exception handlers
7. includes health routes twice:
   - unversioned `/health`
   - versioned `/api/v1/health`

Swagger is still enabled for development:

```http
http://localhost:8002/docs
```

---

## 10. Validation Results

The following validation passed:

```bash
python3 -m py_compile backend/main.py backend/config.py backend/api/health.py backend/core/logging.py backend/core/middleware.py backend/core/exceptions.py backend/core/retry.py backend/models/schemas.py
```

Docker backend rebuild passed:

```bash
docker compose up -d --build backend
```

Health check passed:

```bash
make health
```

Output:

```json
{"status":"ok"}
{"status":"ready","components":{"redis":{"status":"ok","detail":null},"chromadb":{"status":"ok","detail":null},"ollama":{"status":"ok","detail":null}}}
```

Swagger check passed:

```http
HTTP/1.1 200 OK
```

for:

```http
http://localhost:8002/docs
```

---

## 11. Important Fix Made During Phase 2

A `structlog` processor bug was found and fixed.

Wrong:

```python
structlog.processors.StackInfoRenderer
```

Correct:

```python
structlog.processors.StackInfoRenderer()
```

Without this fix, backend startup failed.

Now backend starts correctly and logs JSON events.

---

## 12. What Phase 2 Does Not Yet Include

Phase 2 does not yet implement:

- Spring Boot ingestion client
- normalizer/chunker
- ChromaDB collection wrapper
- embeddings
- retrieval
- chat API
- SSE streaming
- webhook endpoint
- admin refresh endpoint
- rate limiting implementation

These come in later phases.

---

## 13. Next Phase

Next implementation phase:

```text
Phase 3 — Domain Models and Shared Schemas
```
