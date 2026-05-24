# Phase 3 — Domain Models and Shared Schemas

## Status

Phase 3 is **implemented, roadmap-complete, and verified**.

This phase creates the typed contracts that future ingestion, retrieval, webhook, guardrail, and chat code will use.

---

## 1. Goal of Phase 3

The goal is to define stable Pydantic models for the RAG backend before adding business logic.

These models make later phases safer because every pipeline stage will share the same data contracts.

---

## 2. Files Created or Updated

| File | Purpose |
|---|---|
| `backend/models/domain.py` | Source, raw fetch, document, metadata, and chunk models |
| `backend/models/retrieval.py` | Retrieved chunk and retrieval request/result models |
| `backend/models/chat.py` | Message, chat, citation, and SSE event models |
| `backend/models/guardrails.py` | Guardrail and hallucination-prevention result models |
| `backend/models/webhook.py` | Java backend webhook sync models |
| `backend/models/ingestion.py` | Ingestion/refresh status and result models |
| `backend/models/schemas.py` | Health and standard error response schemas |
| `backend/models/__init__.py` | Central model exports |
| `backend/api/schemas.py` | Schema-only Swagger validation routes |
| `backend/main.py` | Registered schema routes and bumped version to `0.3.0` |

---

## 3. Roadmap Requirement Coverage

Phase 3 roadmap requirements from `RAG_CHATBOT_IMPLEMENTATION_PHASES.md`:

| Requirement | Status |
|---|---|
| Pydantic API request/response schemas | Done |
| Raw document/source fetch models | Done |
| Normalized document models | Done |
| Chunk models | Done |
| Retrieved chunk models | Done |
| Message models | Done |
| Citation models | Done |
| Guard result models | Done |
| Ingestion report models | Done |
| Health response schemas | Done |
| Webhook payload schemas | Done |
| OpenAPI/Swagger schema visibility | Done |

---

## 4. Domain Models

File:

```text
backend/models/domain.py
```

### `SourceType`

Supported v1 Java backend source types:

```text
course
college
syllabus
note
old_question
training
question_set
question
```

### `SourceFetchResult`

Represents raw source API output before normalization.

### `DocumentMetadata`

Canonical metadata fields:

```text
source_type
source_id
title
category
tags
updated_at
version
url
payload_hash
```

### `NormalizedDocument`

Represents one normalized source item before chunking.

### `DocumentChunk`

Represents one chunk ready for embedding and vector storage.

---

## 5. Retrieval Models

File:

```text
backend/models/retrieval.py
```

Created:

| Model | Purpose |
|---|---|
| `RetrievalMethod` | `dense`, `keyword`, `rrf` |
| `RetrievedChunk` | Retrieved chunk with score, rank, method |
| `RetrievalRequest` | Internal retrieval query contract |
| `RetrievalResult` | Internal retrieval result contract |

---

## 6. Chat Models

File:

```text
backend/models/chat.py
```

Created:

| Model | Purpose |
|---|---|
| `ChatMessage` | Stored user/assistant/system message |
| `ChatRequest` | Non-streaming chat request |
| `StreamChatRequest` | SSE streaming chat request |
| `ChatResponse` | Final chat answer with citations |
| `Citation` | Source citation returned to frontend |
| `StreamEvent` | SSE event payload |
| `StreamEventType` | `token`, `citation`, `done`, `error` |

Future endpoints:

```http
POST /api/v1/chat
POST /api/v1/chat/stream
```

---

## 7. Guardrail Models

File:

```text
backend/models/guardrails.py
```

Created:

| Model | Purpose |
|---|---|
| `GuardrailDecision` | `allow`, `refuse`, `fallback` |
| `GuardrailReason` | in-scope/out-of-scope/no-context/unsafe/low-confidence |
| `GuardrailResult` | Base guard result |
| `AnswerGuardResult` | Generated-answer guard result |

These prepare future hallucination-prevention and answer-safety checks.

---

## 8. Webhook Models

File:

```text
backend/models/webhook.py
```

Created:

| Model | Purpose |
|---|---|
| `WebhookEventType` | `created`, `updated`, `deleted`, `refresh` |
| `WebhookSyncRequest` | Payload from Java backend |
| `WebhookSyncAccepted` | Accepted response |
| `WebhookHeaders` | HMAC signature header container |

