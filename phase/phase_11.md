# Phase 11 — Ollama Generation and SSE Streaming

## 1. Goal

Implement streaming Ollama generation and convert model output into server-sent events with token, sources, done, error, and heartbeat events.

---

## 2. Changes & Deliverables

| Feature/Task | Status | File(s) Affected |
| :--- | :--- | :--- |
| Async Ollama generation client | Done | `backend/generation/llm_client.py` |
| SSE streaming generator | Done | `backend/generation/generator.py` |
| Final streaming result capture | Done | `backend/generation/generator.py` |
| Streaming tests | Done | `backend/tests/test_streaming_generation.py`, `backend/tests/test_streaming_persistence.py` |

No known Phase 11 task remains pending in the verified scope.

---

## 3. Technical Implementation Details

- **Key Pattern:** Async iterators stream Ollama JSONL tokens into SSE-formatted events.
- **Heartbeat:** Timeout windows emit heartbeat events for slow streams.
- **Failure Handling:** Ollama failures emit safe `error` events instead of raw exceptions.
- **Persistence Support:** `stream_sse_with_result(...)` exposes the final guarded answer so API routes can persist it.

---

## 4. Verification (The "Proof")

- **Unit Tests:** Streaming tests are included in final regression.

```text
79 passed, 3 skipped in 1.86s
```

- **Live Contract Evidence:**

```text
POST /api/v1/chat/stream
200 text/event-stream; charset=utf-8
```

---

## 5. Next Steps

Phase 11 is required for Phase 12/13 because session memory and public APIs depend on streaming generation behavior.
