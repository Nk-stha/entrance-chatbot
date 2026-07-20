# Physical Data Flow Diagram - Entrance Chatbot

> Image verification note: `image/physicaldfd.png` has been checked against the current repository implementation. A report-ready verification and explanation is available in `docs/physicaldfd.md`. The image is architecturally consistent with the implemented FastAPI, ChromaDB, Redis, Ollama, Java API integration, monitoring, and CI/CD design, with three academic qualifications: Redis is a state store rather than only a cache, "Llama 3" should be read as configurable Ollama answer generation, and "System (Metrics)" is an endpoint output rather than a persistent store.

## Source Basis and Evidence Limits

This Physical DFD represents the implementation present in this repository. It is based on:

- `backend/main.py`, `backend/config.py`, `backend/api/*`
- `backend/ingestion/*`, `backend/retrieval/*`, `backend/generation/*`, `backend/memory/*`, `backend/core/*`
- `backend/models/*`
- `docker-compose.yml`, `docker-compose.prod.yml`
- `.env.example`, `.env.production.example`
- `.github/workflows/*.yml`
- `scripts/deploy-vps.sh`, `scripts/backup-vps.sh`
- `deploy/nginx/entrance-chatbot.conf`
- existing Markdown documentation under `docs/` and `phase/`

Missing implementation artifacts not present in this workspace:

- The real frontend application source and UI screens are not in this repository. The frontend is modeled only as an external browser/client application documented by `docs/frontend-integration.md`.
- The Java/Spring backend code and database schema are not in this repository. The Java backend is modeled only as an external HTTP source system documented by the integration and source inventory docs.
- No email, SMS, payment gateway, cloud object storage, report/document generation module, message queue, or separate worker process exists in this repository.
- A nightly reconciliation function exists in code, but no startup hook, cron entry, systemd timer, or compose service wires it into runtime. It is therefore documented as callable code, not an active scheduled process.

## Notation

Yourdon & DeMarco-style notation is used:

- External Entity: `[E# Name]`
- Physical Process: `(P# Process / Program / Container)`
- Data Store: `||D# Store / File / Volume||`
- Data Flow: noun phrase on an arrow

## 1. Physical Context Diagram

```text
[E1 Existing Entrance Gateway Frontend / Browser]
    -- HTTPS/HTTP chat request, session id, optional filters -->
        (0 Entrance Chatbot Dockerized Backend System)
    <-- JSON chat response or text/event-stream events --

[E2 Entrance Gateway Java Backend API]
    -- source JSON records, webhook sync event -->
        (0 Entrance Chatbot Dockerized Backend System)
    <-- source HTTP requests, sync accepted response --

[E3 Admin / Operations Caller]
    -- X-API-Key admin refresh, sync, stats request -->
        (0 Entrance Chatbot Dockerized Backend System)
    <-- ingestion report, sync report, Chroma stats --

[E4 Monitoring / Uptime Tool]
    -- health, readiness, metrics request -->
        (0 Entrance Chatbot Dockerized Backend System)
    <-- health JSON, readiness JSON, Prometheus text metric --

[E5 GitHub Actions Runner]
    -- image tag, SSH deployment command -->
        (0 Entrance Chatbot Dockerized Backend System)
    <-- test result, build result, deploy result --

[E6 GitHub Container Registry]
    -- backend Docker image -->
        (0 Entrance Chatbot Dockerized Backend System)
    <-- pushed backend Docker image --
```

## 2. Physical Level 1 DFD

```text
[E1 Existing Entrance Gateway Frontend / Browser]
    -- POST /api/v1/chat JSON or POST /api/v1/chat/stream JSON -->
        (1.0 Process Chat HTTP Request)
    <-- ChatResponse JSON or SSE token/sources/done/error events --

(1.0 Process Chat HTTP Request)
    -- rag:session:{session_id} JSON -->
        ||D2 Redis Data Store and redis-data Volume||
(1.0 Process Chat HTTP Request)
    <-- recent chat history JSON --
        ||D2 Redis Data Store and redis-data Volume||
(1.0 Process Chat HTTP Request)
    -- Chroma query and metadata filter -->
        ||D1 ChromaDB Collection and chroma-data Volume||
(1.0 Process Chat HTTP Request)
    <-- chunk documents, metadata, distances --
        ||D1 ChromaDB Collection and chroma-data Volume||
(1.0 Process Chat HTTP Request)
    -- /api/embeddings query prompt, /api/generate prompt -->
        (4.0 Use Ollama Model Service)
(1.0 Process Chat HTTP Request)
    <-- embedding vector, streamed generated tokens --
        (4.0 Use Ollama Model Service)

[E3 Admin / Operations Caller]
    -- POST /api/v1/admin/refresh or /admin/sync with X-API-Key -->
        (2.0 Run Knowledge Ingestion and Sync)
    <-- success flag and ingestion report --

[E2 Entrance Gateway Java Backend API]
    -- POST /api/v1/webhooks/sync with X-API-Key -->
        (2.0 Run Knowledge Ingestion and Sync)
    <-- WebhookSyncAccepted JSON --

(2.0 Run Knowledge Ingestion and Sync)
    -- GET source endpoint request with optional bearer token -->
        [E2 Entrance Gateway Java Backend API]
[E2 Entrance Gateway Java Backend API]
    -- source API JSON page or source API JSON object -->
        (2.0 Run Knowledge Ingestion and Sync)

(2.0 Run Knowledge Ingestion and Sync)
    -- /api/embeddings chunk prompt -->
        (4.0 Use Ollama Model Service)
(2.0 Run Knowledge Ingestion and Sync)
    <-- embedding vector list --
        (4.0 Use Ollama Model Service)
(2.0 Run Knowledge Ingestion and Sync)
    -- chunk id, document text, embedding, metadata -->
        ||D1 ChromaDB Collection and chroma-data Volume||
(2.0 Run Knowledge Ingestion and Sync)
    -- rag:webhook:event:{event_id}, rag:payload_hash:{source_id} -->
        ||D2 Redis Data Store and redis-data Volume||
(2.0 Run Knowledge Ingestion and Sync)
    <-- processed event marker, payload hash --
        ||D2 Redis Data Store and redis-data Volume||

[E3 Admin / Operations Caller]
    -- GET /api/v1/admin/stats with X-API-Key -->
        (3.0 Serve Admin and Monitoring Status)
    <-- collection name and chunk count --

[E4 Monitoring / Uptime Tool]
    -- GET /health, /api/v1/health, /api/v1/health/ready, /api/v1/metrics -->
        (3.0 Serve Admin and Monitoring Status)
    <-- health JSON, readiness JSON, metric text --

(3.0 Serve Admin and Monitoring Status)
    -- Chroma stats or heartbeat request -->
        ||D1 ChromaDB Collection and chroma-data Volume||
(3.0 Serve Admin and Monitoring Status)
    <-- collection count or heartbeat status --
        ||D1 ChromaDB Collection and chroma-data Volume||
(3.0 Serve Admin and Monitoring Status)
    -- Redis ping -->
        ||D2 Redis Data Store and redis-data Volume||
(3.0 Serve Admin and Monitoring Status)
    <-- Redis pong or error --
        ||D2 Redis Data Store and redis-data Volume||
(3.0 Serve Admin and Monitoring Status)
    -- /api/tags request -->
        (4.0 Use Ollama Model Service)
(3.0 Serve Admin and Monitoring Status)
    <-- model tag status --
        (4.0 Use Ollama Model Service)

(4.0 Use Ollama Model Service)
    -- model files and runtime cache -->
        ||D3 Ollama Model Store and ollama-data Volume||
(4.0 Use Ollama Model Service)
    <-- model files and runtime cache --
        ||D3 Ollama Model Store and ollama-data Volume||

[E5 GitHub Actions Runner]
    -- source checkout, test command, Docker build command -->
        (5.0 Build and Deploy Runtime Stack)
    <-- CI result, image digest, deployment status --
(5.0 Build and Deploy Runtime Stack)
    -- pushed backend image -->
        [E6 GitHub Container Registry]
[E6 GitHub Container Registry]
    -- pulled backend image -->
        (5.0 Build and Deploy Runtime Stack)
(5.0 Build and Deploy Runtime Stack)
    -- compose config, env file, service snapshots, backup archives -->
        ||D4 Deployment Files, Logs, and Backups||
(5.0 Build and Deploy Runtime Stack)
    <-- compose config, env file, previous volume data --
        ||D4 Deployment Files, Logs, and Backups||
```

