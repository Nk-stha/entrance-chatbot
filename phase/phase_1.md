# Phase 1 — Docker-First Infrastructure Foundation

## Status

Phase 1 is **partially implemented and ready for first Docker run**.

This phase creates the base infrastructure required before building ingestion, retrieval, generation, and webhook logic.

---

## 1. Goal of Phase 1

The goal of Phase 1 is to create a runnable production-shaped environment using Docker Compose.

It prepares these core services:

| Service | Purpose |
|---|---|
| FastAPI backend | Main chatbot API server |
| ChromaDB | Vector database for RAG chunks and embeddings |
| Redis | Conversation memory, webhook idempotency, sync hashes |
| Ollama | Local LLM and embedding model runtime |

This phase does **not** yet implement the full chatbot.

It only creates the infrastructure foundation.

---

## 2. Files Created in Phase 1

| File | Purpose |
|---|---|
| `.env.example` | Environment variable template |
| `docker-compose.yml` | Local Docker service stack |
| `docker-compose.prod.yml` | VPS-safe production resource limits |
| `Makefile` | Shortcut commands for Docker workflows |
| `.gitignore` | Prevent secrets/cache/data from being committed |
| `PHASE_1_INFRASTRUCTURE_SETUP.md` | Short operational setup guide |
| `backend/Dockerfile` | Builds FastAPI backend image |
| `backend/.dockerignore` | Prevents unnecessary files from entering Docker image |
| `backend/requirements.txt` | Python package dependencies |
| `backend/config.py` | Typed app settings from environment variables |
| `backend/main.py` | Minimal FastAPI app with health checks |

---

## 3. `.env.example`

Path:

```text
.env.example
```

### What it does

This file defines all environment variables required by the chatbot backend.

It is a template. The real runtime file should be named:

```text
.env
```

The Makefile can create `.env` from `.env.example` using:

```bash
make env
```

### Important values

```env
BACKEND_API_BASE_URL=http://api.entrancegateway.com/api/v1
OLLAMA_MODEL=qwen2.5:3b
OLLAMA_EMBED_MODEL=nomic-embed-text
CHROMA_COLLECTION=entrance_knowledge
REDIS_URL=redis://redis:6379/0
UVICORN_WORKERS=1
CHUNK_SIZE_CHARS=600
CHUNK_OVERLAP_CHARS=120
```

### Why this matters

This keeps configuration outside code.

It allows different values for:

- local development
- Docker development
- production VPS

without changing Python files.

---

## 4. `docker-compose.yml`

Path:

```text
docker-compose.yml
```

### What it creates

This file starts four services:

```text
backend
chromadb
redis
ollama
```

### Backend service

The backend service builds from:

```text
./backend/Dockerfile
```

It exposes:

```http
http://localhost:8000
```

