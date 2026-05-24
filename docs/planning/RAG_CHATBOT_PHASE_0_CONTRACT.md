# Phase 0 — Requirement Finalization and API Contract

## Status

Phase 0 is **locked for implementation** after the decisions in this document are accepted.

This document is the source of truth for the first implementation pass.

---

## 1. System Scope

The chatbot project is **backend-only**.

It will expose HTTP/SSE APIs for the existing React/MERN frontend.

It will not build a new frontend.

It will not scrape websites.

Knowledge comes only from Spring Boot backend APIs and Spring Boot webhooks.

---

## 2. Runtime Target

Production VPS:

| Resource |            Value |
| -------- | ---------------: |
| CPU      |           4 vCPU |
| RAM      |             8 GB |
| Disk     |       75 GB NVMe |
| Swap     | 8 GB recommended |

Core runtime choices:

| Component       | Choice                         |
| --------------- | ------------------------------ |
| Backend         | FastAPI, Python 3.12, async    |
| ASGI server     | Uvicorn, 1 worker              |
| Vector DB       | ChromaDB persistent local mode |
| LLM runtime     | Ollama                         |
| Chat model      | `qwen2.5:3b`                   |
| Embedding model | `nomic-embed-text`             |
| Memory/state    | Redis 7                        |
| Deployment      | Docker Compose                 |

---

## 3. Backend Source API URLs

Local development:

```http
http://localhost:8080/api/v1
```

Production:

```http
http://api.entrancegateway.com/api/v1
```

Runtime configuration:

```env
BACKEND_API_BASE_URL=http://api.entrancegateway.com/api/v1
BACKEND_API_LOCAL_URL=http://localhost:8080/api/v1
BACKEND_API_DOCKER_URL=http://spring-backend:8080/api/v1
BACKEND_API_PAGE_SIZE=100
```

Implementation rule:

- Use `BACKEND_API_BASE_URL` as the active source URL.
- Keep local and Docker URLs as reference values only.

---

## 4. Protected API Authentication

Protected Spring Boot APIs will use a service-account JWT.

```env
CHATBOT_BACKEND_JWT=your-service-account-jwt
```

Every protected source request must send:

```http
Authorization: Bearer <CHATBOT_BACKEND_JWT>
```

Rules:

- Do not use end-user JWTs for ingestion.
- Do not log the JWT.
- If the JWT is missing and a protected source is enabled, fail ingestion with a clear configuration error.

---

## 5. Global Knowledge Sources

Initial global RAG ingestion includes:

| Source type    | Include in v1 | Notes                                        |
| -------------- | ------------: | -------------------------------------------- |
| `course`       |           Yes | Core academic knowledge                      |
| `college`      |           Yes | College discovery and metadata               |
| `syllabus`     |           Yes | Course/subject structure                     |
| `note`         |           Yes | Learning material metadata/descriptions      |
| `old_question` |           Yes | Exam preparation content                     |
| `question_set` |           Yes | Practice set metadata                        |
| `question`     |           Yes | Practice questions and answers               |
| `training`     |           Yes | Training/program offerings                   |
| `quiz_attempt` |            No | User-specific data, excluded from global RAG |
| `blog`         |            No | No backend API exists yet                    |

PDF/file extraction is **not included in v1**.

Fields such as `syllabusFile`, `pdfFilePath`, and `materialsLink` are stored as metadata/source references only.

---

## 6. Canonical Normalized Document Schema

Every API item becomes a `NormalizedDocument`:

```json
{
  "source_type": "course",
  "source_id": "course:<stable-id>",
  "title": "Human-readable title",
  "content": "Human-readable text generated from important fields.",
  "metadata": {
    "source_primary_id": "<raw backend id>",
    "category": "optional category",
    "tags": [],
    "url": null,
    "file_url": null,
    "updated_at": null,
    "version": null
  }
}
```

Required fields:

| Field         | Required | Rule                                    |
| ------------- | -------: | --------------------------------------- |
| `source_type` |      Yes | One of the known source types           |
| `source_id`   |      Yes | Deterministic and globally unique       |
| `title`       |      Yes | Fallback to source type + ID if missing |
| `content`     |      Yes | Human-readable text, not raw JSON       |
| `metadata`    |      Yes | JSON-serializable dictionary            |

---

## 7. Metadata Taxonomy

Common metadata keys:

| Key                 | Purpose                               |
| ------------------- | ------------------------------------- |
| `source_type`       | Filtering and citation grouping       |
| `source_id`         | Stable document identity              |
| `source_primary_id` | Raw backend ID                        |
| `title`             | Citation title                        |
| `category`          | Optional grouping/filtering           |
| `tags`              | Optional search/filter tags           |
| `url`               | Backend/web URL when available        |
| `file_url`          | PDF/material reference when available |
| `updated_at`        | Optional backend timestamp            |
| `version`           | Optional backend version              |
| `content_hash`      | MD5/SHA hash for no-op detection      |

Chunk-level metadata additionally includes:

| Key            | Purpose                          |
| -------------- | -------------------------------- |
| `chunk_id`     | Deterministic Chroma ID          |
| `chunk_index`  | Position inside source document  |
| `total_chunks` | Total chunks for source document |

Chunk ID format:

```text
{source_type}:{source_primary_id}:chunk:{chunk_index}
```

---

## 8. Chunking Contract

Use recursive character chunking for v1.

```env
CHUNK_SIZE_CHARS=600
CHUNK_OVERLAP_CHARS=120
```

Rules:

- Use LangChain `RecursiveCharacterTextSplitter` or an equivalent implementation.
- Preserve source metadata on every chunk.
- Avoid semantic/sentence-embedding chunking in v1 to reduce CPU/RAM pressure.

---

## 9. Retrieval Contract

Hybrid retrieval uses two tracks:

| Track                    | Top K |
| ------------------------ | ----: |
| Dense semantic search    |    20 |
| Keyword/full-text search |    20 |
| Final RRF context        |     5 |

Runtime configuration:

```env
RETRIEVAL_DENSE_TOP_K=20
RETRIEVAL_KEYWORD_TOP_K=20
RETRIEVAL_FINAL_TOP_K=5
```

Reranking:

- Use Reciprocal Rank Fusion (RRF).
- Do not load a cross-encoder model in v1.

---

## 10. Frontend API Contract

Use versioned chatbot routes.

### Non-streaming chat

```http
POST /api/v1/chat
```

Request:

```json
{
  "session_id": "uuid",
  "message": "Which colleges offer BCA?",
  "filters": {}
}
```

Response:

```json
{
  "session_id": "uuid",
  "answer": "...",
  "sources": [],
  "confidence": 0.82
}
```

### Streaming chat

```http
POST /api/v1/chat/stream
```

The frontend should use `fetch()` with `ReadableStream`, not browser `EventSource`, because the endpoint uses `POST`.

SSE-style stream format:

```text
data: {"type":"token","content":"Hello"}

data: {"type":"sources","sources":[]}

data: {"type":"done","confidence":0.82}
```

Supported event types:

| Type        | Meaning                    |
| ----------- | -------------------------- |
| `token`     | Incremental answer text    |
| `sources`   | Final citation/source list |
| `done`      | Stream completed           |
| `error`     | Recoverable stream error   |
| `heartbeat` | Keep-alive event           |

---

## 11. Conversation Memory Contract

Memory is stored in Redis by `session_id`.

```env
SESSION_TTL_SECONDS=3600
MAX_CHAT_HISTORY_MESSAGES=5
```

Rules:

- Store only the recent conversation context.
- Do not store unnecessary long-term chat history.
- Frontend owns/persists the `session_id`.

---

## 12. Webhook Contract

Spring Boot triggers FastAPI when source data changes.

```http
POST /api/v1/webhooks/sync
```

Payload:

```json
{
  "event_id": "uuid-or-unique-event-id",
  "event_type": "updated",
  "source_type": "course",
  "source_ids": ["course-uuid-1"],
  "occurred_at": "2026-05-24T12:00:00Z"
}
```

