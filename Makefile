.DEFAULT_GOAL := help
.PHONY: help setup up down logs shell migrate migrations superuser test test-backend \
        test-frontend test-mobile lint format check schema build clean rename \
        fe-install fe-dev fe-build mobile-dev mobile-ios mobile-android

PYTHON ?= python
VENV   ?= .venv
BIN    := $(VENV)/bin
COMPOSE := docker compose

help: ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

# ---------------------------------------------------------------------------
# Local (no Docker)
# ---------------------------------------------------------------------------

setup: ## Create the virtualenv, install deps, copy .env
	$(PYTHON) -m venv $(VENV)
	$(BIN)/pip install --upgrade pip
	$(BIN)/pip install -r requirements/dev.txt
	@test -f .env || (cp .env.example .env && echo "Created .env from .env.example")
	@test -f website/.env || (cp website/.env.example website/.env && echo "Created website/.env")
	@test -f mobile/.env || (cp mobile/.env.example mobile/.env && echo "Created mobile/.env")
	@echo "Now run: make migrate && make run"

run: ## Run the Django dev server
	$(BIN)/python manage.py runserver

migrate: ## Apply migrations
	$(BIN)/python manage.py migrate

migrations: ## Create migrations for model changes
	$(BIN)/python manage.py makemigrations

superuser: ## Create a superuser interactively
	$(BIN)/python manage.py createsuperuser

shell: ## Django shell
	$(BIN)/python manage.py shell

worker: ## Run a Celery worker
	$(BIN)/celery -A template worker -l info

# ---------------------------------------------------------------------------
# Docker
# ---------------------------------------------------------------------------

up: ## Build and start every service
	$(COMPOSE) up --build

down: ## Stop services (add ARGS=-v to drop the database volume)
	$(COMPOSE) down $(ARGS)

logs: ## Tail service logs
	$(COMPOSE) logs -f

# ---------------------------------------------------------------------------
# Quality
# ---------------------------------------------------------------------------

test: test-backend test-frontend test-mobile ## Run every test suite

test-backend: ## Run pytest with coverage
	$(BIN)/python -m pytest --cov --cov-report=term-missing

test-frontend: ## Run the website test suite
	npm run test --workspace website

test-mobile: ## Run the mobile test suite
	npm run test --workspace mobile

lint: ## Lint backend, website and mobile
	$(BIN)/ruff check .
	$(BIN)/ruff format --check .
	@# `--workspaces` covers packages/shared too, which has a typecheck and no
	@# lint of its own -- `--if-present` is what lets that be true.
	npm run lint --workspaces --if-present
	npm run typecheck --workspaces --if-present

format: ## Auto-format and auto-fix
	$(BIN)/ruff check --fix .
	$(BIN)/ruff format .
	npm run lint:fix --workspaces --if-present

check: ## Django checks, including the production deploy checklist
	$(BIN)/python manage.py check
	@# The deploy checklist needs production settings to import, so supply
	@# throwaway values rather than requiring a real production .env.
	DJANGO_ENVIRONMENT=production \
	SECRET_KEY="$$($(BIN)/python -c 'from django.core.management.utils import get_random_secret_key as k; print(k())')" \
	ALLOWED_HOSTS=example.com \
	DATABASE_URL=postgres://checks:checks@db.example.com:5432/checks \
	FRONTEND_URL=https://example.com \
	STRIPE_ENABLED=true \
	$(BIN)/python manage.py check --deploy --fail-level WARNING
	DJANGO_SETTINGS_MODULE=template.settings.testing \
		$(BIN)/python manage.py makemigrations --check --dry-run
	@# CI fails the build on a schema warning, so run the same check here --
	@# a view added without a declared request or response passes every other
	@# target and only turns red on the pull request.
	DJANGO_SETTINGS_MODULE=template.settings.testing \
		$(BIN)/python manage.py spectacular --fail-on-warn --file /dev/null

schema: ## Write the OpenAPI schema to schema.yml
	$(BIN)/python manage.py spectacular --fail-on-warn --file schema.yml

# ---------------------------------------------------------------------------
# Frontend
# ---------------------------------------------------------------------------

fe-install: ## Install every workspace's dependencies
	@# One install at the root. The website, the mobile app and packages/shared
	@# are npm workspaces, so installing inside one of them would produce a
	@# second lockfile and a second copy of React.
	npm install

fe-dev: ## Run the Vite dev server
	npm run dev --workspace website

fe-build: ## Production build of the frontend
	npm run build --workspace website

# ---------------------------------------------------------------------------
# Mobile
# ---------------------------------------------------------------------------

mobile-dev: ## Start the Expo dev server
	npm run start --workspace mobile

mobile-ios: ## Open the app in the iOS simulator
	npm run ios --workspace mobile

mobile-android: ## Open the app in the Android emulator
	npm run android --workspace mobile

# ---------------------------------------------------------------------------
# Template
# ---------------------------------------------------------------------------

rename: ## Rename the project: make rename NAME=myapp
	@test -n "$(NAME)" || (echo "Usage: make rename NAME=myapp" && exit 1)
	$(PYTHON) scripts/rename_project.py $(NAME)

clean: ## Remove build artefacts and caches
	find . -type d -name __pycache__ -not -path "./$(VENV)/*" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .ruff_cache htmlcov .coverage coverage.xml staticfiles
	rm -rf website/dist website/coverage
