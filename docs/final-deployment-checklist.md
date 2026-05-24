# Final Deployment Checklist

Use this checklist before staging or production deployment.

## 1. Environment

- [ ] `.env` exists on the server.
- [ ] `API_KEY` is long, random, and not exposed to public frontend code.
- [ ] `CHATBOT_BACKEND_JWT` is configured for Java backend ingestion.
- [ ] `BACKEND_API_BASE_URL` uses HTTPS production API.
- [ ] `CORS_ORIGINS` includes only trusted frontend domains.
- [ ] `OLLAMA_MODEL` is available in Ollama.
- [ ] `OLLAMA_EMBED_MODEL` is available in Ollama.

## 2. Docker Stack

Run:

```bash
docker compose up -d --build
```

Verify:

```bash
docker compose ps
```

Expected:

- backend: up/healthy
- redis: up/healthy
- chromadb: up
- ollama: up

## 3. Health Checks

Run:

```bash
make health
```

Expected:

```text
/status ok
/readiness redis/chromadb/ollama ok
```

## 4. Test Suite

Run:

```bash
docker compose exec -T backend python -m pytest -q
```

Expected current baseline:

```text
76 passed, 3 skipped
```

The skipped tests are docs-mount checks that skip inside the backend Docker container because only `./backend` is mounted at `/app`.

## 5. Ingestion Verification

Run admin stats:

```bash
curl -H "X-API-Key: $(grep '^API_KEY=' .env | cut -d= -f2-)" \
  http://localhost:8002/api/v1/admin/stats
```

Expected:

```json
{"collection":"entrance_knowledge","count":3}
```

For production, run `/admin/refresh` only when ready to call the Java backend and embed/store data.

## 6. Chat API Smoke

```bash
curl -X POST http://localhost:8002/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is BCA?",
    "session_id": "deployment-smoke",
    "filters": {"source_type": "course"},
    "top_k": 3
  }'
```

Expected:

- JSON response
- `answer`
- `sources`
- `confidence`

## 7. Streaming API Smoke

```bash
curl -N -X POST http://localhost:8002/api/v1/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is BCA?",
    "session_id": "deployment-stream-smoke",
    "filters": {"source_type": "course"},
    "top_k": 3
  }'
```

Expected SSE events:

- `token`
- `sources`
- `done`

## 8. Frontend Integration

- [ ] Existing frontend uses `POST /api/v1/chat` or `/api/v1/chat/stream`.
- [ ] Frontend sends a stable `session_id`.
- [ ] Frontend renders citations from `sources`.
- [ ] Frontend does not send or expose `API_KEY`.
- [ ] Frontend domain is included in `CORS_ORIGINS`.

## 9. Security

- [ ] Admin endpoints reject requests without `X-API-Key`.
- [ ] Webhook endpoint is called only by trusted Java backend/server-side code.
- [ ] Redis-backed rate limiting is enabled through `RATE_LIMIT_REQUESTS` and `RATE_LIMIT_WINDOW`.
- [ ] Rate-limit failures return HTTP `429` with `rate_limit_exceeded`.
- [ ] Logs do not print API keys, JWTs, or user secrets.
- [ ] Public frontend cannot access `.env` values.

## 10. Monitoring

Check:

```bash
curl http://localhost:8002/api/v1/metrics
```

Expected:

```text
entrance_chatbot_up 1
```

## 11. Rollback

Before deployment:

- [ ] Save current `.env`.
- [ ] Save current Git commit hash.
- [ ] Keep previous Docker image/tag if deploying with registry.
- [ ] Know how to restore Chroma and Redis volumes if needed.