## 3. Physical Level 2 DFDs

### 3.1 Level 2 for 1.0 - Process Chat HTTP Request

```text
[E1 Existing Entrance Gateway Frontend / Browser]
    -- POST /api/v1/chat JSON or POST /api/v1/chat/stream JSON -->
        (1.1 Apply HTTP Middleware)

(1.1 Apply HTTP Middleware)
    -- request id, CORS headers, rate-limit key -->
        ||D2 Redis Data Store and redis-data Volume||
(1.1 Apply HTTP Middleware)
    <-- rate-limit counter or Redis failure --
        ||D2 Redis Data Store and redis-data Volume||
(1.1 Apply HTTP Middleware)
    -- validated ChatRequest model -->
        (1.2 Load Session Memory)

(1.2 Load Session Memory)
    -- rag:session:{session_id} lookup -->
        ||D2 Redis Data Store and redis-data Volume||
(1.2 Load Session Memory)
    <-- recent messages JSON --
        ||D2 Redis Data Store and redis-data Volume||
(1.2 Load Session Memory)
    -- question with recent history -->
        (1.3 Retrieve Chroma Candidates)

(1.3 Retrieve Chroma Candidates)
    -- /api/embeddings query text -->
        (4.0 Use Ollama Model Service)
(1.3 Retrieve Chroma Candidates)
    <-- query embedding vector --
        (4.0 Use Ollama Model Service)
(1.3 Retrieve Chroma Candidates)
    -- collection.query and collection.get request -->
        ||D1 ChromaDB Collection and chroma-data Volume||
(1.3 Retrieve Chroma Candidates)
    <-- dense candidates and keyword candidates --
        ||D1 ChromaDB Collection and chroma-data Volume||
(1.3 Retrieve Chroma Candidates)
    -- fused and filtered retrieval candidates -->
        (1.4 Build Prompt and Generate Answer)

(1.4 Build Prompt and Generate Answer)
    -- system prompt and user prompt -->
        (4.0 Use Ollama Model Service)
(1.4 Build Prompt and Generate Answer)
    <-- streamed generation chunks -->
        (4.0 Use Ollama Model Service)
(1.4 Build Prompt and Generate Answer)
    -- answer text and source map -->
        (1.5 Validate Citations and Persist Turn)

(1.5 Validate Citations and Persist Turn)
    -- rag:session:{session_id} updated message list -->
        ||D2 Redis Data Store and redis-data Volume||
(1.5 Validate Citations and Persist Turn)
    -- ChatResponse JSON or SSE events -->
        [E1 Existing Entrance Gateway Frontend / Browser]
```

### 3.2 Level 2 for 2.0 - Run Knowledge Ingestion and Sync

