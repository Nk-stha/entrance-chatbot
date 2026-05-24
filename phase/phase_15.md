# Phase 15 — Testing, QA, and Production Hardening

## 1. Goal

Validate correctness, reliability, security behavior, dependency-failure handling, Docker health, and staging deployment readiness for the completed RAG backend.

This phase closes the final QA loop and verifies that all previous backend phases remain stable together.

---

## 2. Changes & Deliverables

| Feature/Task | Status | File(s) Affected |
| :--- | :--- | :--- |
| Shared API test fixtures | Done | `backend/tests/conftest.py` |
| Security and response hardening tests | Done | `backend/tests/test_security_hardening.py` |
| Dependency failure-mode tests | Done | `backend/tests/test_dependency_failures.py` |
| Redis-backed rate-limit middleware | Done | `backend/core/middleware.py` |
| Rate-limit tests for `429` and Redis failure degradation | Done | `backend/tests/test_rate_limiting.py` |
| Streaming final-answer persistence regression test | Done | `backend/tests/test_streaming_persistence.py` |
| Full ingestion/retrieval/reranking/generation/API/SSE regression re-run | Done | `backend/tests/*` |
| Docker stack smoke validation | Done | `docker-compose.yml`, runtime containers |
| Health and readiness validation | Done | `backend/api/health.py`, `make health` |
| Final deployment checklist | Done | `docs/final-deployment-checklist.md` |
| Phase index update | Done | `phase/README.md` |

No planned Phase 15 task remains pending.

---

## 3. Technical Implementation Details

- **Key Pattern:** Used targeted regression tests for final hardening instead of duplicating all earlier phase tests. Earlier phase suites remain the source of truth for ingestion, retrieval, reranking, generation, API, SSE, and memory behavior.

- **Rate limiting:** Added `RateLimitMiddleware` as a Redis-backed fixed-window limiter.
  - Uses existing settings:

```text
RATE_LIMIT_REQUESTS
RATE_LIMIT_WINDOW
```

  - Key format:

```text
rag:rate:{client_ip}:{window_bucket}
```

  - On limit breach, it returns:

```http
429 Too Many Requests
Retry-After: <window_seconds>
```

  - Error payload:

```json
{
  "success": false,
  "error": {
    "code": "rate_limit_exceeded",
    "message": "Too many requests. Please try again later.",
    "request_id": "..."
  }
}
```

- **Rate-limit failure trade-off:** If Redis is unavailable, rate limiting degrades open and logs `rate_limit_unavailable`. This preserves chatbot availability rather than failing all public requests because the limiter backend is down.

- **Streaming persistence:** Added a regression test proving the streaming path exposes the final answer for session memory persistence. This closes the earlier placeholder-memory gap.

- **Security hardening:** Tests verify:
  - request ID propagation
  - response-time header
  - API-key rejection for protected routes
  - configured API-key acceptance
  - sanitized validation errors
  - consistent 404 response shape

- **Dependency failure handling:** Tests verify:
  - Redis session memory degrades gracefully
  - Ollama streaming failure emits safe SSE error
  - guardrails refuse answers without source context

---

## 4. Verification (The "Proof")

### Unit/Regression Tests

Final full backend test run:

```text
79 passed, 3 skipped in 1.86s
```

The 3 skipped tests are documentation-mount checks that intentionally skip inside the backend Docker container because only `./backend` is mounted at `/app`. Equivalent root-level docs validation passed outside the container.

### Compile Check

```text
python3 -m py_compile $(find backend -name '*.py' | sort)
```

Result:

```text
passed
```

### Docs Cleanup Check

```text
docs cleanup: PASS
```

This confirmed old placeholder streaming-memory wording is no longer present.

### Health Check

```json
{"status":"ok"}
```

### Readiness Check

```json
{"status":"ready","components":{"redis":{"status":"ok","detail":null},"chromadb":{"status":"ok","detail":null},"ollama":{"status":"ok","detail":null}}}
```

### Docker Smoke Test

```text
entrance-chatbot-backend    Up healthy   0.0.0.0:8002->8000/tcp
entrance-chatbot-chromadb   Up           0.0.0.0:8001->8000/tcp
entrance-chatbot-ollama     Up           0.0.0.0:11435->11434/tcp
entrance-chatbot-redis      Up healthy   0.0.0.0:6379->6379/tcp
```

### Logs

Relevant structured log events covered by implementation paths:

```text
http_request
rate_limit_exceeded
rate_limit_unavailable
retrieval_started
rrf_rerank_finished
generation_stream_error
session_memory_message_appended
```

### Phase 5 Re-Verification

Phase 5 was re-tested through:

```text
tests/test_normalizer_chunker.py
```

as part of the final full regression suite.

Current evidence-based status:

```text
Phase 5 is fully completed.
No known Phase 5 pending task remains.
Phase 5 passed current regression validation.
```

No test evidence currently shows Phase 5 causing errors, failures, or future-phase regressions in the verified scope.

---

## 5. Next Steps

Phase 15 closes the implementation roadmap. The next dependency is not another backend build phase; it is staging deployment review and production rollout preparation using:

```text
docs/final-deployment-checklist.md
```

Current accurate status:

```text
Phase 15 is complete.
No known Phase 15 pending task remains.
No known roadmap task remains pending after the audit/fix pass.
```

> [!IMPORTANT]
> This means no known pending task remains based on the phase files, roadmap, tests, and validation commands. It does not mean future bugs are impossible; it means the current verified scope is passing and no known phase checklist item remains open.
