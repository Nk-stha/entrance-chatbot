# Production CI/CD Setup Checklist

This checklist is for enabling production CI/CD for the Entrance Gateway chatbot on the VPS.

---

## One-Time VPS Setup Runbook

Use this section only for the first production setup or when rebuilding a new VPS.
After these steps pass once, normal future deployments should only require `git push origin main` or manually rerunning the GitHub deploy workflow.

### Step 1 — Confirm repository exists on VPS

```bash
ls -la /opt/entrance-chatbot
```

Expected result:

```text
.git
.env.production
backend/
docker-compose.prod.yml
scripts/
```

If the directory does not exist yet:

```bash
git clone https://github.com/Nk-stha/entrance-chatbot.git /opt/entrance-chatbot
```

---

### Step 2 — Create production environment file

```bash
cd /opt/entrance-chatbot
cp .env.production.example .env.production
chmod 600 .env.production
nano .env.production
```

Required values to set:

```env
BACKEND_IMAGE=ghcr.io/nk-stha/entrance-chatbot/backend:latest
CHATBOT_BACKEND_JWT=FULL_JAVA_BACKEND_JWT
API_KEY=LONG_RANDOM_ADMIN_API_KEY
WEBHOOK_SECRET=LONG_RANDOM_WEBHOOK_SECRET
CORS_ORIGINS=https://entrancegateway.com,https://www.entrancegateway.com,http://localhost:3000,http://localhost:8080
```

Generate strong secrets:

```bash
openssl rand -hex 32
```

Manual test:

```bash
grep -n 'BACKEND_IMAGE\|CHATBOT_BACKEND_JWT\|API_KEY\|WEBHOOK_SECRET\|CHUNK_SIZE_CHARS\|CHUNK_OVERLAP_CHARS' .env.production
```

Expected result:

```text
Each variable appears on its own line.
CHUNK_SIZE_CHARS=600
CHUNK_OVERLAP_CHARS=120
```

Also verify no placeholders remain:

```bash
grep 'REPLACE_\|PASTE_\|FULL_JWT_HERE\|YOUR_NEW_RANDOM' .env.production || true
```

Expected result:

```text
No output
```

---

### Step 3 — Login to GHCR if backend image is private

Create a GitHub token with:

```text
read:packages
repo, only if the package/repository is private
```

Then login on the VPS:

```bash
echo 'YOUR_GITHUB_PAT' | docker login ghcr.io -u 'Nk-stha' --password-stdin
```

Expected result:

```text
Login Succeeded
```

Manual test:

```bash
docker pull ghcr.io/nk-stha/entrance-chatbot/backend:latest
```

Expected result:

```text
Status: Downloaded newer image for ghcr.io/nk-stha/entrance-chatbot/backend:latest
```

or:

```text
Image is up to date for ghcr.io/nk-stha/entrance-chatbot/backend:latest
```

---

### Step 4 — Open VPS firewall port 8002

This project currently exposes the chatbot backend directly through VPS IP and port `8002`.

```bash
sudo ufw allow 8002/tcp
sudo ufw status
```

Expected result:

```text
8002/tcp ALLOW
```

If your VPS provider has a separate cloud firewall, also allow inbound TCP `8002` there.

Manual test before deploy:

```bash
sudo ss -tulpn | grep ':8002' || true
```

Expected result before chatbot starts:

```text
No non-chatbot process is using 8002
```

---

### Step 5 — Validate production Compose config

```bash
cd /opt/entrance-chatbot
docker compose --env-file .env.production -f docker-compose.prod.yml config >/tmp/entrance-chatbot-compose-check.yml
```

Expected result:

```text
Command exits successfully with no error
```

Manual port safety check:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml config | grep -E 'published|target|8002|6379|11434'
```

Expected result:

```text
Backend publishes 8002 to target 8000.
Redis, ChromaDB, and Ollama do not publish public host ports.
```

---

### Step 6 — Run first manual deploy

```bash
cd /opt/entrance-chatbot
chmod +x scripts/deploy-vps.sh scripts/backup-vps.sh
APP_DIR=/opt/entrance-chatbot scripts/deploy-vps.sh
```

Expected result:

```text
[deploy] Deployment completed successfully
```

Manual container check:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml ps
```

