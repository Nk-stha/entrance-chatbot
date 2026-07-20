# Physical Data Flow Diagram Verification - Entrance Chatbot

## 1. Purpose

This document verifies the Physical Data Flow Diagram (Physical DFD) shown in `image/physicaldfd.png` against the actual Entrance Chatbot implementation in this repository. It is written in report format so it can be used as an academic explanation of the system's physical design, data movement, processing components, and persistent storage.

## 2. Verification Verdict

The Physical DFD in `image/physicaldfd.png` mostly matches the implemented system. It correctly represents the main runtime architecture:

- A browser or frontend sends chat requests to the chatbot backend.
- The chatbot backend retrieves knowledge from a Chroma vector database.
- Redis is used for session memory, cache-like state, webhook idempotency, payload hashes, and rate-limit counters.
- The Java backend API is the external source of authoritative Entrance Gateway data.
- Ollama is used for embeddings during ingestion and for LLM answer generation during chat.
- Monitoring tools call health, readiness, and metrics endpoints.
- GitHub Actions and a container registry are used for build and deployment flow.

However, the image is a simplified physical DFD. For academic accuracy, the following qualifications should be stated:

| Diagram Item | Verification Result | Explanation |
|---|---|---|
| `Entrance Chatbot System (Docker App)` | Matches | The implemented system is a Dockerized FastAPI backend supported by Redis, ChromaDB, and Ollama containers. |
| `User (Browser)` | Matches | The repository does not contain frontend source code, but `docs/frontend-integration.md` documents a browser/client integration that calls the chatbot API. |
| `Java Backend (API)` | Matches as an external system | The chatbot fetches source data from a configured Java backend API using `BACKEND_API_BASE_URL`. The Java backend implementation itself is not present in this repository. |
| `Admin (Ops User)` | Matches | Admin operations are exposed through protected endpoints such as `/api/v1/admin/refresh`, `/api/v1/admin/sync`, and `/api/v1/admin/stats`. |
| `Monitor (Uptime Tool)` | Matches | Monitoring is supported through `/health`, `/api/v1/health`, `/api/v1/health/ready`, and `/api/v1/metrics`. |
| `D1 Vector DB (Chroma)` | Matches | ChromaDB stores embedded chunks, document text, ids, and metadata in the configured collection. |
| `D2 Cache (Redis)` | Matches, but name is simplified | Redis is more than a cache. It stores session history, webhook event markers, payload hashes, and rate-limit counters. |
| `Ollama (Embed)` | Matches | Ingestion and retrieval call Ollama `/api/embeddings` using the configured embedding model. |
| `Get Answer (Llama 3)` | Partially matches | The code uses the configured `OLLAMA_MODEL`, whose default is `qwen2.5:1.5b`. The diagram label should be read as "LLM answer generation through Ollama", not as a fixed Llama 3 requirement. |
| `System (Metrics)` | Partially matches | Metrics are not a persistent data store. The implemented `/api/v1/metrics` endpoint currently returns a lightweight Prometheus text metric: `entrance_chatbot_up 1`. |
| `All components run inside Docker containers` | Mostly matches | Runtime services run in Docker Compose. GitHub Actions, GitHub Container Registry, the browser, Java API, and monitoring tool are external to the runtime stack. |

Overall, the diagram is valid for explaining the implemented chatbot system if the above simplifications are acknowledged.

## 3. Evidence Used

The verification is based on the following repository artifacts:

- `backend/main.py`: FastAPI app setup, routers, middleware, startup Redis client, and Ollama warmup.
- `backend/api/chat.py`: public chat and streaming chat endpoints.
- `backend/api/admin.py`: admin refresh, sync, and vector-store stats endpoints.
- `backend/api/webhooks.py`: webhook sync endpoint.
- `backend/api/health.py`: health and readiness endpoints.
- `backend/api/router.py`: metrics endpoint and API router composition.
- `backend/config.py`: physical configuration for Redis, ChromaDB, Ollama, backend API, CORS, rate limits, and model names.
- `backend/ingestion/*`: source fetching, normalization, chunking, embedding, and Chroma upsert logic.
- `backend/retrieval/*`: hybrid dense plus keyword retrieval over ChromaDB.
- `backend/generation/*`: prompt construction, Ollama generation, citation validation, and hallucination guardrails.
- `backend/memory/session.py`: Redis-backed conversation memory.
- `docker-compose.yml` and `docker-compose.prod.yml`: Docker services, ports, networks, and volumes.
- `.github/workflows/*`, `scripts/deploy-vps.sh`, and `scripts/backup-vps.sh`: CI/CD, deployment, and backup flow.

