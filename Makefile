.PHONY: help up down dev build logs clean test lint migrate seed check monitoring backup

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

up: ## Start all services (production)
	docker compose up -d

down: ## Stop all services
	docker compose down

dev: ## Start all services (development with hot reload)
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up

build: ## Build all Docker images
	docker compose build

logs: ## Tail logs from all services
	docker compose logs -f

logs-server: ## Tail server logs
	docker compose logs -f server

logs-worker: ## Tail worker logs
	docker compose logs -f worker

clean: ## Remove all containers, volumes, and images
	docker compose down -v --rmi local

test: ## Run all tests
	docker compose exec server pytest -v
	docker compose exec worker pytest -v

test-server: ## Run server tests
	docker compose exec server pytest -v

test-worker: ## Run worker tests
	docker compose exec worker pytest -v

lint: ## Run linters
	docker compose exec server ruff check .
	docker compose exec server mypy .

migrate: ## Run database migrations
	docker compose exec server alembic upgrade head

migrate-create: ## Create a new migration (usage: make migrate-create MSG="description")
	docker compose exec server alembic revision --autogenerate -m "$(MSG)"

seed: ## Seed the database with demo data
	docker compose exec server python -m app.db.seed

shell-server: ## Open a shell in the server container
	docker compose exec server bash

shell-worker: ## Open a shell in the worker container
	docker compose exec worker bash

shell-db: ## Open psql in the database container
	docker compose exec postgres psql -U whiteops -d whiteops

status: ## Show status of all services
	docker compose ps

worker-add: ## Add a remote worker (usage: make worker-add IP=192.168.1.100)
	./scripts/add-worker.sh $(IP)

check: ## Run pre-deployment checks
	./scripts/pre-deploy-check.sh

monitoring: ## Start monitoring stack (Prometheus + Grafana)
	docker compose --profile monitoring up -d

backup: ## Backup database to ./backups/
	@mkdir -p backups
	docker compose exec postgres pg_dump -U whiteops whiteops > backups/whiteops_$$(date +%Y%m%d_%H%M%S).sql
	@echo "Backup saved to backups/"

restore: ## Restore database (usage: make restore FILE=backups/whiteops_xxx.sql)
	docker compose exec -T postgres psql -U whiteops whiteops < $(FILE)
