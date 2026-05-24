# Phase 1 — Infrastructure Setup

## Create 8 GB Swap File

Run these commands on the production VPS before starting the production Docker stack:

```bash
sudo fallocate -l 8G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

Verify:

```bash
free -h
swapon --show
```

## Start Services

Development:

```bash
make up
```

Production-style with resource limits:

```bash
make up-prod
```

## Pull Ollama Models

After Ollama starts:

```bash
make pull-models
```

This pulls:

- `qwen2.5:3b`
- `nomic-embed-text`

## Health Checks

```bash
make health
```

Expected liveness:

```json
{"status":"ok"}
```

Readiness may show `not_ready` until Redis, ChromaDB, and Ollama are all reachable.

## Ollama Port Note

The Ollama container listens internally on:

```text
http://ollama:11434
```

On the host machine it is exposed as:

```text
http://localhost:11435
```

This avoids conflict with a locally installed Ollama service that may already use host port `11434`.

If you see this error:

```text
failed to bind host port 0.0.0.0:11434/tcp: address already in use
```

use the current `docker-compose.yml`, where Ollama maps:

```yaml
ports:
  - "11435:11434"
```
