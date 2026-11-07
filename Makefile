PYTHON ?= python3.12
VENV ?= .venv
BIN := $(VENV)/bin
COMPOSE := docker compose -p qadam

.PHONY: help venv install lint format test cov run-web run-bot up down logs clean

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-10s %s\n", $$1, $$2}'

$(BIN)/python:
	$(PYTHON) -m venv $(VENV)

venv: $(BIN)/python ## Create the virtualenv

install: venv ## Install runtime + dev dependencies and git hooks
	$(BIN)/pip install -r requirements-dev.txt
	$(BIN)/pre-commit install

lint: ## Ruff lint + format check
	$(BIN)/ruff check .
	$(BIN)/ruff format --check .

format: ## Auto-fix lint issues and format
	$(BIN)/ruff check --fix .
	$(BIN)/ruff format .

test: ## Run the test suite
	$(BIN)/pytest

cov: ## Run tests with a coverage report
	$(BIN)/pytest --cov --cov-report=term-missing

run-web: ## Run the Flask dev server on :5000 (override with PORT)
	$(BIN)/python -m backend.app

run-bot: ## Run the Telegram bot (needs BOT_TOKEN)
	$(BIN)/python -m bot.bot

up: ## Build and start db + web + bot with Docker Compose
	$(COMPOSE) up --build -d

down: ## Stop the stack and remove volumes
	$(COMPOSE) down -v

logs: ## Follow container logs
	$(COMPOSE) logs -f

clean: ## Remove caches
	rm -rf .pytest_cache .ruff_cache .coverage htmlcov
	find . -name __pycache__ -prune -exec rm -rf {} +
