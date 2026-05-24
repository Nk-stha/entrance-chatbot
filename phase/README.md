# RAG Chatbot Phase Documentation

This folder contains detailed notes for each implementation phase.

Each phase file explains:

- what was created
- what each file does
- why it exists
- how to run or verify it
- what is not included yet

## Related Documentation

The main markdown documentation is organized under:

[docs/README.md](../docs/README.md)

## Phase Files

| Phase | File | Status |
|---:|---|---|
| 1 | [phase_1.md](phase_1.md) | Infrastructure scaffold verified |
| 2 | [phase_2.md](phase_2.md) | Core FastAPI backend verified |
| 3 | [phase_3.md](phase_3.md) | Domain/shared schemas verified and hardened |
| 4 | [phase_4.md](phase_4.md) | Backend API ingestion client verified |
| 5 | [phase_5.md](phase_5.md) | Normalization and recursive chunking verified |
| 6 | [phase_6.md](phase_6.md) | Embedding and ChromaDB storage verified |
| 7 | [phase_7.md](phase_7.md) | Full and incremental sync pipeline verified |
| 8 | [phase_8.md](phase_8.md) | Hybrid retrieval and QR-RAG verified |

## Current Status

Phase 1 created and verified the Docker-first infrastructure foundation.

Phase 2 created and verified the modular FastAPI core backend.

Phase 3 created, hardened, and verified the RAG domain and shared schema contracts.

Phase 4 created and verified the async Java backend ingestion API client with JWT auth.

Phase 5 created and verified source normalization plus deterministic recursive chunking.

Phase 6 created and verified Ollama embedding client plus ChromaDB vector storage.

Phase 7 created and verified full/incremental ingestion pipeline orchestration.

Phase 8 created and verified hybrid retrieval with QR-RAG query reformulation.

Setup runbook:

[PHASE_1_INFRASTRUCTURE_SETUP.md](../docs/setup/PHASE_1_INFRASTRUCTURE_SETUP.md)

Next implementation work:

```text
Phase 9 — RRF Fusion Layer
```
