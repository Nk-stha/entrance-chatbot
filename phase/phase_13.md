# Phase 13 — Public, Admin, Webhook, and Monitoring APIs

## 1. Goal

Expose production-ready backend API endpoints for public chat, streaming chat, admin sync operations, webhook refresh, collection stats, and metrics.

This phase makes the RAG backend callable by external clients while protecting operational/admin routes with an API key.

---

## 2. Changes & Deliverables

| Feature/Task | Status | File(s) Affected |
| :--- | :--- | :--- |
| Public non-streaming chat endpoint `POST /api/v1/chat` | Done | `backend/api/chat.py` |
| Public streaming chat endpoint `POST /api/v1/chat/stream` | Done | `backend/api/chat.py` |
| Streaming endpoint persists actual final answer to Redis memory | Done | `backend/api/chat.py`, `backend/generation/generator.py`, `backend/tests/test_streaming_persistence.py` |
| Admin full refresh endpoint `POST /api/v1/admin/refresh` | Done | `backend/api/admin.py` |
| Admin incremental sync endpoint `POST /api/v1/admin/sync` | Done | `backend/api/admin.py` |
| Admin collection stats endpoint `GET /api/v1/admin/stats` | Done | `backend/api/admin.py` |
| Webhook targeted refresh endpoint `POST /api/v1/webhooks/sync` | Done | `backend/api/webhooks.py` |
| API-key protection for admin and webhook routes | Done | `backend/api/admin.py`, `backend/api/webhooks.py` |
| Lightweight metrics endpoint `GET /api/v1/metrics` | Done | `backend/api/router.py` |
| Main router wiring under `/api/v1` | Done | `backend/api/router.py`, `backend/main.py` |
| API endpoint regression tests | Done | `backend/tests/test_api_endpoints.py` |

No planned Phase 13 task remains pending.

---

## 3. Technical Implementation Details

- **Key Pattern:** FastAPI `APIRouter` modules split endpoints by responsibility:
  - `backend/api/chat.py` for public chat routes.
  - `backend/api/admin.py` for protected admin routes.
  - `backend/api/webhooks.py` for protected webhook refresh.
  - `backend/api/router.py` for central API router and metrics.

- **Chat flow:** `/chat` performs:

```text
Redis history -> hybrid retrieval -> prompt build -> Ollama generation -> citation guardrail -> Redis memory save -> JSON response
```

- **Streaming flow:** `/chat/stream` performs:

```text
Redis history -> hybrid retrieval -> prompt build -> SSE streaming -> capture final done/error result -> Redis memory save
```

- **Streaming persistence fix:** The earlier placeholder behavior was removed. The streaming generator now exposes `stream_sse_with_result(...)`, allowing the API route to persist the real final guarded assistant answer.

- **Admin protection:** Admin and webhook endpoints require:

```http
X-API-Key: <API_KEY>
```

- **Trade-off:** The `/metrics` endpoint is intentionally lightweight:

```text
entrance_chatbot_up 1
```

This keeps Phase 13 simple while leaving room for a richer Prometheus exporter later.

---

## 4. Verification (The "Proof")

### Unit/Regression Tests

Final full backend regression after the streaming persistence fix:

```text
79 passed, 3 skipped in 1.86s
```

Relevant tests:

```text
backend/tests/test_api_endpoints.py
backend/tests/test_streaming_persistence.py
backend/tests/test_streaming_generation.py
backend/tests/test_session_memory.py
```

### Smoke Tests

Metrics endpoint:

```text
GET /api/v1/metrics
entrance_chatbot_up 1
```

Unauthorized admin stats:

```text
GET /api/v1/admin/stats
401
Invalid admin API key
```

Authorized admin stats:

```json
{"collection":"entrance_knowledge","count":3}
```

Streaming route content type:

```text
POST /api/v1/chat/stream
200 text/event-stream; charset=utf-8
```

### Logs

Example structured log events observed during API/retrieval flows:

```text
retrieval_started
query_rewrite_started
ollama_embedding_started
rrf_rerank_finished
prompt_build_started
http_request
```

---

## 5. Next Steps

Phase 13 is required for Phase 14 because the frontend integration contract depends on stable public API paths, SSE event behavior, admin stats, webhook sync, and metrics.

Current accurate status:

```text
Phase 13 is complete.
No known Phase 13 pending task remains.
Streaming memory persistence is now fixed and verified.
```