It runs:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1
```

### ChromaDB service

ChromaDB runs on container port `8000` and host port `8001`:

```text
localhost:8001 -> chromadb:8000
```

The backend talks to ChromaDB internally through:

```text
http://chromadb:8000
```

### Redis service

Redis runs on:

```text
localhost:6379
```

Inside Docker, backend uses:

```text
redis://redis:6379/0
```

Redis has append-only persistence enabled:

```bash
redis-server --appendonly yes
```

It also has a memory cap policy:

```bash
--maxmemory 384mb --maxmemory-policy allkeys-lru
```

### Ollama service

Ollama runs on:

```text
localhost:11434
```

Inside Docker, backend uses:

```text
http://ollama:11434
```

Models are stored in a Docker volume:

```text
ollama-data
```

### Volumes

The file creates persistent volumes:

| Volume | Stores |
|---|---|
| `chroma-data` | ChromaDB vector database files |
| `redis-data` | Redis append-only data |
| `ollama-data` | Downloaded Ollama models |

### Why this matters

Without volumes, all vector data and downloaded models would be lost when containers are removed.

---

## 5. `docker-compose.prod.yml`

Path:

```text
docker-compose.prod.yml
```

### What it does

This file adds production resource limits for your VPS.

Target VPS:

```text
4 vCPU / 8 GB RAM / 75 GB NVMe
```

### Resource limits

| Service | CPU Limit | RAM Limit |
|---|---:|---:|
| Ollama | 3.0 cores | 3584 MB |
| FastAPI backend | 2.0 cores | 2 GB |
| ChromaDB | 1.5 cores | 1536 MB |
| Redis | 0.5 cores | 512 MB |

### Why this matters

This prevents one service, especially Ollama, from consuming all server memory and crashing the VPS.

The final architecture intentionally uses:

```text
qwen2.5:3b
```

instead of a larger model to stay inside the 8 GB RAM limit.

---

## 6. `backend/Dockerfile`

Path:

```text
backend/Dockerfile
```

### What it does

This file builds the FastAPI backend image.

Base image:

```dockerfile
python:3.12-slim
```

It installs:

- system dependency: `curl`
- Python dependencies from `requirements.txt`
- backend source files

It exposes port:

```text
8000
```

It defines a container health check:

```bash
curl -fsS http://localhost:8000/health || exit 1
```

### Why this matters

Docker can detect whether the backend is alive.

This is useful for production restarts and deployment checks.

---

## 7. `backend/requirements.txt`

Path:

```text
backend/requirements.txt
```

### Packages added

| Package | Purpose |
|---|---|
| `fastapi` | Web API framework |
| `uvicorn[standard]` | ASGI server |
| `pydantic` | Data validation |
| `pydantic-settings` | Environment settings management |
| `httpx` | Async HTTP client for readiness/API calls |
| `redis` | Async Redis client |
| `chromadb` | ChromaDB Python client for later phases |
| `structlog` | Structured logging for later phases |
| `python-dotenv` | `.env` loading support |
| `orjson` | Fast JSON serialization |

### Why this matters

These are the minimum dependencies needed for Phase 1 and the next backend phases.

---

## 8. `backend/config.py`

Path:

```text
backend/config.py
```

### What it does

This file defines typed application settings using Pydantic.

It reads values like:

```env
BACKEND_API_BASE_URL
OLLAMA_MODEL
REDIS_URL
CHROMA_HOST
WEBHOOK_SECRET
```

and exposes them as Python attributes.

Example:

```python
settings.ollama_model
settings.redis_url
settings.chroma_base_url
```

### Important class

```python
class Settings(BaseSettings):
```

This class maps environment variables to typed Python fields.

### Important helper

```python
@lru_cache
def get_settings() -> Settings:
    return Settings()
```

This caches settings so they are not repeatedly reloaded.

### Useful computed properties

```python
cors_origin_list
```

Converts comma-separated CORS string into a list.

```python
chroma_base_url
```

Builds ChromaDB URL from host and port.

### Why this matters

Centralized configuration keeps the app clean and prevents duplicated environment parsing.

---

## 9. `backend/main.py`

Path:

```text
backend/main.py
```

### What it does

This is the first FastAPI application entrypoint.

It currently provides:

- app initialization
- CORS middleware
- Redis client setup
- HTTP client setup
- liveness health endpoint
- readiness health endpoint
- versioned health endpoints

---

### 9.1 Lifespan handler

Code:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
```

This runs startup and shutdown logic.

On startup, it creates:

```python
app.state.http_client = httpx.AsyncClient(timeout=5.0)
app.state.redis = Redis.from_url(settings.redis_url, decode_responses=True)
```

On shutdown, it closes them:

```python
await app.state.http_client.aclose()
await app.state.redis.aclose()
```

### Why this matters

Creating clients once and reusing them is more efficient than creating a new client for every request.

---

### 9.2 FastAPI app

Code:

```python
app = FastAPI(
    title="Entrance Gateway RAG Chatbot API",
    description="Backend-only RAG chatbot API for Entrance Gateway.",
    version="0.1.0",
    lifespan=lifespan,
)
```

This creates the API application.

The app title and description appear in OpenAPI docs.

Once running, docs will be available at:

```http
http://localhost:8000/docs
```

---

### 9.3 CORS middleware

Code:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

This allows the existing frontend to call the chatbot backend.

The allowed frontend URLs come from:

```env
CORS_ORIGINS=http://localhost:3000
```

For production, this should later include your real frontend domain.

---

### 9.4 Liveness health endpoint

Endpoints:

```http
GET /health
GET /api/v1/health
```

Response:

```json
{"status":"ok"}
```

This only confirms the FastAPI app is running.