## 4. Physical System Boundary

The physical system boundary is the Entrance Chatbot backend stack. It includes:

- FastAPI backend container.
- ChromaDB container and Chroma persistent Docker volume.
- Redis container and Redis persistent Docker volume.
- Ollama container and Ollama model volume.
- Deployment configuration, logs, and backup scripts used to operate the stack.

The following are outside the chatbot system boundary:

- Browser or frontend application.
- Entrance Gateway Java backend API.
- Admin or operations caller.
- Monitoring or uptime service.
- GitHub Actions runner.
- GitHub Container Registry or Docker registry.

## 5. Physical Context Diagram Explanation

At context level, the whole chatbot stack is represented as one process: `(0) Entrance Chatbot System`.

```text
[E1 User Browser]
    -- chat request -->
        (0 Entrance Chatbot System)
    <-- chat response or stream events --

[E2 Java Backend API]
    -- source data or webhook event -->
        (0 Entrance Chatbot System)
    <-- source data request or sync acknowledgement --

[E3 Admin / Operations User]
    -- refresh, sync, or stats request -->
        (0 Entrance Chatbot System)
    <-- admin report or stats response --

[E4 Monitoring / Uptime Tool]
    -- health, readiness, or metrics request -->
        (0 Entrance Chatbot System)
    <-- status response or metric result --

[E5 GitHub Actions]
    -- build and deployment command -->
        (0 Entrance Chatbot System)
    <-- test, build, or deployment result --

[E6 Container Registry]
    -- backend Docker image -->
        (0 Entrance Chatbot System)
    <-- pushed backend Docker image --
```

This context view matches the diagram because every external actor communicates through HTTP, Docker, or deployment interfaces rather than directly reading internal stores.

## 6. Level 1 Physical DFD Explanation

The Level 1 diagram divides the chatbot system into three main runtime processes plus supporting model and deployment services.

### 6.1 Process 1.0 - Process Chat Request

This process receives a chat request from the frontend or browser. The implemented endpoints are:

- `POST /api/v1/chat`
- `POST /api/v1/chat/stream`

The backend validates the request, loads recent conversation history from Redis, retrieves relevant source chunks from ChromaDB, builds a grounded prompt, calls Ollama for answer generation, validates citations, stores the conversation turn, and returns either JSON or Server-Sent Events.

Physical data stores and services used:

- `D1 Vector DB (Chroma)` for retrieved document chunks and metadata.
- `D2 Cache / State Store (Redis)` for session history and rate-limit state.
- `Ollama` for embeddings and answer generation.

### 6.2 Process 2.0 - Sync and Ingest Knowledge

This process maintains the searchable knowledge base. It is triggered by admin requests or Java backend webhook events.

Implemented endpoints:

- `POST /api/v1/admin/refresh`
- `POST /api/v1/admin/sync`
- `POST /api/v1/webhooks/sync`

The ingestion pipeline fetches records from the Java backend API, normalizes the records into documents, splits documents into chunks, creates embeddings through Ollama, and stores the embedded chunks in ChromaDB. Redis is used to remember processed webhook event ids and payload hashes so repeated events or unchanged records can be skipped.

Supported source categories include:

- Courses.
- Colleges.
- Syllabus.
- Notes.
- Old questions.
- Trainings.
- Question sets.
- Questions.

### 6.3 Process 3.0 - Provide Status and Health

This process serves operational visibility.

Implemented endpoints:

- `GET /health`
- `GET /api/v1/health`
- `GET /health/ready`
- `GET /api/v1/health/ready`
- `GET /api/v1/metrics`
- `GET /api/v1/admin/stats`