```text
[E3 Admin / Operations Caller]
    -- admin refresh/sync JSON with X-API-Key -->
        (2.1 Verify Admin API Key and Parse Sync Request)

[E2 Entrance Gateway Java Backend API]
    -- webhook JSON with X-API-Key -->
        (2.1 Verify Admin API Key and Parse Sync Request)

(2.1 Verify Admin API Key and Parse Sync Request)
    -- source type and optional source id or event payload -->
        (2.2 Claim Event and Check Payload Hash)

(2.2 Claim Event and Check Payload Hash)
    -- SET NX rag:webhook:event:{event_id}, GET rag:payload_hash:{source_id} -->
        ||D2 Redis Data Store and redis-data Volume||
(2.2 Claim Event and Check Payload Hash)
    <-- duplicate marker or previous payload hash --
        ||D2 Redis Data Store and redis-data Volume||
(2.2 Claim Event and Check Payload Hash)
    -- source fetch scope or delete scope -->
        (2.3 Fetch Source API Records)

(2.3 Fetch Source API Records)
    -- GET /courses, /colleges, /syllabus, /notes, /old-question-collections/questions, /trainings, /question-sets, /questions -->
        [E2 Entrance Gateway Java Backend API]
(2.3 Fetch Source API Records)
    <-- source API JSON records -->
        [E2 Entrance Gateway Java Backend API]
(2.3 Fetch Source API Records)
    -- SourceFetchResult list -->
        (2.4 Normalize and Chunk Source Records)

(2.4 Normalize and Chunk Source Records)
    -- DocumentChunk list -->
        (2.5 Embed and Upsert Chunks)

(2.5 Embed and Upsert Chunks)
    -- /api/embeddings chunk content -->
        (4.0 Use Ollama Model Service)
(2.5 Embed and Upsert Chunks)
    <-- embedding vectors -->
        (4.0 Use Ollama Model Service)
(2.5 Embed and Upsert Chunks)
    -- collection.upsert or collection.delete request -->
        ||D1 ChromaDB Collection and chroma-data Volume||
(2.5 Embed and Upsert Chunks)
    -- SET rag:payload_hash:{source_id} -->
        ||D2 Redis Data Store and redis-data Volume||
(2.5 Embed and Upsert Chunks)
    -- ingestion report or WebhookSyncAccepted JSON -->
        [E3 Admin / Operations Caller]
(2.5 Embed and Upsert Chunks)
    -- WebhookSyncAccepted JSON -->
        [E2 Entrance Gateway Java Backend API]
```

### 3.3 Level 2 for 3.0 - Serve Admin and Monitoring Status

```text
[E3 Admin / Operations Caller]
    -- GET /api/v1/admin/stats with X-API-Key -->
        (3.1 Verify Status Request)
[E4 Monitoring / Uptime Tool]
    -- GET /health, /api/v1/health, /api/v1/health/ready, /api/v1/metrics -->
        (3.1 Verify Status Request)

(3.1 Verify Status Request)
    -- stats request -->
        (3.2 Read Chroma Collection Stats)
(3.2 Read Chroma Collection Stats)
    -- collection.count request -->
        ||D1 ChromaDB Collection and chroma-data Volume||
(3.2 Read Chroma Collection Stats)
    <-- collection name and count --
        ||D1 ChromaDB Collection and chroma-data Volume||
(3.2 Read Chroma Collection Stats)
    -- stats JSON -->
        [E3 Admin / Operations Caller]

(3.1 Verify Status Request)
    -- readiness probe -->
        (3.3 Probe Runtime Dependencies)
(3.3 Probe Runtime Dependencies)
    -- Redis ping -->
        ||D2 Redis Data Store and redis-data Volume||
(3.3 Probe Runtime Dependencies)
    <-- Redis status --
        ||D2 Redis Data Store and redis-data Volume||
(3.3 Probe Runtime Dependencies)
    -- Chroma heartbeat request -->
        ||D1 ChromaDB Collection and chroma-data Volume||
(3.3 Probe Runtime Dependencies)
    <-- Chroma status --
        ||D1 ChromaDB Collection and chroma-data Volume||
(3.3 Probe Runtime Dependencies)
    -- /api/tags request -->
        (4.0 Use Ollama Model Service)
(3.3 Probe Runtime Dependencies)
    <-- Ollama status --
        (4.0 Use Ollama Model Service)
(3.3 Probe Runtime Dependencies)
    -- readiness JSON -->
        [E4 Monitoring / Uptime Tool]

(3.1 Verify Status Request)
    -- liveness or metrics request -->
        (3.4 Return Lightweight Service Status)
(3.4 Return Lightweight Service Status)
    -- health JSON or entrance_chatbot_up metric -->
        [E4 Monitoring / Uptime Tool]
```

### 3.4 Level 2 for 4.0 - Use Ollama Model Service

```text
(1.3 Retrieve Chroma Candidates)
    -- /api/embeddings query text -->
        (4.1 Generate Embedding Vector)
(2.5 Embed and Upsert Chunks)
    -- /api/embeddings chunk content -->
        (4.1 Generate Embedding Vector)
(4.1 Generate Embedding Vector)
    -- embedding model files -->
        ||D3 Ollama Model Store and ollama-data Volume||
(4.1 Generate Embedding Vector)
    <-- embedding model files --
        ||D3 Ollama Model Store and ollama-data Volume||
(4.1 Generate Embedding Vector)
    -- embedding vector -->
        (1.3 Retrieve Chroma Candidates)
(4.1 Generate Embedding Vector)
    -- embedding vector -->
        (2.5 Embed and Upsert Chunks)

(1.4 Build Prompt and Generate Answer)
    -- /api/generate prompt and generation options -->
        (4.2 Stream Completion Tokens)
(4.2 Stream Completion Tokens)
    -- chat model files -->
        ||D3 Ollama Model Store and ollama-data Volume||
(4.2 Stream Completion Tokens)
    <-- chat model files --
        ||D3 Ollama Model Store and ollama-data Volume||
(4.2 Stream Completion Tokens)
    -- streamed generation chunks -->
        (1.4 Build Prompt and Generate Answer)

(3.3 Probe Runtime Dependencies)
    -- /api/tags request -->
        (4.3 Report Model Service Tags)
(4.3 Report Model Service Tags)
    -- model tag status -->
        (3.3 Probe Runtime Dependencies)
```

### 3.5 Level 2 for 5.0 - Build and Deploy Runtime Stack

