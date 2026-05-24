# Phase 4 — Backend API Ingestion Layer

## Status

Phase 4 is **implemented and verified** for the backend API client layer.

The async Java backend API client is implemented, unit-tested, real-connectivity tested, and integrated with JWT auth, retries, timeouts, pagination, wrapper extraction, targeted fetch helpers, and safe structured logging.

---

## 1. Goal of Phase 4

Fetch authoritative knowledge from Java/Spring backend APIs only.

No scraping or HTML crawling is used.

---

## 2. Files Created or Updated

| File | Purpose |
|---|---|
| `backend/ingestion/__init__.py` | Ingestion package marker |
| `backend/ingestion/api_client.py` | Async backend API ingestion client |
| `backend/tests/test_api_client.py` | Unit tests for wrappers, auth, pagination, and targeted fetch |
| `backend/pytest.ini` | Async pytest configuration |
| `backend/requirements.txt` | Added pytest test dependencies |
| `backend/config.py` | Changed default Java API URL to HTTPS |
| `.env.example` | Changed Java API URL to HTTPS |
| `.env` | Changed Java API URL to HTTPS locally |
| `phase/README.md` | Added Phase 4 status |

---

## 3. Implemented Features

| Requirement | Status |
|---|---|
| Async `httpx.AsyncClient` wrapper | Done |
| Endpoint-specific source configs | Done |
| `ApiResponse -> data.content[]` extraction | Done |
| Spring `Page -> content[]` extraction | Done |
| Direct list extraction | Done |
| `ApiResponse.data` list/object extraction | Done |
| Pagination support | Done |
| Retry handling | Done |
| Timeout handling | Done |
| JWT bearer auth for protected endpoints | Done |
| Webhook-triggered incremental sync support | Done via targeted fetch helper |
| Transient API errors normalized | Done via `ExternalServiceError` |
| Structured start/success/failure logs | Done |
| No scraping/HTML crawling | Done |

---

## 4. Source Types Supported

The client has endpoint configs for:

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

---

## 5. Auth Behavior

Protected endpoints use:

```http
Authorization: Bearer <CHATBOT_BACKEND_JWT>
```

If a protected endpoint is called without `CHATBOT_BACKEND_JWT`, the client raises a configuration error.

The token is never logged.

---

## 6. Response Shapes Supported

The client supports all documented response wrapper shapes:

```text
ApiResponse -> data.content[]
Spring Page -> content[]
Direct List<T>
ApiResponse.data list
ApiResponse.data object
```

---

## 7. Real Java Backend Connectivity

The Java backend was tested from inside the chatbot backend container.

Initial finding:

```text
http://api.entrancegateway.com/api/v1 -> HTTP 301 Cloudflare HTML redirect
```

Fix applied:

```text
https://api.entrancegateway.com/api/v1
```

Real API tests passed:

```text
GET /courses?page=0&size=100&sortBy=courseName&sortDir=asc -> HTTP 200
GET /notes?page=0&size=100&sortBy=noteName&sortDir=asc -> HTTP 200 with JWT
```

The current API returned zero records for both probes, but connectivity, JSON parsing, wrapper extraction, and JWT authorization all succeeded.

---

## 8. Incremental Sync Detail Endpoints

Likely/confirmed detail endpoint shapes were probed using invalid `test-id` values.

Most endpoints returned `400` with `expectedType: Long`, which confirms the route exists and expects a numeric ID.

Configured detail endpoints:

```text
GET /courses/{source_id}
GET /colleges/{source_id}
GET /syllabus/{source_id}
GET /notes/{source_id}
GET /old-question-collections/{source_id}
GET /trainings/{source_id}
GET /question-sets/{source_id}
GET /questions/{source_id}
```

Not used:

```text
GET /old-question-collections/questions/{source_id}
```

That route returned a resource-not-found style server response during probing, so the client uses `/old-question-collections/{source_id}` for old question detail fetches.

`fetch_source_by_id()` accepts both raw IDs and prefixed source IDs:

```text
123
note:123
course:123
```

Before calling Java, prefixed IDs are normalized to the raw ID.

---

## 9. Logging Behavior

The API client logs:

```text
backend_api_request_started
backend_api_request_succeeded
backend_api_request_failed
backend_api_page_fetched
backend_api_source_fetched
```

Logs include safe metadata only:

```text
source_type
path
params
status_code
page
count
last
total
```

Secrets such as JWT/API keys are not logged.

---

## 10. Validation Results

Python compile passed:

```text
python3 -m py_compile $(find backend -name '*.py' | sort)
```

Container tests passed:

```text
10 passed in 1.77s
```

Real backend client smoke tests passed:

```text
COURSE_OK count=0 last=True first=None
NOTE_OK count=0 last=True first=None
```

Health passed:

```json
{"status":"ok"}
```

Readiness passed:

```json
{"status":"ready","components":{"redis":{"status":"ok","detail":null},"chromadb":{"status":"ok","detail":null},"ollama":{"status":"ok","detail":null}}}
```

Markdown validation passed:

```text
phase markdown fences: PASS
```

---

## 11. What Still Remains Outside Phase 4

Phase 4 only fetches raw source data from the Java backend.

Not included yet:

- normalization into `NormalizedDocument`
- chunking
- embeddings
- ChromaDB writes
- actual webhook processing endpoint
- admin refresh endpoint
- retrieval and chat generation

These belong to later phases.

---

## 12. Next Step

Next implementation phase:

```text
Phase 5 — Normalization and Recursive Chunking
```
