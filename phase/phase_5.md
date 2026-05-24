# Phase 5 — Normalization and Recursive Chunking

## Status

Phase 5 is **fully implemented and verified** for its roadmap scope.

The backend can now convert raw Java API source records into clean, semantic, metadata-rich normalized documents and deterministic chunks.

---

## 1. Goal of Phase 5

Convert Java backend API objects into RAG-ready chunks.

Pipeline:

```text
SourceFetchResult
  -> NormalizedDocument
  -> DocumentChunk[]
```

---

## 2. Files Created or Updated

| File | Purpose |
|---|---|
| `backend/ingestion/normalizer.py` | Source-specific normalization into `NormalizedDocument` |
| `backend/ingestion/chunker.py` | Recursive character chunking into `DocumentChunk` |
| `backend/tests/test_normalizer_chunker.py` | Unit tests for normalization and chunking |
| `phase/phase_5.md` | Phase 5 documentation |
| `phase/README.md` | Phase index updated |

---

## 3. Implemented Normalization

The normalizer supports every configured source type:

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

For each source, it builds:

- stable document ID
- human-readable content
- title
- source type
- source ID
- category
- tags
- optional citation URL
- deterministic payload hash
- original raw payload for traceability

---

## 4. Human-Readable Content Strategy

Phase 5 does **not** embed raw JSON dumps.

It converts important fields into readable educational text, for example:

```text
Course: BCA.
Description: Bachelor of Computer Applications.
Level: BACHELOR.
Type: SEMESTER.
Affiliation: TRIBHUVAN_UNIVERSITY.
```

This keeps future embeddings cleaner and more useful.

---

## 5. Chunking Strategy

Chunking uses configured settings:

```text
CHUNK_SIZE_CHARS=600
CHUNK_OVERLAP_CHARS=120
```

The chunker uses recursive separator splitting with these separators:

```text
blank lines
new lines
sentence boundaries
spaces
characters
```

This mirrors LangChain `RecursiveCharacterTextSplitter` behavior while keeping the backend lightweight and dependency-safe for the VPS container.

---

## 6. Chunk Metadata

Every chunk includes:

- deterministic chunk ID
- source type
- source ID
- source title
- document ID
- chunk index
- chunk start offset
- chunk end offset
- payload hash
- tags/category

Example chunk ID:

```text
note:123:chunk:0
```

---

## 7. Traceability and Citation Safety

Every chunk can trace back to:

```text
source_type
source_id
title
payload_hash
document_id
chunk_id
```

This preserves citation traceability for later retrieval and chat phases.

---

## 8. Future-Bug Prevention

The implementation prevents common future ingestion bugs:

| Risk | Prevention |
|---|---|
| Raw JSON embedded directly | source-specific readable content builders |
| unstable change detection | deterministic SHA-256 payload hash |
| unstable chunk IDs | `{document_id}:chunk:{index}` format |
| invalid chunk offsets | `ChunkMetadata` validates `chunk_end > chunk_start` |
| chunk size drift | chunker enforces `chunk_size + overlap` maximum |
| missing source traceability | every chunk carries source/document metadata |
| URL validation bypass | inherited from hardened Phase 3 `DocumentMetadata` |

---

## 9. What Phase 5 Does Not Include

Phase 5 only normalizes and chunks documents.

Not included yet:

- embeddings
- ChromaDB writes
- vector index management
- retrieval
- chat generation
- webhook processing
- admin refresh orchestration

These belong to later phases.

---

## 10. Validation Results

Python compile passed:

```text
python3 -m py_compile $(find backend -name '*.py' | sort)
```

Container test suite passed:

```text
16 passed in 1.77s
```

The tests cover:

- stable payload hash
- course normalization
- all source type normalization
- traceable metadata
- recursive chunk splitting
- deterministic chunk IDs
- chunk offset validation
- chunk size/overlap behavior
- multi-document chunk flattening
- Phase 4 API client regression coverage

Health passed:

```json
{"status":"ok"}
```

Readiness passed:

```json
{"status":"ready","components":{"redis":{"status":"ok","detail":null},"chromadb":{"status":"ok","detail":null},"ollama":{"status":"ok","detail":null}}}
```

---

## 11. Completion Assessment

Phase 5 roadmap requirement check:

| Requirement | Status |
|---|---|
| Implement document normalizer | Done |
| Map each backend source type to canonical document format | Done |
| Implement recursive character chunking | Done |
| Use configured 600-character chunks with 120-character overlap | Done |
| Attach rich metadata to every chunk | Done |
| Generate deterministic chunk IDs | Done |
| Preserve source traceability for citations | Done |
| Unit tests for normalization and chunking | Done |

Final status:

```text
Phase 5 is complete for its defined scope.
No pending Phase 5 blocker remains.
Safe to proceed to Phase 6.
```