```text
[E5 GitHub Actions Runner]
    -- repository checkout and Python dependency install -->
        (5.1 Run CI Tests and Compile Check)
(5.1 Run CI Tests and Compile Check)
    -- pytest result and compile result -->
        [E5 GitHub Actions Runner]

[E5 GitHub Actions Runner]
    -- Docker build command and metadata -->
        (5.2 Build and Push Backend Image)
(5.2 Build and Push Backend Image)
    -- backend image tags and labels -->
        [E6 GitHub Container Registry]
[E6 GitHub Container Registry]
    -- pushed image digest -->
        (5.2 Build and Push Backend Image)

[E5 GitHub Actions Runner]
    -- SSH command and deployment secrets -->
        (5.3 Pull Image and Start Compose Stack)
(5.3 Pull Image and Start Compose Stack)
    -- pulled backend image -->
        [E6 GitHub Container Registry]
(5.3 Pull Image and Start Compose Stack)
    -- docker-compose.prod.yml, .env.production -->
        ||D4 Deployment Files, Logs, and Backups||
(5.3 Pull Image and Start Compose Stack)
    <-- production config and secret values --
        ||D4 Deployment Files, Logs, and Backups||
(5.3 Pull Image and Start Compose Stack)
    -- running containers and json-file logs -->
        ||D4 Deployment Files, Logs, and Backups||

(5.4 Backup Runtime Volumes)
    -- Docker volume archive request -->
        ||D1 ChromaDB Collection and chroma-data Volume||
(5.4 Backup Runtime Volumes)
    <-- chroma-data archive content --
        ||D1 ChromaDB Collection and chroma-data Volume||
(5.4 Backup Runtime Volumes)
    -- Docker volume archive request -->
        ||D2 Redis Data Store and redis-data Volume||
(5.4 Backup Runtime Volumes)
    <-- redis-data archive content --
        ||D2 Redis Data Store and redis-data Volume||
(5.4 Backup Runtime Volumes)
    -- Docker volume archive request -->
        ||D3 Ollama Model Store and ollama-data Volume||
(5.4 Backup Runtime Volumes)
    <-- ollama-data archive content --
        ||D3 Ollama Model Store and ollama-data Volume||
(5.4 Backup Runtime Volumes)
    -- tar.gz archives, env backup, Docker snapshots -->
        ||D4 Deployment Files, Logs, and Backups||
```

## 4. External Entities

| ID | External Entity | Physical Evidence |
|---|---|---|
| E1 | Existing Entrance Gateway Frontend / Browser | Documented in `docs/frontend-integration.md`; sends `/api/v1/chat` and `/api/v1/chat/stream` requests. |
| E2 | Entrance Gateway Java Backend API | Configured by `BACKEND_API_BASE_URL`; source endpoints listed in `backend/ingestion/api_client.py`; sends webhook events. |
| E3 | Admin / Operations Caller | Uses protected `/api/v1/admin/refresh`, `/api/v1/admin/sync`, `/api/v1/admin/stats` with `X-API-Key`. |
| E4 | Monitoring / Uptime Tool | Calls `/health`, `/api/v1/health`, `/api/v1/health/ready`, and `/api/v1/metrics`. |
| E5 | GitHub Actions Runner | Defined by `.github/workflows/ci.yml`, `build-image.yml`, and `deploy-vps.yml`. |
| E6 | GitHub Container Registry | `ghcr.io/${{ github.repository }}/backend` image target in `build-image.yml`; production compose consumes `BACKEND_IMAGE`. |

## 5. Physical Processes

| ID | Process | Actual Component |
|---|---|---|
| 0 | Entrance Chatbot Dockerized Backend System | Whole repository-deployed chatbot stack. |
| 1.0 | Process Chat HTTP Request | FastAPI app routes in `backend/api/chat.py`. |
| 1.1 | Apply HTTP Middleware | CORS, request ID, access log, rate limiter, exception handlers in `main.py` and `core/*`. |
| 1.2 | Load Session Memory | `memory/session.py` using Redis key `rag:session:{session_id}`. |
| 1.3 | Retrieve Chroma Candidates | `retrieval/retriever.py`, query rewriter, embedder, Chroma collection query/get, RRF reranker. |
| 1.4 | Build Prompt and Generate Answer | `generation/prompt_builder.py`, `generation/llm_client.py`, `generation/generator.py`. |
| 1.5 | Validate Citations and Persist Turn | `generation/citation.py`, `generation/hallucination.py`, `memory/session.py`. |
| 2.0 | Run Knowledge Ingestion and Sync | Admin/webhook routes plus `ingestion/pipeline.py`. |
| 2.1 | Verify Admin API Key and Parse Sync Request | `api/admin.py`, `api/webhooks.py`, Pydantic models. |
| 2.2 | Claim Event and Check Payload Hash | Redis keys in `ingestion/pipeline.py`. |
| 2.3 | Fetch Source API Records | `ingestion/api_client.py` HTTP client. |
| 2.4 | Normalize and Chunk Source Records | `ingestion/normalizer.py`, `ingestion/chunker.py`. |
| 2.5 | Embed and Upsert Chunks | `ingestion/embedder.py`, `retrieval/vector_store.py`. |
| 3.0 | Serve Admin and Monitoring Status | `api/admin.py`, `api/health.py`, `api/router.py`. |
| 3.1 | Verify Status Request | Admin API-key dependency or public status route dispatch. |
| 3.2 | Read Chroma Collection Stats | `VectorStore.stats()`. |
| 3.3 | Probe Runtime Dependencies | `api/health.py` Redis ping, Chroma heartbeat, Ollama tags request. |
| 3.4 | Return Lightweight Service Status | `health()` and `/metrics`. |
| 4.0 | Use Ollama Model Service | `ollama/ollama` Docker service. |
| 4.1 | Generate Embedding Vector | Ollama `/api/embeddings`, model `nomic-embed-text`. |
| 4.2 | Stream Completion Tokens | Ollama `/api/generate`, configured chat model. |
| 4.3 | Report Model Service Tags | Ollama `/api/tags`. |
| 5.0 | Build and Deploy Runtime Stack | GitHub Actions, Docker Compose, VPS scripts. |
| 5.1 | Run CI Tests and Compile Check | `.github/workflows/ci.yml`. |
| 5.2 | Build and Push Backend Image | `.github/workflows/build-image.yml`. |
| 5.3 | Pull Image and Start Compose Stack | `.github/workflows/deploy-vps.yml`, `scripts/deploy-vps.sh`, `docker-compose.prod.yml`. |
| 5.4 | Backup Runtime Volumes | `scripts/backup-vps.sh`. |

