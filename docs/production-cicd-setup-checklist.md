# Production CI/CD Setup Checklist

This checklist is for enabling production CI/CD for the Entrance Gateway chatbot on the VPS.

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

This chatbot production compose uses only:

```text
127.0.0.1:8002 -> chatbot backend container 8000
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
- [ ] Nginx proxies to `127.0.0.1:8002`
- [ ] HTTPS works
- [ ] Ollama models are pulled
- [ ] `/admin/refresh` completed once
- [ ] `/admin/stats` shows expected stored chunks
- [ ] `/chat` smoke passes
- [ ] `/chat/stream` smoke passes
- [ ] Backup script runs successfully
