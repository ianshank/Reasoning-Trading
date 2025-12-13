# Makefile for Reasoning Trading
# Provides common development commands for the project

.PHONY: help install install-dev install-all clean test test-unit test-integration test-e2e test-cov \
        lint format type-check security-check pre-commit docker-build docker-run docker-test \
        run-api run-cli docs release version

# Default Python version
PYTHON := python3.11
VENV := .venv
PIP := $(VENV)/bin/pip
PYTEST := $(VENV)/bin/pytest
RUFF := $(VENV)/bin/ruff
MYPY := $(VENV)/bin/mypy

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

# =============================================================================
# Help
# =============================================================================
help: ## Show this help message
	@echo "$(BLUE)Reasoning Trading - Development Commands$(NC)"
	@echo ""
	@echo "$(GREEN)Usage:$(NC)"
	@echo "  make <target>"
	@echo ""
	@echo "$(GREEN)Targets:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'

# =============================================================================
# Installation
# =============================================================================
$(VENV)/bin/activate:
	$(PYTHON) -m venv $(VENV)

install: $(VENV)/bin/activate ## Install production dependencies
	$(PIP) install --upgrade pip
	$(PIP) install -e .
	@echo "$(GREEN)Production dependencies installed$(NC)"

install-dev: $(VENV)/bin/activate ## Install development dependencies
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev]"
	@echo "$(GREEN)Development dependencies installed$(NC)"

install-all: $(VENV)/bin/activate ## Install all dependencies (dev + analysis + webui)
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev,analysis,webui]"
	@echo "$(GREEN)All dependencies installed$(NC)"

setup: install-dev pre-commit-install ## Complete development setup
	@echo "$(GREEN)Development environment is ready!$(NC)"

# =============================================================================
# Cleaning
# =============================================================================
clean: ## Remove build artifacts and caches
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .eggs/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf coverage.xml
	rm -rf coverage-*.xml
	rm -rf junit-*.xml
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@echo "$(GREEN)Cleaned build artifacts$(NC)"

clean-all: clean ## Remove all artifacts including virtual environment
	rm -rf $(VENV)
	@echo "$(GREEN)Removed virtual environment$(NC)"

# =============================================================================
# Testing
# =============================================================================
test: ## Run all tests
	$(PYTEST) tests/ -v --tb=short

test-unit: ## Run unit tests only
	$(PYTEST) tests/ \
		--ignore=tests/integration \
		--ignore=tests/e2e \
		--ignore=tests/user_journeys \
		-v --tb=short

test-integration: ## Run integration tests only
	$(PYTEST) tests/integration/ -v --tb=short

test-e2e: ## Run E2E and user journey tests
	$(PYTEST) tests/e2e/ tests/user_journeys/ -v --tb=short --timeout=600

test-cov: ## Run tests with coverage report
	$(PYTEST) tests/ \
		--cov=reasoning_trading \
		--cov-report=term-missing \
		--cov-report=html \
		--cov-report=xml \
		-v --tb=short
	@echo "$(GREEN)Coverage report generated in htmlcov/$(NC)"

test-fast: ## Run tests in parallel (requires pytest-xdist)
	$(PYTEST) tests/ -n auto -v --tb=short

test-watch: ## Run tests in watch mode (requires pytest-watch)
	$(VENV)/bin/ptw tests/ -- -v --tb=short

# =============================================================================
# Code Quality
# =============================================================================
lint: ## Run linter (Ruff)
	$(RUFF) check src/ tests/
	@echo "$(GREEN)Linting passed$(NC)"

lint-fix: ## Run linter and auto-fix issues
	$(RUFF) check src/ tests/ --fix
	@echo "$(GREEN)Linting issues fixed$(NC)"

format: ## Format code with Ruff
	$(RUFF) format src/ tests/
	@echo "$(GREEN)Code formatted$(NC)"

format-check: ## Check code formatting
	$(RUFF) format --check src/ tests/

type-check: ## Run type checker (MyPy)
	$(MYPY) src/reasoning_trading --ignore-missing-imports
	@echo "$(GREEN)Type checking passed$(NC)"

security-check: ## Run security checks (Bandit)
	$(VENV)/bin/bandit -r src/ -c pyproject.toml
	@echo "$(GREEN)Security check passed$(NC)"

check: lint format-check type-check ## Run all code quality checks
	@echo "$(GREEN)All checks passed$(NC)"

# =============================================================================
# Pre-commit
# =============================================================================
pre-commit-install: ## Install pre-commit hooks
	$(VENV)/bin/pre-commit install
	$(VENV)/bin/pre-commit install --hook-type commit-msg
	@echo "$(GREEN)Pre-commit hooks installed$(NC)"