## 6. Data Stores

| ID | Data Store | Type / Location | Contents |
|---|---|---|---|
| D1 | ChromaDB Collection and chroma-data Volume | ChromaDB service, Docker volume `chroma-data` or `entrance-chatbot-chroma-data` | Collection `entrance_knowledge`, chunk ids, document text, embeddings, source metadata. |
| D2 | Redis Data Store and redis-data Volume | Redis service, Docker volume `redis-data` or `entrance-chatbot-redis-data` | Session memory JSON, webhook event markers, payload hashes, rate-limit counters. |
| D3 | Ollama Model Store and ollama-data Volume | Ollama service, Docker volume `ollama-data` or `entrance-chatbot-ollama-data` | Pulled chat and embedding model files, runtime model cache. |
| D4 | Deployment Files, Logs, and Backups | Repo files, `/opt/entrance-chatbot`, Docker json-file logs, backup directory | Compose files, `.env.production`, deploy scripts, service snapshots, volume backup tarballs, container logs. |

## 7. Data Flows

| From | To | Data Flow |
|---|---|---|
| E1 | 1.1 | POST `/api/v1/chat` JSON |
| E1 | 1.1 | POST `/api/v1/chat/stream` JSON |
| 1.1 | E1 | validation error JSON or rate-limit JSON |
| 1.1 | D2 | rate-limit key |
| D2 | 1.1 | rate-limit counter |
| 1.1 | 1.2 | validated ChatRequest model |
| 1.2 | D2 | session memory lookup |
| D2 | 1.2 | recent messages JSON |
| 1.2 | 1.3 | question with recent history |
| 1.3 | 4.1 | embedding request JSON |
| 4.1 | 1.3 | query embedding vector |
| 1.3 | D1 | Chroma collection query |
| D1 | 1.3 | retrieved documents and metadata |
| 1.3 | 1.4 | retrieval candidate list |
| 1.4 | 4.2 | generation request JSON |
| 4.2 | 1.4 | streamed generation chunks |
| 1.4 | 1.5 | answer text and source map |
| 1.5 | D2 | updated session memory JSON |
| 1.5 | E1 | ChatResponse JSON |
| 1.5 | E1 | SSE token/sources/done/error events |
| E3 | 2.1 | admin refresh request with `X-API-Key` |
| E3 | 2.1 | admin sync request with `X-API-Key` |
| E2 | 2.1 | webhook sync request with `X-API-Key` |
| 2.1 | E3 | unauthorized error JSON |
| 2.1 | 2.2 | parsed sync request or webhook payload |
| 2.2 | D2 | webhook event claim |
| 2.2 | D2 | payload hash lookup |
| D2 | 2.2 | duplicate event marker |
| D2 | 2.2 | previous payload hash |
| 2.2 | 2.3 | source fetch scope |
| 2.2 | 2.5 | source delete scope |
| 2.3 | E2 | paginated source HTTP GET |
| 2.3 | E2 | detail source HTTP GET |
| E2 | 2.3 | source JSON response |
| 2.3 | 2.4 | SourceFetchResult list |
| 2.4 | 2.5 | DocumentChunk list |
| 2.5 | 4.1 | chunk embedding request JSON |
| 4.1 | 2.5 | chunk embedding vectors |
| 2.5 | D1 | Chroma upsert payload |
| 2.5 | D1 | Chroma delete request |
| 2.5 | D2 | payload hash update |
| 2.5 | E3 | ingestion report JSON |
| 2.5 | E2 | WebhookSyncAccepted JSON |
| E3 | 3.1 | admin stats request with `X-API-Key` |
| E4 | 3.1 | health request |
| E4 | 3.1 | readiness request |
| E4 | 3.1 | metrics request |
| 3.1 | E3 | unauthorized error JSON |
| 3.1 | 3.2 | stats command |
| 3.2 | D1 | Chroma count request |
| D1 | 3.2 | collection count |
| 3.2 | E3 | stats JSON |
| 3.1 | 3.3 | readiness command |
| 3.3 | D2 | Redis ping |
| D2 | 3.3 | Redis status |
| 3.3 | D1 | Chroma heartbeat request |
| D1 | 3.3 | Chroma status |
| 3.3 | 4.3 | Ollama tags request |
| 4.3 | 3.3 | Ollama status |
| 3.3 | E4 | readiness JSON |
| 3.4 | E4 | health JSON |
| 3.4 | E4 | Prometheus metric text |
| E5 | 5.1 | GitHub checkout and test command |
| 5.1 | E5 | compile and pytest result |
| E5 | 5.2 | Docker build command |
| 5.2 | E6 | backend image push |
| E6 | 5.2 | image digest |
| E5 | 5.3 | SSH deploy command |
| 5.3 | E6 | backend image pull request |
| E6 | 5.3 | backend Docker image |
| 5.3 | D4 | running container logs |
| D4 | 5.3 | compose and environment config |
| 5.4 | D1 | Chroma volume read |
| 5.4 | D2 | Redis volume read |
| 5.4 | D3 | Ollama volume read |
| 5.4 | D4 | backup tarballs and snapshots |

## 8. Data Dictionary

### Data Flows

