# Phase 8 — Hybrid Retrieval and QR-RAG Query Reformulation

## Status

Phase 8 is **fully implemented and verified** for its roadmap scope.

The backend can now retrieve relevant context from ChromaDB using QR-RAG query rewriting, dense vector search, keyword search, metadata filters, deduplication, and Reciprocal Rank Fusion.

---

## 1. Planned Task Checklist

| Planned task | Status |
|---|---|
| Implement QR-RAG query rewriting | Done |
| Gracefully fallback to original query on rewrite failure | Done |
| Embed original/rewritten queries | Done |
| Implement dense vector retrieval | Done |
| Implement keyword/full-text retrieval | Done |
| Fuse results with Reciprocal Rank Fusion | Done |
| Deduplicate by chunk ID | Done |
| Support metadata filters | Done |
| Add configurable retrieval top-k values | Done |
| Add retrieval tests | Done |
| Run live retrieval smoke against stored course chunks | Done |

No planned Phase 8 task remains pending.

---

## 2. Files Created or Updated

| File | Purpose |
|---|---|
| `backend/retrieval/query_rewriter.py` | QR-RAG query rewriting with fallback |
| `backend/retrieval/types.py` | Retrieval candidate/result/filter types |
| `backend/retrieval/hybrid.py` | Reciprocal Rank Fusion implementation |
| `backend/retrieval/retriever.py` | Dense + keyword hybrid retriever |
| `backend/tests/test_retrieval.py` | Retrieval unit tests |
| `phase/phase_8.md` | Phase 8 documentation |
| `phase/README.md` | Phase index updated |

---

## 3. Query Rewriting

`QueryRewriter` calls Ollama:

```http
POST /api/generate
```

It asks the model to rewrite the user question into a concise retrieval query.

If Ollama fails or returns an empty response, it logs the failure and safely falls back to the original query.

This satisfies:

```text
QR-RAG gracefully falls back to the original query on failure.
```

---

## 4. Dense Retrieval

`Retriever.dense_search()` embeds the rewritten query with Ollama embeddings, then queries ChromaDB using:

```text
query_embeddings
n_results
metadata filters
```

It returns ranked `RetrievalCandidate` objects with chunk text, metadata, source ID, source type, title, and score.

---

## 5. Keyword Retrieval

`Retriever.keyword_search()` scans stored Chroma documents and metadata for query terms.

It is intentionally lightweight for VPS deployment and provides keyword recall when semantic retrieval alone misses exact terms such as course names.

---

## 6. Hybrid Fusion

`reciprocal_rank_fusion()` merges dense and keyword candidate lists.

It:

- deduplicates by stable chunk ID
- combines rankings with RRF scoring
- returns the configured final top-k candidates

---

## 7. Metadata Filters

`RetrievalFilters` supports:

```text
source_type
source_id
category
```

Filters are converted into Chroma `where` filters.

Examples:

```python
RetrievalFilters(source_type=SourceType.COURSE)
RetrievalFilters(source_id="course:8")
```

---

## 8. Configurable Top-K

The retriever uses existing config values:

```text
RETRIEVAL_DENSE_TOP_K
RETRIEVAL_KEYWORD_TOP_K
RETRIEVAL_FINAL_TOP_K
```

---

## 9. Live Retrieval Smoke Evidence

The live ChromaDB collection contained real course chunks:

```text
total_count: 3
course_count_sample: 3
```

Query:

```text
BCA computer application course
```

QR-RAG rewrite output:

```text
BCA Computer Application College Admission Exam Search
```

Retrieval output:

```text
candidate_count: 3
```

Top result:

```text
rank: 1
chunk_id: course:8:chunk:0
source_id: course:8
title: BCA
text: Course: BCA.
Description: Bachelor in Computer Application.
Level: BACHELOR.
Type: SEMESTER.
Affiliation: TRIBHUVAN_UNIVERSITY.
```

This proves retrieval returns the expected BCA course context for a BCA query.

---

## 10. Logging Behavior

Phase 8 logs:

```text
query_rewrite_started
query_rewrite_succeeded
query_rewrite_failed_fallback
retrieval_started
retrieval_finished
```

Embedding and ChromaDB logs are inherited from Phases 6 and 7.

---

## 11. Phase 5 Re-Verification

Phase 5 remains fully complete.

It was re-tested through:

```text
tests/test_normalizer_chunker.py
```

as part of the Phase 8 full regression suite.

No pending Phase 5 blocker remains.

---

## 12. Validation Results

Python compile passed:

```text
python3 -m py_compile $(find backend -name '*.py' | sort)
```

Container test suite passed:

```text
34 passed in 2.24s
```

Health passed:

```json
{"status":"ok"}
```

Readiness passed:

```json
{"status":"ready","components":{"redis":{"status":"ok","detail":null},"chromadb":{"status":"ok","detail":null},"ollama":{"status":"ok","detail":null}}}
```

Live retrieval smoke passed with expected BCA result.

---

## 13. Completion Assessment

Phase 8 roadmap requirement check:

| Requirement | Status |
|---|---|
| Retrieval returns relevant chunks for semantic queries | Done |
| Retrieval returns relevant chunks for keyword queries | Done |
| QR-RAG gracefully falls back on failure | Done |
| Metadata filtering works correctly | Done |
| Dense + keyword results are fused | Done |
| Results are deduplicated by chunk ID | Done |

Final status:

```text
Phase 8 is complete for its defined backend retrieval scope.
No pending Phase 8 blocker remains.
Safe to proceed to Phase 9.
```