pre-commit-run: ## Run pre-commit on all files
	$(VENV)/bin/pre-commit run --all-files

pre-commit-update: ## Update pre-commit hooks
	$(VENV)/bin/pre-commit autoupdate

# =============================================================================
# Docker
# =============================================================================
docker-build: ## Build Docker image
	docker build -t reasoning-trading:latest .
	@echo "$(GREEN)Docker image built$(NC)"

docker-build-dev: ## Build Docker image for development
	docker build --target development -t reasoning-trading:dev .
	@echo "$(GREEN)Development Docker image built$(NC)"

docker-run: ## Run Docker container
	docker run -it --rm \
		--env-file .env \
		-p 8000:8000 \
		reasoning-trading:latest

docker-run-api: ## Run API server in Docker
	docker run -it --rm \
		--env-file .env \
		-p 8000:8000 \
		reasoning-trading:latest trading-api

docker-test: ## Run tests in Docker
	docker run -it --rm \
		reasoning-trading:latest \
		pytest tests/ -v --tb=short

docker-compose-up: ## Start services with docker-compose
	docker-compose up -d
	@echo "$(GREEN)Services started$(NC)"

docker-compose-down: ## Stop services with docker-compose
	docker-compose down
	@echo "$(GREEN)Services stopped$(NC)"

docker-compose-logs: ## View docker-compose logs
	docker-compose logs -f

# =============================================================================
# Running the Application
# =============================================================================
run-api: ## Run the API server
	$(VENV)/bin/trading-api

run-api-dev: ## Run the API server in development mode
	$(VENV)/bin/uvicorn reasoning_trading.api.server:app --reload --host 0.0.0.0 --port 8000

run-cli: ## Show CLI help
	$(VENV)/bin/reasoning-trading --help

analyze: ## Run analysis on a symbol (usage: make analyze SYMBOL=AAPL)
	$(VENV)/bin/reasoning-trading analyze $(SYMBOL)

# =============================================================================
# Documentation
# =============================================================================
docs: ## Generate documentation
	@echo "$(YELLOW)Documentation generation not yet configured$(NC)"

docs-serve: ## Serve documentation locally
	@echo "$(YELLOW)Documentation serving not yet configured$(NC)"

# =============================================================================
# Release
# =============================================================================
build: ## Build distribution packages
	$(PIP) install build
	$(PYTHON) -m build
	@echo "$(GREEN)Distribution packages built in dist/$(NC)"

release-check: ## Check if release is ready
	$(PIP) install twine
	twine check dist/*

version: ## Show current version
	@grep "^version" pyproject.toml | head -1

bump-patch: ## Bump patch version (X.Y.Z -> X.Y.Z+1)
	@echo "$(YELLOW)Use 'bump2version patch' for version bumping$(NC)"

bump-minor: ## Bump minor version (X.Y.Z -> X.Y+1.0)
	@echo "$(YELLOW)Use 'bump2version minor' for version bumping$(NC)"

bump-major: ## Bump major version (X.Y.Z -> X+1.0.0)
	@echo "$(YELLOW)Use 'bump2version major' for version bumping$(NC)"

# =============================================================================
# Development Utilities
# =============================================================================
env: ## Create .env file from template
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "$(GREEN)Created .env from .env.example$(NC)"; \
	else \
		echo "$(YELLOW).env already exists$(NC)"; \
	fi

shell: ## Open Python shell with project imported
	$(VENV)/bin/python -c "from reasoning_trading import *; import code; code.interact(local=locals())"

ipython: ## Open IPython shell with project imported
	$(VENV)/bin/ipython -i -c "from reasoning_trading import *"

redis-start: ## Start Redis server (if installed locally)
	redis-server --daemonize yes
	@echo "$(GREEN)Redis server started$(NC)"

redis-stop: ## Stop Redis server
	redis-cli shutdown || true
	@echo "$(GREEN)Redis server stopped$(NC)"

redis-cli: ## Open Redis CLI
	redis-cli

# =============================================================================
# CI/CD Helpers
# =============================================================================
ci-lint: ## Run CI linting (used in GitHub Actions)
	$(RUFF) check src/ tests/ --output-format=github
	$(RUFF) format --check src/ tests/

ci-test: ## Run CI tests (used in GitHub Actions)
	$(PYTEST) tests/ \
		-v \
		--tb=short \
		--cov=reasoning_trading \
		--cov-report=xml \
		--junitxml=junit.xml

ci-security: ## Run CI security checks (used in GitHub Actions)
	$(VENV)/bin/pip-audit --desc
	$(VENV)/bin/bandit -r src/ -c pyproject.toml