Expected result:

```text
entrance-chatbot-backend    Up ... healthy
entrance-chatbot-redis      Up ... healthy
entrance-chatbot-chromadb   Up
entrance-chatbot-ollama     Up
```

Manual port check:

```bash
docker ps --format 'table {{.Names}}\t{{.Ports}}' | grep entrance-chatbot
```

Expected result:

```text
entrance-chatbot-backend   0.0.0.0:8002->8000/tcp
entrance-chatbot-chromadb  8000/tcp
entrance-chatbot-redis     6379/tcp
entrance-chatbot-ollama    11434/tcp
```

---

### Step 7 — Verify local health and readiness

```bash
curl -fsS http://127.0.0.1:8002/health && echo
```

Expected result:

```json
{"status":"ok"}
```

```bash
curl -fsS http://127.0.0.1:8002/api/v1/health/ready && echo
```

Expected result:

```json
{"status":"ready","components":{"redis":{"status":"ok"},"chromadb":{"status":"ok"},"ollama":{"status":"ok"}}}
```

```bash
curl -fsS http://127.0.0.1:8002/api/v1/metrics && echo
```

Expected result:

```text
entrance_chatbot_up 1
```

---

### Step 8 — Verify public IP access

From your laptop or browser:

```text
http://YOUR_VPS_IP:8002/health
```

Expected result:

```json
{"status":"ok"}
```

From terminal:

```bash
curl -fsS http://YOUR_VPS_IP:8002/health && echo
```

Expected result:

```json
{"status":"ok"}
```

If this fails but local `127.0.0.1:8002` works, check:

```text
UFW firewall
VPS provider firewall/security group
Docker port mapping
```

---

### Step 9 — Pull Ollama models once

```bash
cd /opt/entrance-chatbot
docker compose --env-file .env.production -f docker-compose.prod.yml exec ollama ollama pull qwen2.5:3b
docker compose --env-file .env.production -f docker-compose.prod.yml exec ollama ollama pull nomic-embed-text
```

Manual test:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml exec ollama ollama list
```

Expected result:

```text
qwen2.5:3b
nomic-embed-text
```

---

### Step 10 — Run initial ingestion once

```bash
source /opt/entrance-chatbot/.env.production
curl -X POST http://127.0.0.1:8002/api/v1/admin/refresh \
  -H "X-API-Key: ${API_KEY}"
```

Expected successful or partially successful result:

```json
{
  "report": {
    "fetched_count": 1,
    "chunk_count": 1,
    "embedded_count": 1,
    "upserted_count": 1
  }
}
```

> [!NOTE]
> A partial success can still index data. For example, if one source type returns a Java API `400`, verify `/admin/stats` before treating the whole setup as failed.

Manual stats test:

```bash
curl -H "X-API-Key: ${API_KEY}" \
  http://127.0.0.1:8002/api/v1/admin/stats
```

Expected result:

```json
{"collection":"entrance_knowledge","count":5}
```

The exact `count` can be higher or lower depending on available Java backend data.
It should be greater than `0` after successful ingestion.

---

### Step 11 — Test normal chat

```bash
curl -X POST http://127.0.0.1:8002/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Which training teaches Redis caching?",
    "session_id": "prod-smoke-1",
    "filters": null,
    "top_k": 5
  }'
```

Expected result:

```text
HTTP 200 response with an answer and sources/citations when relevant context exists.
```

If there is no relevant context, expected answer is the configured refusal message.

---

### Step 12 — Test streaming chat

```bash
curl -N -X POST http://127.0.0.1:8002/api/v1/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is BCA?",
    "session_id": "prod-stream-smoke-1",
    "filters": null,
    "top_k": 5
  }' --max-time 120