| Data Flow | Format / Transport | Fields / Contents |
|---|---|---|
| POST `/api/v1/chat` JSON | HTTP JSON | `message`, `session_id`, optional `filters`, optional `top_k` |
| POST `/api/v1/chat/stream` JSON | HTTP JSON | Same body as chat request |
| ChatResponse JSON | HTTP JSON | `answer`, `confidence`, `sources`, `session_id`, `allowed`, `reason` |
| SSE token/sources/done/error events | `text/event-stream` | `token`, `sources`, `confidence`, `allowed`, `reason`, `answer`, or fallback `message` |
| validation error JSON | HTTP JSON | `success=false`, `error.code`, `error.message`, optional sanitized validation details, `request_id` |
| rate-limit JSON | HTTP 429 JSON | `success=false`, `error.code=rate_limit_exceeded`, `Retry-After` |
| rate-limit key | Redis key/value | `rag:rate:{client_ip}:{window_bucket}` counter |
| validated ChatRequest model | In-process Pydantic object | Validated message, session id, filters, top k |
| session memory lookup | Redis GET | Key `rag:session:{session_id}` |
| recent messages JSON | Redis string JSON | List of `{role, content, created_at}` |
| updated session memory JSON | Redis SET with TTL | Trimmed recent user/assistant messages |
| question with recent history | In-process string/object | Current question plus formatted recent session context |
| embedding request JSON | HTTP JSON to Ollama | `model`, `prompt` |
| query embedding vector | HTTP JSON result | Numeric embedding array |
| Chroma collection query | Chroma HTTP client request | Query embedding, result count, optional metadata filter |
| retrieved documents and metadata | Chroma response | ids, documents, metadatas, distances |
| retrieval candidate list | In-process dataclass list | chunk id, document id, content, metadata, score, rank, retrieval type |
| generation request JSON | HTTP stream to Ollama | `model`, combined prompt, `stream=true`, temperature, token limit |
| streamed generation chunks | HTTP streaming JSON lines | partial response text and done flag |
| answer text and source map | In-process data | Generated answer and numbered source map |
| admin refresh request | HTTP request | Route `/api/v1/admin/refresh`, header `X-API-Key` |
| admin sync request | HTTP JSON | `source_type`, optional `source_id`, header `X-API-Key` |
| webhook sync request | HTTP JSON | `event_id`, `event_type`, `source_type`, `source_ids`, `occurred_at`, header `X-API-Key` |
| unauthorized error JSON | HTTP 401 JSON | Standard error wrapper with `Invalid admin API key` |
| parsed sync request or webhook payload | Pydantic object | Validated source/event fields |
| webhook event claim | Redis SET NX | Key `rag:webhook:event:{event_id}`, value `processed`, 7-day TTL |
| payload hash lookup | Redis GET | Key `rag:payload_hash:{source_id}` |
| duplicate event marker | Redis value | Existing processed marker |
| previous payload hash | Redis value | MD5 hash of prior source payload |
| source fetch scope | In-process instruction | Source type, source id, full source type, or all source types |
| source delete scope | In-process instruction | Source type and source id list |
| paginated source HTTP GET | HTTP request to Java backend | Supported list endpoint, page, size, sort values, optional bearer token |
| detail source HTTP GET | HTTP request to Java backend | Detail endpoint using raw source id, optional bearer token |
| source JSON response | HTTP JSON | API wrapper, Spring page, list, or object response |
| SourceFetchResult list | Pydantic list | `source_type`, `source_id`, `payload`, `fetched_at` |
| DocumentChunk list | Pydantic list | chunk id, document id, content, chunk metadata |
| chunk embedding request JSON | HTTP JSON to Ollama | Chunk text prompt and embedding model |
| chunk embedding vectors | HTTP JSON result | List of numeric vectors |
| Chroma upsert payload | Chroma request | ids, documents, embeddings, scalar metadata |
| Chroma delete request | Chroma request | metadata `source_id` or `document_id` filter |
| payload hash update | Redis SET | Key `rag:payload_hash:{source_id}`, value current MD5 |
| ingestion report JSON | HTTP JSON | success flag, counts, source types, timestamps, errors |
| WebhookSyncAccepted JSON | HTTP JSON | `accepted`, `event_id`, `source_type`, `source_ids` |
| admin stats request | HTTP request | Route `/api/v1/admin/stats`, header `X-API-Key` |
| health request | HTTP request | `/health` or `/api/v1/health` |
| readiness request | HTTP request | `/health/ready` or `/api/v1/health/ready` |
| metrics request | HTTP request | `/api/v1/metrics` |
| stats command | In-process command | Read Chroma collection stats |
| Chroma count request | Chroma client call | `collection.count()` |
| collection count | Chroma result | Collection name and integer count |
| stats JSON | HTTP JSON | `collection`, `count` |
| readiness command | In-process command | Probe Redis, ChromaDB, Ollama |
| Redis ping | Redis command | `PING` |
| Redis status | Redis result/error | `ok` or `error` with detail |
| Chroma heartbeat request | HTTP request | `/api/v1/heartbeat` on Chroma service |
| Chroma status | HTTP result/error | `ok` or `error` with detail |
| Ollama tags request | HTTP request | `/api/tags` |
| Ollama status | HTTP result/error | `ok` or `error` with detail |
| readiness JSON | HTTP JSON | `status`, `components.redis`, `components.chromadb`, `components.ollama` |
| health JSON | HTTP JSON | `{"status":"ok"}` |
| Prometheus metric text | text/plain | `entrance_chatbot_up 1` |
| GitHub checkout and test command | GitHub Actions job | checkout, setup Python, install requirements, compile, pytest |
| compile and pytest result | GitHub Actions output | pass/fail job status |
| Docker build command | GitHub Actions job | Buildx build of `backend/Dockerfile` |
| backend image push | GHCR write | Tagged Docker image |
| image digest | GHCR metadata | Pushed image digest/tag |
| SSH deploy command | GitHub Actions SSH action | VPS host/user/password secret and deploy shell script |
| backend image pull request | Docker registry request | `BACKEND_IMAGE` from `.env.production` |
| backend Docker image | Docker image layers | Production backend image |
| compose and environment config | Files | `docker-compose.prod.yml`, `.env.production` |
| running container logs | Docker json-file logs | Backend, Redis, ChromaDB, Ollama logs with size rotation |
| volume read | Docker volume mount | Data archive input from Chroma, Redis, or Ollama volume |
| backup tarballs and snapshots | Files | `.tar.gz` volume backups, env backup, docker ps snapshots |

### Data Stores