Future endpoint:

```http
POST /api/v1/webhooks/sync
```

---

## 9. Ingestion Models

File:

```text
backend/models/ingestion.py
```

Created:

| Model | Purpose |
|---|---|
| `IngestionStatus` | `success`, `partial`, `failed`, `skipped` |
| `SourceIngestionStats` | Per-source ingestion counters |
| `IngestionResult` | Final ingestion job result |
| `RefreshRequest` | Admin refresh request body |
| `RefreshAccepted` | Admin refresh accepted response |

Future endpoint:

```http
POST /api/v1/admin/refresh
```

---

## 10. Swagger Schema Routes

File:

```text
backend/api/schemas.py
```

These are temporary schema-only routes for development validation.

They make Phase 3 models visible in Swagger/OpenAPI before real chat/webhook/admin endpoints are implemented.

Routes:

```http
POST /api/v1/schemas/examples/source-fetch
POST /api/v1/schemas/examples/document
POST /api/v1/schemas/examples/normalized-document
POST /api/v1/schemas/examples/retrieval
POST /api/v1/schemas/examples/message
POST /api/v1/schemas/examples/chat
POST /api/v1/schemas/examples/chat-stream
POST /api/v1/schemas/examples/webhook
POST /api/v1/schemas/examples/refresh
GET  /api/v1/schemas/examples/guardrail
```

Swagger:

```http
http://localhost:8002/docs
```

---

## 11. Future-Bug Prevention Changes

To reduce future timestamp bugs, default timestamps now use timezone-aware UTC:

```python
datetime.now(timezone.utc)
```

This avoids naive datetime ambiguity during sync, ingestion, and webhook processing.

Additional review hardening fixes were applied:

| Review issue | Fix |
|---|---|
| `HttpUrl` validation bypassed by `str` union | `url` is now `HttpUrl | None` only |
| `chunk_end > chunk_start` missing | Added `ChunkMetadata` model validator |
| Debug endpoint accessible everywhere | `/debug/settings` now returns 404 outside local/dev/test |
| Validation errors may leak input | Error responses now omit rejected `input` values |
| Runtime parameters under-validated | Added bounds and cross-field config checks |
| Phase 3 model files not fully documented | Phase doc now lists all model files |

---

## 12. Final Verification Results

Python compile passed:

```text
compile OK
```

Backend rebuild passed:

```bash
docker compose up -d --build backend
```

Health check passed:

```json
{"status":"ok"}
```

Readiness passed:

```json
{"status":"ready","components":{"redis":{"status":"ok","detail":null},"chromadb":{"status":"ok","detail":null},"ollama":{"status":"ok","detail":null}}}
```

OpenAPI roadmap validation passed:

```text
version: 0.3.0
schema_count: 34
Phase 3 roadmap contract OK
```

Container model smoke test passed:

```text
all required Phase 3 models instantiate OK
```

Hardening smoke tests passed:

```text
invalid URL rejected: PASS
bad chunk offsets rejected: PASS
validation error sanitized: PASS
```

Swagger check passed:

```text
HTTP/1.1 200 OK
```

Markdown fence validation passed:

```text
OK phase/README.md
OK phase/phase_1.md
OK phase/phase_2.md
OK phase/phase_3.md
```

---

## 13. Important Note

Some Pydantic models appear in OpenAPI with generated names like:

```text
NormalizedDocument-Input
NormalizedDocument-Output
DocumentChunk-Input
DocumentChunk-Output
```

This is normal for models with flexible fields and different input/output schema generation.

---

## 14. What Phase 3 Does Not Yet Include

Phase 3 does not implement business logic yet.

Not included yet:

- Java backend API client
- source normalization logic
- chunking implementation
- embeddings
- ChromaDB writes
- retrieval implementation
- actual chat endpoint
- actual SSE endpoint
- actual webhook endpoint
- actual admin refresh endpoint

---

## 15. Final Assessment

Phase 3 satisfies the roadmap requirements and is safe to use as the model foundation for Phase 4.

No current runtime error was detected in Phase 3 validation.

Future bugs cannot be guaranteed impossible, but the current schema contracts compile, load in Docker, appear in OpenAPI, instantiate correctly, and keep the backend healthy.

---

## 16. Next Phase

Next implementation phase:

```text
Phase 4 — Backend API Client and Auth
```
