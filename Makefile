.PHONY: help env up up-prod down build logs ps health pull-models restart

COMPOSE=docker compose
PROD_COMPOSE=docker compose -f docker-compose.yml -f docker-compose.prod.yml

help:
	@echo "Available commands:"
	@echo "  make env          Copy .env.example to .env if missing"
	@echo "  make up           Start development stack"
	@echo "  make up-prod      Start stack with production resource limits"
	@echo "  make down         Stop stack"
	@echo "  make build        Build backend image"
	@echo "  make logs         Follow logs"
	@echo "  make ps           Show service status"
	@echo "  make health       Check backend health endpoints"
	@echo "  make pull-models  Pull Ollama models"
	@echo "  make restart      Restart all services"

env:
	@test -f .env || cp .env.example .env
	@echo ".env is ready"

up: env
	$(COMPOSE) up -d --build

up-prod: env
	$(PROD_COMPOSE) up -d --build

build:
	$(COMPOSE) build

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f

ps:
	$(COMPOSE) ps

health:
	@curl -fsS http://localhost:8000/health && echo
	@curl -fsS http://localhost:8000/health/ready && echo

pull-models:
	$(COMPOSE) exec ollama ollama pull qwen2.5:3b
	$(COMPOSE) exec ollama ollama pull nomic-embed-text

restart:
	$(COMPOSE) restart