```

Expected result includes SSE events:

```text
event: heartbeat
event: sources
event: token
event: done
```

---

### Step 13 — Configure backup cron once

Manual backup test:

```bash
cd /opt/entrance-chatbot
APP_DIR=/opt/entrance-chatbot scripts/backup-vps.sh
```

Expected result:

```text
[backup] Backup completed at /opt/entrance-chatbot/backups/<timestamp>
```

Add cron:

```bash
crontab -e
```

```cron
0 2 * * * APP_DIR=/opt/entrance-chatbot /opt/entrance-chatbot/scripts/backup-vps.sh >> /var/log/entrance-chatbot-backup.log 2>&1
```

---

### Step 14 — Future deployment flow

After one-time setup, future code deployments should be:

```bash
git add .
git commit -m "your change"
git push origin main
```

Expected result:

```text
GitHub Actions CI passes.
Backend image is published to GHCR.
Deploy workflow updates the VPS automatically.
```

Manual rerun option:

```text
GitHub Actions → Deploy Chatbot to VPS → Run workflow
```

---

## 1. Files Added for CI/CD

| File | Purpose |
| :--- | :--- |
| `.github/workflows/ci.yml` | Compile Python, run tests, validate Docker build |
| `.github/workflows/build-image.yml` | Build and push backend image to GHCR |
| `.github/workflows/deploy-vps.yml` | SSH to VPS and run production deploy script |
| `docker-compose.prod.yml` | Standalone production Docker Compose stack |
| `.env.production.example` | Safe production environment template |
| `scripts/deploy-vps.sh` | VPS deployment script with health/readiness/port checks |
| `scripts/backup-vps.sh` | VPS volume and environment backup script |
| `deploy/nginx/entrance-chatbot.conf` | Nginx reverse proxy template for streaming-safe routing |

---

## 2. Required GitHub Secrets

Set these in GitHub repository settings:

```text
Settings → Secrets and variables → Actions → New repository secret
```

| Secret | Required | Example |
| :--- | :---: | :--- |
| `VPS_HOST` | Yes | `your-vps-ip-or-domain` |
| `VPS_USER` | Yes | `root` or `deploy` |
| `VPS_PASSWORD` | Yes | VPS SSH password for that user |

> [!WARNING]
> Password deployment is supported because this VPS currently uses password login. For stronger production security, migrate to SSH key authentication later and replace `VPS_PASSWORD` with `VPS_SSH_KEY` in the workflow.
The real `.env.production` must exist only on the VPS.

---

## 3. Required VPS Directory

Expected app directory:

```bash
/opt/entrance-chatbot
```

Create it once:

```bash
sudo mkdir -p /opt/entrance-chatbot
sudo chown -R $USER:$USER /opt/entrance-chatbot
```

If using a `deploy` user:

```bash
sudo chown -R deploy:deploy /opt/entrance-chatbot
```

---

## 4. First VPS Clone

The deploy workflow can clone the repository automatically if `/opt/entrance-chatbot/.git` does not exist.

Manual clone option:

```bash
git clone https://github.com/YOUR_ORG/YOUR_REPO.git /opt/entrance-chatbot
```

---

## 5. Production Environment on VPS

Copy template:

```bash
cd /opt/entrance-chatbot
cp .env.production.example .env.production
chmod 600 .env.production
```

Edit values:

```bash
nano .env.production
```

Required replacements:

```text
BACKEND_IMAGE=ghcr.io/YOUR_ORG/YOUR_REPO/backend:latest
CHATBOT_BACKEND_JWT=real Java backend JWT if required
API_KEY=long random admin API key
CORS_ORIGINS=https://entrancegateway.com,https://www.entrancegateway.com
```

Generate API key:

```bash
openssl rand -hex 32
```

> [!IMPORTANT]
> The deploy script refuses to run if `.env.production` still contains `REPLACE_` placeholders.

---

## 6. GHCR Image Name

This workflow publishes images to:

```text
ghcr.io/<github-owner>/<github-repo>/backend
```

So for this repo, set VPS `.env.production` like:

```env
BACKEND_IMAGE=ghcr.io/<github-owner>/<github-repo>/backend:latest
```

If the repository/package is private, the VPS must log in to GHCR:

```bash
echo '<GITHUB_PAT_WITH_PACKAGE_READ>' | docker login ghcr.io -u '<github-username>' --password-stdin
```

If the package is public, login is not required.

---

## 7. VPS Port Safety

Your current VPS already uses these host ports:

```text
3000, 3100, 5000, 6030, 8080, 9000, 9001, 9090, 9443
```

This chatbot production compose temporarily exposes the backend on VPS port `8002` for direct IP access:

```text
0.0.0.0:8002 -> chatbot backend container 8000
```

You can access:

```text
http://YOUR_VPS_IP:8002/health
http://YOUR_VPS_IP:8002/api/v1/chat
```

Before deploy:

```bash
sudo ss -tulpn | grep -E ':8002|:8001|:6379|:11434|:11435' || true
```

No non-chatbot process should be using `8002`.

---

## 8. Manual First Deploy

Before relying on GitHub Actions, run once manually on VPS:

```bash
cd /opt/entrance-chatbot
chmod +x scripts/deploy-vps.sh scripts/backup-vps.sh
APP_DIR=/opt/entrance-chatbot scripts/deploy-vps.sh
```

Expected result:

```text
[deploy] Deployment completed successfully
```

---

## 9. Pull Ollama Models

After containers start:

```bash
cd /opt/entrance-chatbot
docker compose --env-file .env.production -f docker-compose.prod.yml exec ollama ollama pull qwen2.5:3b
docker compose --env-file .env.production -f docker-compose.prod.yml exec ollama ollama pull nomic-embed-text
```

Verify:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml exec ollama ollama list
```

