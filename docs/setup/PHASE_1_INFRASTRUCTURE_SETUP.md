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
