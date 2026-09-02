# Makefile - convenience wrappers around `docker compose` for this project.
# Run `make` or `make help` to list all targets.

COMPOSE := docker compose
APP     := dicom_app
DB      := db
ORTHANC := orthanc

.DEFAULT_GOAL := help
.PHONY: help env up detach down build rebuild \
        restart restart-app restart-db restart-orthanc \
        logs logs-app logs-db logs-orthanc \
        ps shell shell-db shell-orthanc test lint studies clean-volumes

help: ## Show this help
	@echo "Usage: make <target>"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

env: ## Create .env from .env.example if it doesn't exist yet
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo ".env created from .env.example - edit it (passwords especially) before running 'make up'"; \
	else \
		echo ".env already exists"; \
	fi

up: env ## Start the full stack in the foreground (Ctrl-C to stop)
	$(COMPOSE) up

detach: env ## Start the full stack in the background
	$(COMPOSE) up -d

down: ## Stop and remove containers (keeps volumes/data)
	$(COMPOSE) down

build: env ## Build (or rebuild) images
	$(COMPOSE) build

rebuild: env ## Rebuild images from scratch, ignoring the build cache
	$(COMPOSE) build --no-cache

restart: ## Restart all services
	$(COMPOSE) restart

restart-app: ## Restart only dicom_app
	$(COMPOSE) restart $(APP)

restart-db: ## Restart only the database
	$(COMPOSE) restart $(DB)

restart-orthanc: ## Restart only orthanc
	$(COMPOSE) restart $(ORTHANC)

logs: ## Follow logs for all services
	$(COMPOSE) logs -f

logs-app: ## Follow logs for dicom_app only
	$(COMPOSE) logs -f $(APP)

logs-db: ## Follow logs for the database only
	$(COMPOSE) logs -f $(DB)

logs-orthanc: ## Follow logs for orthanc only
	$(COMPOSE) logs -f $(ORTHANC)

ps: ## List this project's running containers
	$(COMPOSE) ps

shell: ## Open a shell inside the running dicom_app container
	$(COMPOSE) exec $(APP) bash

shell-db: ## Open a psql shell inside the running db container
	$(COMPOSE) exec $(DB) bash -c 'psql -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"'

shell-orthanc: ## Open a shell inside the running orthanc container
	$(COMPOSE) exec $(ORTHANC) bash

test: ## Run the test suite locally (via uv, not in Docker)
	uv run pytest tests/

lint: ## Run ruff locally (via uv, not in Docker)
	uv run ruff check src tests scripts

studies: ## List studies currently synced in Orthanc (ARGS="--patient smith" to filter, "--json", etc.)
	uv run python scripts/list_studies.py $(ARGS)

clean-volumes: ## DESTRUCTIVE: stop containers and delete all volumes (Postgres/Orthanc data)
	@echo "This deletes all Postgres and Orthanc data volumes. Ctrl-C now to cancel, continuing in 5s..."
	@sleep 5
	$(COMPOSE) down -v