Health returns a basic liveness response. Readiness checks Redis, ChromaDB, and Ollama. Metrics return a Prometheus-format text response. Admin stats read the Chroma collection count.

## 7. Level 2 Physical DFD Explanation

### 7.1 Level 2 for Process 1.0 - Chat Request Flow

The image shows the following chat sub-processes: check input, get history, search knowledge, create prompt, get answer, and save history. This matches the code structure.

```text
[User Browser]
    -- chat request -->
        (1.1 Check Input)
    -- validated request -->
        (1.2 Get History)
    -- question with history -->
        (1.3 Search Knowledge)
    -- retrieved chunks -->
        (1.4 Create Prompt)
    -- prompt -->
        (1.5 Get Answer through Ollama LLM)
    -- generated answer -->
        (1.6 Save History)
    -- chat response -->
        [User Browser]
```

Detailed implementation mapping:

| Diagram Process | Implemented Component | Description |
|---|---|---|
| `1.1 Check Input` | Pydantic `ChatRequest`, FastAPI validation, middleware | Validates `message`, `session_id`, optional filters, and `top_k`. |
| `1.2 Get History` | `SessionMemory.format_recent_history()` | Reads `rag:session:{session_id}` from Redis and formats recent messages for the prompt. |
| `1.3 Search Knowledge` | `Retriever.retrieve()` | Performs optional query rewriting, dense vector search, keyword search, RRF reranking, and relevance filtering. |
| `1.4 Create Prompt` | `build_prompt()` and `build_conversational_prompt()` | Creates a system prompt and user prompt using retrieved chunks and conversation history. |
| `1.5 Get Answer` | `OllamaGenerationClient.stream_generate()` | Calls Ollama `/api/generate` using the configured chat model. |
| `1.6 Save History` | `SessionMemory.add_turn()` | Stores the user message and final assistant response in Redis with TTL. |

Important note: the image labels this step as `Get Answer (Llama 3)`, but the implementation does not hard-code Llama 3. The default configured model is `qwen2.5:1.5b`, and it can be changed using `OLLAMA_MODEL`.

### 7.2 Level 2 for Process 2.0 - Knowledge Sync and Ingestion Flow

The image shows get source data, clean data, split text, create embedding, and store in vector DB. This accurately reflects the implemented ingestion pipeline.

```text
[Java Backend API]
    -- source records -->
        (2.1 Get Source Data)
    -- raw JSON records -->
        (2.2 Clean Data)
    -- normalized documents -->
        (2.3 Split Text)
    -- document chunks -->
        (2.4 Create Embedding)
    -- vectors and chunks -->
        (2.5 Store in Vector DB)
```

Detailed implementation mapping:

| Diagram Process | Implemented Component | Description |
|---|---|---|
| `2.1 Get Source Data` | `BackendAPIClient` | Calls Java backend endpoints using HTTP and optional bearer token. |
| `2.2 Clean Data` | `normalize_sources()` | Converts raw API records into readable knowledge documents with metadata. |
| `2.3 Split Text` | `chunk_documents()` | Splits normalized documents into bounded overlapping text chunks. |
| `2.4 Create Embedding` | `OllamaEmbedder` | Calls Ollama `/api/embeddings` using `OLLAMA_EMBED_MODEL`, default `nomic-embed-text`. |
| `2.5 Store in Vector DB` | `VectorStore.upsert_chunks()` | Writes chunk ids, document text, embeddings, and metadata to ChromaDB. |

Redis is also part of this process. The diagram correctly shows Redis as saving state, but the exact keys are:

- `rag:webhook:event:{event_id}` for duplicate webhook prevention.
- `rag:payload_hash:{source_id}` for unchanged payload detection.

### 7.3 Level 2 for Process 3.0 - Status and Health Flow

The image shows health check, service checks, and metrics. This matches the implemented monitoring behavior, with one correction: `System (Metrics)` is an endpoint output, not a persistent data store.

```text
[Monitoring Tool]
    -- status request -->
        (3.1 Health Check)
    -- readiness request -->
        (3.2 Check Services)
    -- metrics request -->
        (3.3 Get Metrics)
    <-- status response or metric result --
```

Detailed implementation mapping:

