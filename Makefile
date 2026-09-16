# Enaya Agent - Makefile
# Common development tasks

.PHONY: help install test lint format typecheck build clean docker-build docker-run docs release

# Default target
help:
	@echo "Enaya Agent - Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  install       - Install package in development mode with all extras"
	@echo "  install-dev   - Install with development dependencies"
	@echo ""
	@echo "Testing:"
	@echo "  test          - Run unit tests with coverage"
	@echo "  test-unit     - Run unit tests only"
	@echo "  test-integration - Run integration tests"
	@echo "  test-e2e      - Run end-to-end tests"
	@echo ""
	@echo "Code Quality:"
	@echo "  lint          - Run ruff linter"
	@echo "  format        - Format code with ruff"
	@echo "  format-check  - Check formatting with ruff"
	@echo "  typecheck     - Run mypy type checker"
	@echo "  quality       - Run all quality checks (lint, format-check, typecheck)"
	@echo ""
	@echo "Building:"
	@echo "  build         - Build Python package (wheel + sdist)"
	@echo "  build-docker  - Build Docker image"
	@echo "  run-docker    - Run Docker container"
	@echo ""
	@echo "Documentation:"
	@echo "  docs          - Build documentation with mkdocs"
	@echo "  docs-serve    - Serve documentation locally"
	@echo ""
	@echo "Development:"
	@echo "  run           - Run enaya chat with default model"
	@echo "  run-tui       - Run TUI interface"
	@echo "  run-api       - Run API server"
	@echo "  setup         - Run interactive setup"
	@echo ""
	@echo "Maintenance:"
	@echo "  clean         - Clean build artifacts"
	@echo "  clean-all     - Clean everything including virtual environments"

# ============================================================
# Setup
# ============================================================
install:
	pip install -e ".[dev]"

install-dev:
	pip install -e ".[dev,test,docs]"

# ============================================================
# Testing
# ============================================================
test: test-unit

test-unit:
	pytest tests/ -v --cov=enaya --cov-report=term-missing

test-integration:
	pytest tests/integration/ -v -x

test-e2e:
	pytest tests/e2e/ -v -x

# ============================================================
# Code Quality
# ============================================================
lint:
	ruff check src/enaya tests

format:
	ruff format src/enaya tests

format-check:
	ruff format --check src/enaya tests

typecheck:
	mypy src/enaya

quality: lint format-check typecheck

# ============================================================
# Building
# ============================================================
build:
	python -m build

build-docker:
	docker build -t enaya-agent:latest .

run-docker:
	docker run --rm -it \
		-v $(HOME)/.enaya:/home/enaya/.enaya \
		-e OPENROUTER_API_KEY \
		-e NVIDIA_API_KEY \
		enaya-agent:latest chat -q "Hello"

# ============================================================
# Documentation
# ============================================================
docs:
	mkdocs build

docs-serve:
	mkdocs serve

# ============================================================
# Development
# ============================================================
run:
	enaya chat -q "Hello, Enaya!"

run-tui:
	enaya tui

run-api:
	enaya api-server --host 0.0.0.0 --port 8000

setup:
	enaya setup

# ============================================================
# Maintenance
# ============================================================
clean:
	rm -rf build/ dist/ *.egg-info/ .pytest_cache/ .coverage coverage.xml htmlcov/ .mypy_cache/ .ruff_cache/ site/ bandit-report.json pip-audit-report.json

clean-all: clean
	rm -rf venv/ .venv/ env/ .env