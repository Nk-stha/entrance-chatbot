# Phase 6 — Embedding Compute and ChromaDB Storage

## Status

Phase 6 is **fully implemented and verified** for its roadmap scope.

The backend can now generate embeddings outside ChromaDB and store chunk vectors with full metadata in ChromaDB.

---

## 1. Goal of Phase 6

Precompute embeddings and store them in ChromaDB with production-safe indexing assumptions.

Pipeline:

```text
DocumentChunk[]
  -> Ollama embeddings
  -> ChromaDB collection
```

---

## 2. Files Created or Updated

| File | Purpose |
|---|---|
| `backend/ingestion/embedder.py` | Ollama embedding client |
| `backend/retrieval/__init__.py` | Retrieval package marker |
| `backend/retrieval/vector_store.py` | ChromaDB vector-store wrapper |
| `backend/tests/test_embedder_vector_store.py` | Unit tests for embedding and vector storage |
| `phase/phase_6.md` | Phase 6 documentation |
| `phase/README.md` | Phase index updated |

---

## 3. Ollama Embedding Engine

Implemented `OllamaEmbedder`.

It calls:

```http
POST /api/embeddings
```

Payload:

```json
{
  "model": "nomic-embed-text",
  "prompt": "chunk text"
}
```

The embedding engine includes:

- async `httpx.AsyncClient`
- timeout handling
- retry with exponential backoff
- response validation
- empty-text rejection
- safe structured logs
- batch helpers for VPS-safe processing

---

## 4. Batch Embedding

Implemented:

```python
embed_texts(texts, batch_size=8)
embed_chunks(chunks, batch_size=8)
```

The implementation embeds in deterministic input order and uses small batches to avoid memory pressure on VPS deployment.

---

## 5. ChromaDB Vector Store

Implemented `VectorStore`.

Capabilities:

- get/create Chroma collection
- configure cosine distance metadata
- upsert chunks with externally generated embeddings
- delete all chunks by `source_id`
- delete all chunks by `document_id`
- return collection stats
- serialize Pydantic metadata to Chroma-compatible scalar values

Collection metadata:

```json
{"hnsw:space": "cosine"}
```

Chroma anonymized telemetry is disabled to avoid noisy production logs.

---

## 6. Idempotency

Chunk IDs are deterministic from Phase 5:

```text
{document_id}:chunk:{index}
```

Chroma uses `upsert`, not `add`, so re-ingesting the same source replaces existing chunk vectors with the same IDs instead of duplicating them.

This satisfies the Phase 6 idempotency requirement.

---

## 7. Stored Data

For every chunk, Chroma stores:

- chunk ID
- raw chunk text
- embedding vector
- scalar metadata

Metadata includes:

```text
source_type
source_id
title
category
tags
payload_hash
document_id
chunk_id
chunk_index
chunk_start
chunk_end
```

---

## 8. Logging Behavior

Embedding logs:

```text
ollama_embedding_started
ollama_embedding_succeeded
ollama_embedding_failed
ollama_embedding_batch_started
ollama_embedding_batch_succeeded
```

Vector store logs:

```text
chroma_chunks_upserted
chroma_chunks_upsert_failed
chroma_source_deleted
chroma_source_delete_failed
chroma_document_deleted
chroma_document_delete_failed
chroma_stats_failed
```

No secrets are logged.

---

## 9. Live ChromaDB Smoke Test

A real ChromaDB smoke test was run inside the backend container using deterministic dummy embeddings.

Result:

```text
{'upserted': 1, 'collection': 'entrance_knowledge', 'count_after_upsert_at_least': True}
```

This verified:

- real ChromaDB connection
- collection creation/access
- vector upsert
- metadata storage path
- delete by source ID
- collection stats

The smoke record was deleted after the test.

---

## 10. What Phase 6 Does Not Include

Phase 6 does not orchestrate full ingestion jobs yet.

Not included yet:

- full sync pipeline
- webhook endpoint processing
- Redis idempotency keys
- scheduled reconciliation
- retrieval search endpoint
- chat generation

Those belong to later phases.

---

## 11. Validation Results

Python compile passed:

```text
python3 -m py_compile $(find backend -name '*.py' | sort)
```

Container test suite passed:

```text
22 passed in 2.35s
```

Live ChromaDB smoke test passed:

```text
upserted: 1
collection: entrance_knowledge
count_after_upsert_at_least: True
```

Health passed:

```json
{"status":"ok"}
```

Readiness passed:

```json
{"status":"ready","components":{"redis":{"status":"ok","detail":null},"chromadb":{"status":"ok","detail":null},"ollama":{"status":"ok","detail":null}}}
```

---

## 12. Completion Assessment

Phase 6 roadmap requirement check:

| Requirement | Status |
|---|---|
| Implement Ollama embedding engine | Done |
| Batch embedding generation | Done |
| Retry and timeout around embedding calls | Done |
| ChromaDB vector-store wrapper | Done |
| Configure cosine distance / HNSW where supported | Done |
| Batch upsert | Done |
| Delete by source ID | Done |
| Collection statistics | Done |
| Store raw chunk text, embedding vector, and metadata | Done |
| Embeddings generated outside ChromaDB | Done |
| ChromaDB stores vectors with full metadata | Done |
| Re-ingesting same source is idempotent | Done via deterministic IDs + upsert |
| ChromaDB storage tests | Done |

Final status:

```text
Phase 6 is complete for its defined scope.
No pending Phase 6 blocker remains.
Safe to proceed to Phase 7.
```
