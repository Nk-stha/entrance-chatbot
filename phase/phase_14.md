# Phase 14 — Existing Frontend API Integration Contract

## 1. Goal

Document the API contract that the existing frontend should consume without creating a new frontend app in this backend repository.

---

## 2. Changes & Deliverables

| Feature/Task | Status | File(s) Affected |
| :--- | :--- | :--- |
| Chat API contract | Done | `docs/api.md` |
| Frontend integration guide | Done | `docs/frontend-integration.md` |
| Postman collection | Done | `docs/postman_collection.json` |
| Contract docs tests | Done | `backend/tests/test_frontend_contract_docs.py` |

No known Phase 14 task remains pending in the verified scope.

---

## 3. Technical Implementation Details

- **Key Pattern:** Documented both normal JSON chat and POST-based SSE streaming because browser `EventSource` cannot send POST bodies.
- **Citation Contract:** Inline `[1]` references map to `sources[].number`.
- **CORS:** Existing frontend domains are configured through `CORS_ORIGINS`.
- **Security Trade-off:** Public chat endpoints do not require API keys; admin/webhook keys must remain server-side only.

---

## 4. Verification (The "Proof")

- **Docs Validation:**

```text
frontend contract docs: PASS
```

- **Final Regression:**

```text
79 passed, 3 skipped in 1.86s
```

- **Live Contract Evidence:**

```text
GET /api/v1/metrics
entrance_chatbot_up 1

POST /api/v1/chat/stream
200 text/event-stream; charset=utf-8
```

---

## 5. Next Steps

Phase 14 is required for frontend integration and staging rollout validation.