| Diagram Process | Implemented Component | Description |
|---|---|---|
| `3.1 Health Check` | `health()` route | Returns `{"status": "ok"}` for liveness. |
| `3.2 Check Services` | `ready()` route | Pings Redis, calls Chroma heartbeat, and calls Ollama tags endpoint. |
| `3.3 Get Metrics` | `/api/v1/metrics` route | Returns Prometheus text metric `entrance_chatbot_up 1`. |

## 8. Physical Data Stores

| ID | Data Store | Physical Technology | Stored Data |
|---|---|---|---|
| D1 | Vector DB | ChromaDB container with Docker volume `chroma-data` or `entrance-chatbot-chroma-data` | Knowledge chunks, embeddings, document ids, source ids, source types, titles, and metadata. |
| D2 | Cache / State Store | Redis 7 container with Docker volume `redis-data` or `entrance-chatbot-redis-data` | Chat session history, rate-limit counters, webhook event markers, and source payload hashes. |
| D3 | Model Store | Ollama container with Docker volume `ollama-data` or `entrance-chatbot-ollama-data` | Local LLM and embedding model files. |
| D4 | Deployment Files and Backups | Repository files, VPS files, Docker logs, and backup archives | Compose files, environment files, Docker image references, logs, and backup tarballs. |

## 9. Main Physical Data Flows

| From | To | Data Flow |
|---|---|---|
| Browser | FastAPI backend | Chat request JSON containing `message`, `session_id`, optional filters, and optional `top_k`. |
| FastAPI backend | Browser | Chat response JSON containing answer, confidence, sources, session id, allowed flag, reason, and intent. |
| FastAPI backend | Browser | Streaming response using `text/event-stream` for token and source events. |
| FastAPI backend | Redis | Session history read/write using `rag:session:{session_id}`. |
| FastAPI backend | ChromaDB | Vector query, keyword scan, collection count, upsert, and delete operations. |
| FastAPI backend | Ollama | Embedding requests through `/api/embeddings`. |
| FastAPI backend | Ollama | Generation requests through `/api/generate`. |
| Admin caller | FastAPI backend | Refresh, sync, and stats requests with `X-API-Key`. |
| Java backend API | FastAPI backend | Webhook sync event with source type, event type, event id, and source ids. |
| FastAPI backend | Java backend API | Source record GET requests for ingestion. |
| Monitoring tool | FastAPI backend | Health, readiness, and metrics requests. |
| GitHub Actions | Container registry | Built backend image push. |
| Deployment script | Container registry | Backend image pull for production deployment. |

## 10. Process Specifications

### PSPEC 1.0 - Process Chat Request

The backend receives a chat request, validates the request body, reads recent conversation context from Redis, classifies whether the message is conversational or knowledge-seeking, retrieves relevant knowledge chunks from ChromaDB for factual questions, builds a source-grounded prompt, calls the configured Ollama chat model, validates citation grounding, stores the final turn in Redis, and returns a response to the browser.

### PSPEC 2.0 - Sync and Ingest Knowledge

The backend accepts an admin refresh, admin targeted sync, or Java backend webhook. It validates the admin API key, determines the affected source type or source ids, claims webhook events in Redis to avoid duplicate processing, fetches source records from the Java backend API, skips unchanged payloads when hashes match, normalizes records, splits them into chunks, creates embeddings with Ollama, and upserts or deletes records in ChromaDB.

### PSPEC 3.0 - Provide Status and Health

The backend responds to liveness, readiness, metrics, and admin statistics requests. Liveness confirms the application process is running. Readiness confirms Redis, ChromaDB, and Ollama are reachable. Metrics expose a Prometheus-style text metric. Admin stats return the Chroma collection name and count.

### PSPEC 4.0 - Use Ollama Model Service

Ollama is a separate physical service in the Docker network. It provides embedding vectors for search and ingestion, provides generated answer tokens for chat responses, and exposes model tag status for readiness checks.

### PSPEC 5.0 - Build and Deploy Runtime Stack

GitHub Actions runs tests, builds the backend Docker image, pushes the image to the container registry, and deploys it to the VPS using Docker Compose. The production compose file starts the backend, ChromaDB, Redis, and Ollama containers on a private Docker network, with only the backend service published externally.

