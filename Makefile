.PHONY: help install install-dev test test-unit test-integration test-e2e coverage lint format typecheck clean build

help: ## Show this help message
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'

install: ## Install the package
	pip install -e .

install-dev: ## Install the package with development dependencies
	pip install -e ".[dev]"

test: ## Run all tests
	pytest tests/ -v

test-unit: ## Run unit tests only
	pytest tests/unit/ -v

test-integration: ## Run integration tests only
	pytest tests/integration/ -v

test-e2e: ## Run end-to-end tests only
	pytest tests/e2e/ -v

coverage: ## Run tests with coverage report
	pytest tests/ --cov=mcp_cube_server --cov-report=term-missing --cov-report=html

lint: ## Run linting checks
	ruff check src/ tests/

format: ## Format code with ruff
	ruff format src/ tests/
	ruff check --fix src/ tests/

typecheck: ## Run type checking with mypy
	mypy src/

clean: ## Clean build artifacts and cache files
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf .ruff_cache/
	rm -rf .mypy_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

build: clean ## Build distribution packages
	python -m build

run: ## Run the server with environment variables
	python -m mcp_cube_server

docker-build: ## Build Docker image
	docker build -t mcp-cube-server .

docker-run: ## Run Docker container
	docker run --env-file .env mcp-cube-server

check: lint typecheck test ## Run all checks (lint, typecheck, test)