---

## 10. Initial Ingestion

Run once after models are ready:

```bash
source /opt/entrance-chatbot/.env.production
curl -X POST http://127.0.0.1:8002/api/v1/admin/refresh \
  -H "X-API-Key: ${API_KEY}"
```

Check stats:

```bash
curl -H "X-API-Key: ${API_KEY}" \
  http://127.0.0.1:8002/api/v1/admin/stats
```

---

## 11. Nginx Setup

Copy template:

```bash
sudo cp /opt/entrance-chatbot/deploy/nginx/entrance-chatbot.conf \
  /etc/nginx/sites-available/entrance-chatbot
```

Edit domain:

```bash
sudo nano /etc/nginx/sites-available/entrance-chatbot
```

Enable:

```bash
sudo ln -s /etc/nginx/sites-available/entrance-chatbot \
  /etc/nginx/sites-enabled/entrance-chatbot
sudo nginx -t
sudo systemctl reload nginx
```

Issue TLS certificate:

```bash
sudo certbot --nginx -d chatbot.entrancegateway.com
```

---

## 12. Backup Cron

Manual backup:

```bash
APP_DIR=/opt/entrance-chatbot scripts/backup-vps.sh
```

Cron example:

```bash
crontab -e
```

Add:

```cron
0 2 * * * APP_DIR=/opt/entrance-chatbot /opt/entrance-chatbot/scripts/backup-vps.sh >> /var/log/entrance-chatbot-backup.log 2>&1
```

---

## 13. GitHub Actions Flow

After setup:

```text
Pull request → CI only
Push to main → CI + build image + deploy to VPS
Manual deploy → run Deploy Chatbot to VPS workflow
```

---

## 14. Required Post-Deploy Checks

```bash
curl -fsS http://127.0.0.1:8002/health
curl -fsS http://127.0.0.1:8002/api/v1/health/ready
curl -fsS http://127.0.0.1:8002/api/v1/metrics
```

Streaming smoke:

```bash
curl -N -X POST http://127.0.0.1:8002/api/v1/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Which training teaches Redis caching?",
    "session_id": "prod-smoke-stream-1",
    "filters": null,
    "top_k": 5
  }' --max-time 120
```

---

## 15. Production Readiness Decision

Do not enable automatic deploy until these are true:

- [ ] CI passes on GitHub
- [ ] Image is visible in GHCR
- [ ] VPS can pull GHCR image
- [ ] `.env.production` has no placeholder values
- [ ] `scripts/deploy-vps.sh` passes manually
- [ ] Backend is reachable at `http://YOUR_VPS_IP:8002/health` while direct VPS/IP access is needed
- [ ] HTTPS works
- [ ] Ollama models are pulled
- [ ] `/admin/refresh` completed once
- [ ] `/admin/stats` shows expected stored chunks
- [ ] `/chat` smoke passes
- [ ] `/chat/stream` smoke passes
- [ ] Backup script runs successfully
