# DrAssist — developer convenience targets.
# Windows users: prefer the equivalent scripts in scripts/*.ps1, or run these
# via Git Bash / WSL where `make` is available.

.PHONY: help setup dev up down restart logs ps build \
        migrate migrate-new migrate-down \
        lint format test test-backend test-frontend \
        shell-backend shell-db clean

help:
	@echo "DrAssist developer commands:"
	@echo "  make setup          First-time environment bootstrap"
	@echo "  make dev            Start full stack in dev mode (hot reload)"
	@echo "  make up             Start full stack (detached)"
	@echo "  make down           Stop all services"
	@echo "  make restart        Restart all services"
	@echo "  make logs           Tail logs for all services"
	@echo "  make build          Rebuild all images"
	@echo "  make migrate        Apply Alembic migrations"
	@echo "  make migrate-new    Create a new Alembic revision (m=message)"
	@echo "  make lint           Run linters (backend + frontend)"
	@echo "  make format         Auto-format code (backend + frontend)"
	@echo "  make test           Run all test suites"
	@echo "  make shell-backend  Open a shell in the backend container"
	@echo "  make shell-db       Open a psql shell in the postgres container"
	@echo "  make clean          Remove containers, volumes, and caches"

setup:
	bash scripts/setup.sh

dev:
	docker compose up --build

up:
	docker compose up -d --build

down:
	docker compose down

restart:
	docker compose restart

logs:
	docker compose logs -f --tail=200

build:
	docker compose build

migrate:
	docker compose exec backend alembic upgrade head

migrate-new:
	docker compose exec backend alembic revision --autogenerate -m "$(m)"

migrate-down:
	docker compose exec backend alembic downgrade -1

lint:
	bash scripts/lint.sh

format:
	docker compose exec backend ruff format .
	docker compose exec frontend npm run format

test:
	bash scripts/test.sh

test-backend:
	docker compose exec backend pytest

test-frontend:
	docker compose exec frontend npm run test

shell-backend:
	docker compose exec backend /bin/bash

shell-db:
	docker compose exec postgres psql -U $${POSTGRES_USER} -d $${POSTGRES_DB}

clean:
	docker compose down -v --remove-orphans