| Store | Physical Structure |
|---|---|
| D1 ChromaDB Collection and chroma-data Volume | ChromaDB 0.5.23 service; collection name from `CHROMA_COLLECTION`; persisted to `/chroma/chroma`; contains chunk ids, documents, embeddings, and scalar metadata including `source_id`, `source_type`, `title`, `chunk_id`, `document_id`. |
| D2 Redis Data Store and redis-data Volume | Redis 7 service with append-only persistence and allkeys-lru maxmemory policy; stores `rag:session:*`, `rag:webhook:event:*`, `rag:payload_hash:*`, and `rag:rate:*` keys. |
| D3 Ollama Model Store and ollama-data Volume | Ollama service mounted at `/root/.ollama`; stores configured chat model and embedding model files. |
| D4 Deployment Files, Logs, and Backups | Repository and VPS files including compose files, env templates, real `.env.production`, nginx template, Docker json-file logs, `/opt/entrance-chatbot/backups` tarballs and snapshots. |

## 9. Physical PSPECs

### PSPEC 1.1 - Apply HTTP Middleware

Assign or reuse `X-Request-ID`, bind request id to structured logs, apply CORS origins from configuration, execute Redis-backed fixed-window rate limiting for non-exempt paths, log method/path/status/duration, add response headers, and convert validation/application/unhandled errors to standard JSON responses.

### PSPEC 1.2 - Load Session Memory

Read `rag:session:{session_id}` from Redis, parse JSON into recent user/assistant messages, refresh TTL, format recent history for prompt input, and degrade to empty history if Redis read fails.

### PSPEC 1.3 - Retrieve Chroma Candidates

Strip and validate the query, optionally rewrite it, request a query embedding from Ollama, query ChromaDB for dense candidates, fetch Chroma documents for keyword matching, apply RRF reranking, apply intent and minimum relevance filters, and output final retrieval candidates.

### PSPEC 1.4 - Build Prompt and Generate Answer

Format retrieved candidates as numbered sources, combine recent history, context, and question into prompt strings, send a streaming generation request to Ollama, collect normal response chunks for non-streaming chat or emit SSE-formatted chunks for streaming chat.

### PSPEC 1.5 - Validate Citations and Persist Turn

Extract citation numbers from the generated answer, reject invalid or missing citations for factual answers, return the fixed refusal message when grounding fails, compute confidence for grounded answers, format citation source objects, and append the final user/assistant turn to Redis session memory.

### PSPEC 2.1 - Verify Admin API Key and Parse Sync Request

Read `X-API-Key`, compare it to configured `API_KEY`, reject missing or mismatched keys with 401, validate request bodies with Pydantic, and pass a typed refresh/sync/webhook request to ingestion processing.

### PSPEC 2.2 - Claim Event and Check Payload Hash

For webhook events, set `rag:webhook:event:{event_id}` with NX and TTL to prevent duplicate processing. For fetched source records, compare stored `rag:payload_hash:{source_id}` with the current payload hash and skip unchanged records.

### PSPEC 2.3 - Fetch Source API Records

Use configured backend base URL to call source endpoints for course, college, syllabus, note, old question, training, question set, and question data. Include bearer token for endpoints marked protected. Parse API wrapper, Spring page, list, or object response shapes into `SourceFetchResult` objects.

### PSPEC 2.4 - Normalize and Chunk Source Records

Map source payload fields into human-readable document content, compute a payload hash, preserve source metadata, split documents into bounded overlapping chunks, and assign deterministic chunk ids and offsets.

### PSPEC 2.5 - Embed and Upsert Chunks

Send chunk content to Ollama embeddings in small batches, validate embedding/chunk count consistency, upsert ids/documents/embeddings/metadata into ChromaDB, delete old chunks by `source_id` for targeted updates/deletes, store payload hashes in Redis, and return an ingestion report.

### PSPEC 3.1 - Verify Status Request

Route public health/readiness/metrics requests directly. For admin stats, require `X-API-Key` and return 401 for invalid credentials.

### PSPEC 3.2 - Read Chroma Collection Stats

Open or create the configured Chroma collection and return collection name plus count. Convert Chroma failures to a service-unavailable error response.

### PSPEC 3.3 - Probe Runtime Dependencies

Ping Redis, call Chroma heartbeat, call Ollama tags endpoint, and aggregate component results into `ready` only when all components return ok.

### PSPEC 3.4 - Return Lightweight Service Status

Return static liveness JSON for health routes and static Prometheus-format metric text for `/api/v1/metrics`.

### PSPEC 4.1 - Generate Embedding Vector

Receive a prompt, call Ollama `/api/embeddings` with the configured embedding model, retry transient HTTP/response failures, validate the returned embedding array, and return numeric vectors.

### PSPEC 4.2 - Stream Completion Tokens

Receive a combined system/user prompt, call Ollama `/api/generate` with `stream=true`, parse JSON lines into token chunks, stop on the done flag, and raise a service error on generation failure.

### PSPEC 4.3 - Report Model Service Tags

Serve Ollama tag status through `/api/tags` for readiness checking.

### PSPEC 5.1 - Run CI Tests and Compile Check

On pull request or push to main, check out code, set up Python 3.12, install `backend/requirements.txt`, compile Python files, and run pytest with test environment values.

### PSPEC 5.2 - Build and Push Backend Image

On push to main, tag, or manual dispatch, build `backend/Dockerfile` with Docker Buildx, generate GHCR tags, authenticate to GHCR, and push the backend image.

### PSPEC 5.3 - Pull Image and Start Compose Stack

SSH to the VPS, clone or update the repository, reset to origin/main, check required files and production env placeholders, validate Docker Compose, pull images, start services, wait for health/readiness, verify dependency ports are not publicly exposed, and report deployment completion.

### PSPEC 5.4 - Backup Runtime Volumes

Create a timestamped backup directory, copy `.env.production`, archive ChromaDB, Redis, and Ollama Docker volumes with an Alpine container, write Docker service snapshots, and prune old backup directories by retention period.

## 10. Balancing Verification

### Context to Level 1