## 11. DFD Balancing Check

The Physical DFD is balanced across its levels:

| Parent Flow | Preserved in Child Diagram |
|---|---|
| User chat request and response | Preserved in Level 2 process 1.0 through input validation, history, retrieval, prompt, answer generation, and history save. |
| Java backend source data | Preserved in Level 2 process 2.0 through source fetch, normalization, chunking, embedding, and vector storage. |
| Admin request and response | Preserved through admin refresh, sync, stats, and ingestion report flows. |
| Monitoring status request and response | Preserved through health check, service checks, and metrics response. |
| ChromaDB read/write | Preserved in chat retrieval, ingestion storage, stats, and readiness checks. |
| Redis read/write | Preserved in session memory, webhook event state, payload hashes, and readiness checks. |
| Ollama requests and responses | Preserved in embedding, answer generation, startup warmup, and readiness checks. |

## 12. DFD Rule Verification

| DFD Rule | Result |
|---|---|
| External entities do not directly access internal data stores. | Passed. The browser, admin, monitor, and Java backend communicate through backend APIs. |
| Data stores do not directly exchange data with each other. | Passed. Redis, ChromaDB, and Ollama model files are accessed through processes. |
| Every process has at least one input and one output. | Passed. Each process receives requests/data and produces responses, store updates, or service calls. |
| Process names describe actions. | Passed. Names such as Process Chat Request, Sync and Ingest Knowledge, and Provide Status and Health are valid process names. |
| Data flows are named as data or protocol payloads. | Passed. Examples include chat request, session data, source data, embedding, metric result, and admin response. |
| Child diagrams preserve parent-level inputs and outputs. | Passed with minor simplification. The image preserves the major parent flows but omits some detailed physical flows such as rate-limit counters and deployment backups. |

## 13. Academic Report Notes

The Physical DFD represents the implementation level of the Entrance Chatbot system. Unlike the Logical DFD, which focuses on business activities, the Physical DFD shows real technologies, communication protocols, deployed components, and storage mechanisms. The system is implemented as a Retrieval-Augmented Generation chatbot using a FastAPI backend. ChromaDB is used as the vector database for semantic search, Redis is used for short-term state and session memory, and Ollama provides both embedding and text-generation model services.

The chat flow begins when the user submits a message from the browser. The backend validates the request, retrieves previous messages from Redis, searches ChromaDB for relevant knowledge, generates an answer with Ollama, validates the answer against retrieved sources, and saves the conversation history back to Redis. This ensures that the chatbot response is both contextual and grounded in stored Entrance Gateway knowledge.

The ingestion flow keeps the vector database synchronized with the authoritative Java backend. Admin users can manually trigger full or targeted synchronization, and the Java backend can send webhook events when source content changes. During ingestion, raw source records are fetched through HTTP, cleaned into normalized documents, split into chunks, embedded through Ollama, and stored in ChromaDB. Redis helps prevent duplicate webhook processing and unnecessary reprocessing of unchanged source records.

The monitoring flow allows operations tools to check whether the system is alive and ready. The readiness endpoint verifies the availability of Redis, ChromaDB, and Ollama, which are required for the chatbot to answer knowledge-based questions reliably. The metrics endpoint currently exposes a minimal Prometheus-compatible metric.

The deployment flow in the diagram is also supported by the repository. The backend can be built into a Docker image, pushed to a container registry, and deployed using Docker Compose. In production, Redis, ChromaDB, and Ollama are internal services on the Docker network, while the backend exposes the API used by the frontend, admin tools, and monitoring tools.

## 14. Final Conclusion

The Physical DFD in `image/physicaldfd.png` is consistent with the implemented Entrance Chatbot system at the architectural level. It correctly shows the main physical processes, external entities, data stores, and data flows. The diagram should be used with three clarifications: Redis is a state store rather than only a cache, the LLM model is configurable through Ollama and is not necessarily Llama 3, and metrics are returned by an endpoint rather than stored as a separate database. With these clarifications, the diagram is suitable for inclusion in an academic report.