Supported `event_type` values:

| Event type     | Behavior                                              |
| -------------- | ----------------------------------------------------- |
| `created`      | Fetch changed record and upsert chunks                |
| `updated`      | Delete old chunks, fetch latest record, upsert chunks |
| `deleted`      | Delete chunks for the source record                   |
| `bulk_refresh` | Refresh all records for the source type               |

Security headers:

```http
X-Webhook-Signature: sha256=<hex_digest>
X-Webhook-Timestamp: <unix-or-iso-timestamp>
```

Signature rule:

```text
HMAC_SHA256(WEBHOOK_SECRET, timestamp + "." + raw_body)
```

Implementation rules:

- Reject missing/invalid signatures.
- Reject stale timestamps.
- Store processed `event_id` values in Redis for idempotency.
- Store payload MD5 hashes to skip no-op reprocessing.

---

## 13. Nightly Reconciliation

Run a nightly reconciliation at **2:00 AM**.

Purpose:

- Catch missed webhooks.
- Catch hard deletes.
- Compare Spring Boot source IDs with ChromaDB indexed source IDs.

Behavior:

- Missing in ChromaDB → ingest.
- Missing in Spring Boot → delete from ChromaDB.
- Hash changed → re-index.

---

## 14. Environment Variables Locked for Phase 1

```env
# Backend API sources
BACKEND_API_BASE_URL=http://api.entrancegateway.com/api/v1
BACKEND_API_LOCAL_URL=http://localhost:8080/api/v1
BACKEND_API_DOCKER_URL=http://spring-backend:8080/api/v1
BACKEND_API_PAGE_SIZE=100

# Ollama
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=qwen2.5:3b
OLLAMA_EMBED_MODEL=nomic-embed-text

# ChromaDB
CHROMA_HOST=chromadb
CHROMA_PORT=8001
CHROMA_COLLECTION=entrance_knowledge

# Redis
REDIS_URL=redis://redis:6379/0
SESSION_TTL_SECONDS=3600

# Security
API_KEY=your-admin-api-key
CHATBOT_BACKEND_JWT=your-service-account-jwt
CORS_ORIGINS=http://localhost:3000
RATE_LIMIT_REQUESTS=30
RATE_LIMIT_WINDOW=60
WEBHOOK_SECRET=your-java-backend-webhook-secret

# App
LOG_LEVEL=INFO
ENVIRONMENT=development
UVICORN_WORKERS=1
MAX_CHAT_HISTORY_MESSAGES=5
RETRIEVAL_DENSE_TOP_K=20
RETRIEVAL_KEYWORD_TOP_K=20
RETRIEVAL_FINAL_TOP_K=5
CHUNK_SIZE_CHARS=600
CHUNK_OVERLAP_CHARS=120
```

---

## 15. Phase 0 Exit Criteria

| Criterion                                | Status |
| ---------------------------------------- | -----: |
| Every ingestion source is known          |   Done |
| Every v1 source has a stable ID strategy |   Done |
| Production API URL is known              |   Done |
| Protected API auth method is known       |   Done |
| Frontend API contract is known           |   Done |
| Webhook contract is known                |   Done |
| Chunking strategy is known               |   Done |
| Retrieval/reranking strategy is known    |   Done |
| VPS resource constraints are reflected   |   Done |
| Quiz attempts excluded from global RAG   |   Done |
| PDF/file extraction deferred             |   Done |

---

## 16. Remaining Non-Blocking Items

These can be finalized during implementation without blocking Phase 1:

1. Exact production frontend origin for `CORS_ORIGINS`.
2. Actual `CHATBOT_BACKEND_JWT` value.
3. Actual `WEBHOOK_SECRET` value.
4. Whether Spring Boot can send `X-Webhook-Timestamp` as Unix seconds or ISO timestamp.
5. Whether production should use `http://api.entrancegateway.com` or `https://api.entrancegateway.com` after SSL is enabled.

---

## Phase 0 Decision

Phase 0 is complete enough to begin:

```text
Phase 1 — Docker-First Infrastructure Foundation
```
