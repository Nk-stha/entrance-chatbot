# Phase 8 — Hybrid Retrieval and QR-RAG

## 1. Goal

Implement query rewriting, dense retrieval, keyword retrieval, metadata filters, and hybrid retrieval output for grounded answer generation.

---

## 2. Changes & Deliverables

| Feature/Task | Status | File(s) Affected |
| :--- | :--- | :--- |
| Query rewriting | Done | `backend/retrieval/query_rewriter.py` |
| Retrieval types and filters | Done | `backend/retrieval/types.py` |
| Hybrid retrieval orchestration | Done | `backend/retrieval/retriever.py` |
| Compatibility hybrid fusion wrapper | Done | `backend/retrieval/hybrid.py` |
| Retrieval tests | Done | `backend/tests/test_retrieval.py` |

No known Phase 8 task remains pending in the verified scope.

---

## 3. Technical Implementation Details

- **Key Pattern:** Query rewriting improves recall, then dense and keyword searches are combined before final reranking.
- **Fallback:** If query rewriting fails, retrieval falls back to the original user query.
- **Trade-off:** Keyword scoring remains lightweight rather than introducing another heavy dependency.

---

## 4. Verification (The "Proof")

- **Unit Tests:** `backend/tests/test_retrieval.py` is included in final regression.

```text
79 passed, 3 skipped in 1.86s
```

- **Live Evidence From Prior Smoke:** Retrieval returned stored course chunks for BCA-related queries.

---

## 5. Next Steps

Phase 8 is required for Phase 9 because RRF reranking consumes dense and keyword candidate lists.
