# RAG Chatbot Implementation Phases

## Detailed Implementation Phases

### Phase 0 — Requirement Finalization and API Contract Discovery

**Goal:** Lock the knowledge-source contract before writing ingestion code.

**Key tasks:**

- Use [RAG_KNOWLEDGE_SOURCE_APIS.md](file:///home/rohan-shrestha/Desktop/entrance-gateway/entrance-chatbot/RAG_KNOWLEDGE_SOURCE_APIS.md) as the source endpoint inventory.
- Confirm backend API base URL: `http://localhost:8080/api/v1`.
- Use service-account JWT authentication for protected endpoints through `CHATBOT_BACKEND_JWT`.
- Define canonical document fields used by the normalizer.
- Define metadata taxonomy: `source_type`, `source_id`, `title`, `category`, `tags`, `updated_at`, `version`, `url`.
- Decide the exact API contract your existing frontend will consume: normal JSON chat, SSE streaming chat, or both.

**Deliverables:**

- Backend API contract notes.
- Final metadata schema.
- Final environment variable list.
- Content type mapping table.
- Final decision on which protected sources require `Authorization: Bearer <jwt>`.
- Webhook event contract for Java backend content-change notifications.

**Exit criteria:**

- Every ingestion source is known.
- Every source has a stable ID and update timestamp.
- No scraping is required or planned.

---

### Phase 1 — Docker-First Infrastructure Foundation

**Goal:** Create the runnable production-shaped environment from day one.

**Key tasks:**

- Create root `docker-compose.yml`.
- Add `docker-compose.prod.yml` override.
- Add backend Dockerfile.
- Add Redis service.
- Add ChromaDB service with persistent volume.
- Add Ollama service with model volume.
- Pull/configure `qwen2.5:7b` and embedding model.
- Add `.env.example`.
- Add `Makefile` commands for local workflows.

**Deliverables:**

- `docker-compose.yml`
- `docker-compose.prod.yml`
- `.env.example`
- `backend/Dockerfile`
- `Makefile`

**Exit criteria:**

- `docker compose up` starts all infrastructure services.
- Redis, ChromaDB, and Ollama are reachable from the backend container.
- Volumes persist ChromaDB and Ollama data.

---

### Phase 2 — Async FastAPI Core Backend

**Goal:** Build the production backend skeleton with async-first patterns.

**Key tasks:**

- Create FastAPI app with lifespan startup/shutdown.
- Add environment-based settings with Pydantic.
- Add structured JSON logging.
- Add global exception handlers.
- Add CORS and security headers.
- Add Redis-backed rate limiting.
- Add request ID middleware.
- Add retry and timeout utilities.
- Add health and readiness endpoints.

**Deliverables:**

- `backend/main.py`
- `backend/config.py`
- `backend/core/logging.py`
- `backend/core/middleware.py`
- `backend/core/exceptions.py`
- `backend/core/retry.py`
- `backend/api/health.py`

**Exit criteria:**

- Backend starts successfully in Docker.
- `/health` returns app liveness.
- `/health/ready` checks Redis, ChromaDB, and Ollama.
- Logs are structured JSON with request IDs.

---

### Phase 3 — Domain Models and Shared Schemas

**Goal:** Establish stable internal and external data contracts.

**Key tasks:**

- Define Pydantic API request/response schemas.
- Define internal domain models for raw documents, normalized documents, chunks, retrieved chunks, messages, citations, and guard results.
- Define ingestion reports and health response schemas.
- Define webhook payload schemas.

**Deliverables:**

- `backend/models/schemas.py`
- `backend/models/domain.py`

**Exit criteria:**

- All services use shared typed models.
- API schemas are ready for OpenAPI documentation.
- No untyped dictionaries are used across major service boundaries.

---

### Phase 4 — Backend API Ingestion Layer

**Goal:** Fetch authoritative content from backend APIs only.

**Key tasks:**

- Build async `httpx.AsyncClient` wrapper.
- Implement endpoint-specific fetch methods from `RAG_KNOWLEDGE_SOURCE_APIS.md`.
- Support `ApiResponse → data.content[]` extraction.
- Support direct Spring `Page → content[]` extraction.
- Support direct `List<T>` extraction.
- Support `ApiResponse.data` list/object extraction for special endpoints.
- Add pagination support.
- Add retry and timeout handling.
- Add API-key/JWT bearer-token support for protected endpoints using `CHATBOT_BACKEND_JWT`.
- Add webhook-triggered incremental sync support for Java backend content-change events.
- Normalize transient API errors into ingestion errors.

**Deliverables:**

- `backend/ingestion/api_client.py`
- Ingestion API client tests.

**Exit criteria:**

- API client can fetch all configured source types: courses, colleges, syllabus, notes, old questions, trainings, question sets, and questions.
- Client handles pagination and timeouts.
- Client handles all documented response wrapper shapes.
- Client supports bearer-token auth for protected endpoints.
- Client never uses scraping or HTML crawling.

---

### Phase 5 — Normalization and Semantic Chunking

**Goal:** Convert API objects into clean, semantic, metadata-rich chunks.

**Key tasks:**

- Implement document normalizer.
- Map each backend source type to canonical document format.
- Implement semantic chunking using sentence boundaries and similarity.
- Add fallback recursive splitting.
- Attach rich metadata to every chunk.
- Generate deterministic chunk IDs.
- Preserve source traceability for citations.

**Deliverables:**

- `backend/ingestion/normalizer.py`
- `backend/ingestion/chunker.py`
- Unit tests for normalization and chunking.

**Exit criteria:**

- Every chunk has source metadata and deterministic ID.
- Chunk size stays within configured token bounds.
- Chunk text remains semantically coherent.

---

### Phase 6 — Embedding Compute and ChromaDB Storage

**Goal:** Precompute embeddings and store them in ChromaDB with production-safe indexing assumptions.

**Key tasks:**

- Implement Ollama embedding engine.
- Batch embedding generation.
- Add retry and timeout around embedding calls.
- Create ChromaDB vector-store wrapper.
- Configure cosine distance and ANN/HNSW behavior where supported.
- Implement batch upsert.
- Implement delete by source ID.
- Implement collection statistics.
- Store raw chunk text, embedding vector, and metadata.

**Deliverables:**

- `backend/ingestion/embedder.py`
- `backend/retrieval/vector_store.py`
- ChromaDB storage tests.

**Exit criteria:**

- Embeddings are generated outside ChromaDB.
- ChromaDB stores vectors with full metadata.
- Re-ingesting the same source is idempotent.

---

### Phase 7 — Full and Incremental Sync Pipeline

**Goal:** Orchestrate the full ingestion lifecycle.

**Key tasks:**

- Implement full sync pipeline.
- Implement webhook-triggered incremental sync based on Java backend content-change events.
- Support `created`, `updated`, and `deleted` event types.
- Store webhook idempotency keys in Redis.
- Support targeted refresh by source type or source ID.
- Track ingestion metrics and errors.
- Return detailed ingestion reports.

**Deliverables:**

- `backend/ingestion/pipeline.py`
- Ingestion pipeline tests.

**Exit criteria:**

- Full sync loads all backend API knowledge into ChromaDB.
- Webhook events refresh only changed content.
- Delete events remove stale chunks from ChromaDB.
- Duplicate webhook events are ignored safely.
- Failed records are reported without crashing the entire sync.

---

### Phase 8 — Hybrid Retrieval and QR-RAG Query Reformulation

**Goal:** Retrieve the best context using modern semantic and hybrid search.

**Key tasks:**

- Implement QR-RAG query rewriting.
- Embed original and rewritten queries.
- Implement dense vector retrieval.
- Implement keyword/full-text retrieval.
- Fuse results with Reciprocal Rank Fusion.
- Deduplicate by chunk ID.
- Support metadata filters.
- Add configurable retrieval top-k values.

**Deliverables:**

- `backend/retrieval/query_rewriter.py`
- `backend/retrieval/hybrid.py`
- `backend/retrieval/retriever.py`
- Retrieval tests.

**Exit criteria:**

- Retrieval returns relevant chunks for semantic and keyword queries.
- QR-RAG gracefully falls back to the original query on failure.
- Metadata filtering works correctly.

---

### Phase 9 — Reranking Layer

**Goal:** Improve retrieved context quality before generation.

**Key tasks:**

- Add cross-encoder reranker.
- Run reranking in a thread pool to avoid blocking the async loop.
- Score query/chunk pairs.
- Return the top final context chunks.
- Add latency logging for reranking.

**Deliverables:**

- `backend/retrieval/reranker.py`
- Reranking tests.

**Exit criteria:**

- Reranker improves result ordering.
- Blocking model inference does not block FastAPI event loop.
- Low-confidence chunks are filtered out.

---

### Phase 10 — Prompt Engineering, Guardrails, and Citations

**Goal:** Generate grounded responses with hallucination prevention.

**Key tasks:**

- Implement system and user prompt builder.
- Format retrieved chunks as numbered sources.
- Add strict context-only answer instructions.
- Add refusal behavior for insufficient context.
- Implement citation extraction and source formatting.
- Implement hallucination guard.
- Validate citation references.
- Add confidence scoring.

**Deliverables:**

- `backend/generation/prompt_builder.py`
- `backend/generation/citation.py`
- `backend/generation/hallucination.py`
- Prompt and guardrail tests.

**Exit criteria:**

- Generated answers cite sources inline.
- Unsupported questions receive safe fallback responses.
- Invalid citations are detected and handled.

---

### Phase 11 — Ollama Generation and SSE Streaming

**Goal:** Stream responses from qwen2.5 to the frontend in real time.

**Key tasks:**

- Implement async Ollama client.
- Use `stream=True` generation.
- Build async generator for token streaming.
- Implement SSE event formatting.
- Add heartbeat events.
- Handle client disconnect cancellation.
- Add graceful fallback for Ollama timeouts/unavailability.

**Deliverables:**

- `backend/generation/llm_client.py`
- `backend/generation/generator.py`
- Streaming generation tests.

**Exit criteria:**

- Tokens stream incrementally through SSE.
- Long responses do not hit normal HTTP timeout behavior.
- SSE emits `token`, `sources`, `done`, `error`, and `heartbeat` events as needed.

---

### Phase 12 — Redis Conversation Memory

**Goal:** Provide session continuity without storing unnecessary long-term chat history.

**Key tasks:**

- Implement Redis-backed session memory.
- Store messages as JSON lists.
- Add configurable TTL.
- Trim history to max turns.
- Support clear-session endpoint behavior.
- Include recent history in prompt building.

**Deliverables:**

- `backend/memory/session.py`
- Session memory tests.

**Exit criteria:**

- Conversation memory persists across requests for a session.
- Old sessions expire automatically.
- Redis failure has graceful degraded behavior.

---

### Phase 13 — Public, Admin, Webhook, and Monitoring APIs

**Goal:** Expose production-ready endpoints for chat, sync, health, and operations.

**Key tasks:**

- Implement `/chat` endpoint.
- Implement `/chat/stream` endpoint.
- Implement `/admin/refresh` full sync.
- Implement `/admin/sync` incremental sync.
- Implement `/admin/stats` collection stats.
- Implement webhook-based targeted refresh.
- Protect admin endpoints with API key.
- Add `/metrics` observability hook.

**Deliverables:**

- `backend/api/chat.py`
- `backend/api/admin.py`
- `backend/api/webhooks.py`
- `backend/api/router.py`
- API endpoint tests.

**Exit criteria:**

- Chat endpoint works end-to-end.
- Admin refresh triggers ingestion.
- Webhook refresh updates targeted content.
- Protected endpoints reject unauthorized requests.

---

### Phase 14 — Existing Frontend API Integration Contract

**Goal:** Provide clean chatbot APIs and documentation that your existing frontend can consume.

**Key tasks:**

- Document `POST /chat` request/response format.
- Document `POST /chat/stream` SSE request format.
- Define SSE event types: `token`, `sources`, `done`, `error`, `heartbeat`.
- Define citation payload shape.
- Define error payload shape.
- Define session ID handling.
- Add example JavaScript/TypeScript integration snippets.
- Add CORS configuration for your existing frontend domain.
- Confirm frontend can send messages and receive streaming events.
- Confirm frontend can display source citations.

**Deliverables:**

- `docs/api.md`
- `docs/frontend-integration.md`
- Optional `docs/postman_collection.json`

**Exit criteria:**

- Existing frontend can call the chatbot API.
- Existing frontend can consume SSE token events.
- Existing frontend can render citations from backend payloads.
- No new frontend app is created in this chatbot project.

---

### Phase 15 — Testing, QA, and Production Hardening

**Goal:** Validate correctness, reliability, and deployment readiness.

**Key tasks:**

- Add ingestion tests.
- Add retrieval tests.
- Add reranking tests.
- Add generation tests.
- Add API tests.
- Add SSE streaming tests.
- Add rate-limit/security tests.
- Add Docker smoke tests.
- Test dependency failure scenarios.
- Review logs and metrics.

**Deliverables:**

- `backend/tests/conftest.py`
- `backend/tests/test_ingestion.py`
- `backend/tests/test_retrieval.py`
- `backend/tests/test_generation.py`
- `backend/tests/test_api.py`
- Final deployment checklist.

**Exit criteria:**

- Test suite passes.
- Docker stack starts cleanly.
- Health checks pass.
- Failure modes return graceful responses.
- System is ready for staging deployment.
