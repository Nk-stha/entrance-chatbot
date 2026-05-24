# Phase 12 — Redis Conversation Memory

## 1. Goal

Provide short-term Redis-backed conversation memory with TTL, trimming, clear behavior, and prompt-history formatting.

---

## 2. Changes & Deliverables

| Feature/Task | Status | File(s) Affected |
| :--- | :--- | :--- |
| Memory package | Done | `backend/memory/__init__.py` |
| Redis session memory | Done | `backend/memory/session.py` |
| Prompt recent-history support | Done | `backend/generation/prompt_builder.py` |
| Session memory tests | Done | `backend/tests/test_session_memory.py` |

No known Phase 12 task remains pending in the verified scope.

---

## 3. Technical Implementation Details

- **Key Pattern:** Messages are stored as JSON lists at `rag:session:{session_id}`.
- **TTL:** Reads and writes refresh `SESSION_TTL_SECONDS`.
- **Trimming:** History is limited by `MAX_CHAT_HISTORY_MESSAGES`.
- **Failure Trade-off:** Redis failures degrade to empty history or false clear result rather than crashing chat.

---

## 4. Verification (The "Proof")

- **Unit Tests:** `backend/tests/test_session_memory.py` is included in final regression.

```text
79 passed, 3 skipped in 1.86s
```

- **Live Smoke Evidence From Phase 12:**

```text
message_count: 2
history_has_user: True
history_has_assistant: True
prompt_has_history: True
cleared: True
after_clear_count: 0
```

---

## 5. Next Steps

Phase 12 is required for Phase 13 because public chat endpoints include session continuity.