It does not check Redis, ChromaDB, or Ollama.

---

### 9.5 Readiness health endpoint

Endpoints:

```http
GET /health/ready
GET /api/v1/health/ready
```

This checks whether these services are reachable:

- Redis
- ChromaDB
- Ollama

Example response:

```json
{
  "status": "ready",
  "components": {
    "redis": {"status": "ok"},
    "chromadb": {"status": "ok"},
    "ollama": {"status": "ok"}
  }
}
```

If any service is not reachable, response status becomes:

```json
{"status":"not_ready"}
```

### Why this matters

Production deployments need to know if the app is truly ready to serve requests.

For example, the backend may be alive, but if Ollama is down, chat generation cannot work.

---

## 10. `Makefile`

Path:

```text
Makefile
```

### Commands available

| Command | What it does |
|---|---|
| `make env` | Creates `.env` from `.env.example` if missing |
| `make up` | Starts local Docker stack |
| `make up-prod` | Starts Docker stack with production limits |
| `make down` | Stops Docker stack |
| `make build` | Builds backend image |
| `make logs` | Follows container logs |
| `make ps` | Shows service status |
| `make health` | Calls backend health endpoints |
| `make pull-models` | Pulls `qwen2.5:3b` and `nomic-embed-text` |
| `make restart` | Restarts services |

### Why this matters

It avoids remembering long Docker commands.

---

## 11. `.gitignore`

Path:

```text
.gitignore
```

### What it prevents

It prevents committing:

- `.env` secrets
- Python cache files
- virtual environments
- logs
- local data folders

### Why this matters

Secrets like JWTs and webhook keys must never be committed to Git.

---

## 12. `backend/.dockerignore`

Path:

```text
backend/.dockerignore
```

### What it prevents

It prevents copying unnecessary files into the Docker image:

- virtual environments
- Python cache files
- test caches
- `.env` files
- Git metadata

### Why this matters

It keeps Docker images smaller and safer.

---

## 13. `PHASE_1_INFRASTRUCTURE_SETUP.md`

Path:

```text
PHASE_1_INFRASTRUCTURE_SETUP.md
```

### What it contains

This file gives operational instructions for:

- creating an 8 GB swap file
- starting Docker services
- pulling Ollama models
- checking health endpoints

### Why this matters

It is the deployment/runbook note for Phase 1.

---

## 14. How Services Connect

```text
Frontend
   ↓
FastAPI backend :8000
   ↓         ↓          ↓
Redis     ChromaDB    Ollama
:6379     :8000       :11434
```

Host machine ports:

| Host URL | Service |
|---|---|
| `http://localhost:8000` | FastAPI backend |
| `http://localhost:8001` | ChromaDB |
| `http://localhost:6379` | Redis |
| `http://localhost:11434` | Ollama |

Internal Docker URLs:

| Internal URL | Service |
|---|---|
| `http://backend:8000` | FastAPI backend |
| `http://chromadb:8000` | ChromaDB |
| `redis://redis:6379/0` | Redis |
| `http://ollama:11434` | Ollama |

---

## 15. How to Run Phase 1

### Step 1: Create `.env`

```bash
make env
```

### Step 2: Start services

```bash
make up
```

### Step 3: Pull Ollama models

```bash
make pull-models
```

### Step 4: Check health

```bash
make health
```

### Step 5: View logs

```bash
make logs
```

---

## 16. Validation Already Done

The following validation was run:

```bash
python3 -m py_compile backend/main.py backend/config.py
```

Result:

```text
Python syntax OK
```

Markdown validation also passed:

```text
Markdown code fences OK
```

---

## 17. What Phase 1 Does Not Yet Include

Phase 1 does not yet implement:

- ingestion from Spring Boot APIs
- webhook processing
- ChromaDB upsert/query logic
- embeddings
- RAG retrieval
- chat endpoint
- SSE streaming endpoint
- admin refresh endpoint
- rate limiting
- structured logging
- tests

These are planned for later phases.

---

## 18. Next Recommended Step

Run the infrastructure stack:

```bash
make up
```

Then pull models:

```bash
make pull-models
```

Then verify:

```bash
make health
```

After Phase 1 is verified, proceed to:

```text
Phase 2 — Async FastAPI Core Backend
```