| Context Flow | Preserved in Level 1 |
|---|---|
| Frontend chat request | E1 to 1.0 |
| Chat response / stream events | 1.0 to E1 |
| Java source records | E2 to 2.0 |
| Java webhook event | E2 to 2.0 |
| Source HTTP requests | 2.0 to E2 |
| Sync acknowledgement | 2.0 to E2 |
| Admin refresh/sync/stats requests | E3 to 2.0 and 3.0 |
| Ingestion/sync/stats responses | 2.0 and 3.0 to E3 |
| Monitoring requests | E4 to 3.0 |
| Monitoring responses | 3.0 to E4 |
| CI/CD commands and image exchange | E5/E6 to 5.0 and 5.0 to E5/E6 |

### Level 1 Process 1.0 to Level 2

Balanced. E1 inputs and outputs are preserved by 1.1 and 1.5. D1, D2, and 4.0 interactions from parent 1.0 appear in child processes 1.2, 1.3, 1.4, and 1.5.

### Level 1 Process 2.0 to Level 2

Balanced. E2 and E3 inputs/outputs are preserved by 2.1, 2.3, and 2.5. D1, D2, and 4.0 parent flows appear in 2.2 and 2.5.

### Level 1 Process 3.0 to Level 2

Balanced. E3 and E4 status inputs/outputs are preserved. D1, D2, and 4.0 status probes from parent 3.0 appear in 3.2 and 3.3.

### Level 1 Process 4.0 to Level 2

Balanced. Embedding, generation, and tag-status flows are preserved by 4.1, 4.2, and 4.3. D3 model-store access is preserved.

### Level 1 Process 5.0 to Level 2

Balanced. GitHub Actions, GHCR, deployment files, logs, backups, and runtime volume backup flows are preserved by 5.1 through 5.4.

## 11. DFD Rule Verification

| Rule | Result |
|---|---|
| No external entity directly exchanges data with another external entity inside the system boundary. | Passed |
| No external entity directly reads or writes an internal data store. | Passed |
| No data store directly exchanges data with another data store. | Passed |
| Every process has at least one input and one output. | Passed |
| Every persisted data store has read/write or documented operational use. | Passed |
| Process names are verb phrases. | Passed |
| Data flow names are noun phrases or concrete protocol payload names. | Passed |
| Level 2 child diagrams preserve parent inputs and outputs. | Passed |

## 12. Black Hole, Miracle, and Gray Hole Check

| Process | Black Hole? | Miracle? | Gray Hole? | Reason |
|---|---:|---:|---:|---|
| 1.0 Process Chat HTTP Request | No | No | No | Uses frontend request, Redis, ChromaDB, and Ollama to produce response and session update. |
| 2.0 Run Knowledge Ingestion and Sync | No | No | No | Uses admin/webhook/source data, Redis state, Ollama embeddings, and Chroma writes to produce reports/acknowledgements. |
| 3.0 Serve Admin and Monitoring Status | No | No | No | Uses status requests and runtime dependency checks to return status outputs. |
| 4.0 Use Ollama Model Service | No | No | No | Uses prompts/model store to return embeddings, tokens, or tag status. |
| 5.0 Build and Deploy Runtime Stack | No | No | No | Uses CI/CD inputs, registry, compose files, env files, and volumes to produce builds/deployments/backups. |
| 1.1 Apply HTTP Middleware | No | No | No | Request input produces validated request or error/log/rate-limit output. |
| 1.2 Load Session Memory | No | No | No | Validated request and Redis lookup produce history-enriched question. |
| 1.3 Retrieve Chroma Candidates | No | No | No | Query and stores/services produce candidate list. |
| 1.4 Build Prompt and Generate Answer | No | No | No | Candidates and Ollama output produce generated answer data. |
| 1.5 Validate Citations and Persist Turn | No | No | No | Answer/source map produce final response and session write. |
| 2.1 Verify Admin API Key and Parse Sync Request | No | No | No | Request input produces parsed instruction or unauthorized error. |
| 2.2 Claim Event and Check Payload Hash | No | No | No | Sync/event input and Redis state produce processing scope or skip. |
| 2.3 Fetch Source API Records | No | No | No | Scope input and Java API responses produce source records. |
| 2.4 Normalize and Chunk Source Records | No | No | No | Source records produce chunk list. |
| 2.5 Embed and Upsert Chunks | No | No | No | Chunks/delete scope and embeddings produce store updates and reports. |
| 3.1 Verify Status Request | No | No | No | Status request input produces routed status command or auth error. |
| 3.2 Read Chroma Collection Stats | No | No | No | Stats command and Chroma count produce stats JSON. |
| 3.3 Probe Runtime Dependencies | No | No | No | Readiness command and probes produce readiness JSON. |
| 3.4 Return Lightweight Service Status | No | No | No | Health/metrics command produces static status output. |
| 4.1 Generate Embedding Vector | No | No | No | Prompt and model files produce vector. |
| 4.2 Stream Completion Tokens | No | No | No | Prompt and model files produce streamed tokens. |
| 4.3 Report Model Service Tags | No | No | No | Tags request produces model service status. |
| 5.1 Run CI Tests and Compile Check | No | No | No | Checkout/test commands produce CI result. |
| 5.2 Build and Push Backend Image | No | No | No | Build command produces pushed image and digest. |
| 5.3 Pull Image and Start Compose Stack | No | No | No | SSH command/config/image produce running stack and logs. |
| 5.4 Backup Runtime Volumes | No | No | No | Volume/env inputs produce backup archives and snapshots. |

## 13. Implementation Notes and Conflicts

- The current webhook route uses `X-API-Key` authentication through `verify_admin_api_key`. Although some planning text mentions HMAC webhook signatures, no HMAC verification is wired into the implemented webhook route.
- The current readiness route is `/health/ready` and `/api/v1/health/ready`. Some documentation elsewhere uses `/api/v1/readiness`; that route is not present in the actual code.
- Public chat routes are explicitly exempted from the Redis-backed rate limiter in `RateLimitMiddleware`; other non-health paths are rate limited.
- Production compose publishes backend port `8002:8000`; Redis, ChromaDB, and Ollama are exposed only to the Docker network in `docker-compose.prod.yml`.
- Development compose publishes Redis, ChromaDB, and Ollama ports to the host for local development.
