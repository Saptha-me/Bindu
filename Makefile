# Makefile for Pebble (using uv)

.PHONY: all clean install dev lint format type-check test coverage build dist upload docs help examples

PYTHON := python3
UV := uv
PACKAGE := pebble
SRC_DIR := src
TESTS_DIR := tests
DOCS_DIR := docs
EXAMPLES_DIR := examples
VENV := .venv

all: clean lint test build

# Virtual environment
$(VENV):
	$(UV) venv $(VENV)

# Installation
install: $(VENV)
	$(UV) pip install -e .

dev: $(VENV)
	$(UV) pip install -e ".[dev,all]"

# Formatting & Linting
format: $(VENV)
	$(UV) run black $(SRC_DIR) $(TESTS_DIR) $(EXAMPLES_DIR)
	$(UV) run isort $(SRC_DIR) $(TESTS_DIR) $(EXAMPLES_DIR)

lint: $(VENV)
	$(UV) run ruff $(SRC_DIR) $(TESTS_DIR) $(EXAMPLES_DIR)
	$(UV) run black --check $(SRC_DIR) $(TESTS_DIR) $(EXAMPLES_DIR)
	$(UV) run isort --check $(SRC_DIR) $(TESTS_DIR) $(EXAMPLES_DIR)

type-check: $(VENV)
	$(UV) run mypy $(SRC_DIR)

# Testing
test: $(VENV)
	$(UV) run pytest $(TESTS_DIR)

integration-test: $(VENV)
	$(UV) run pytest $(TESTS_DIR)/integration

coverage: $(VENV)
	$(UV) run pytest --cov=$(PACKAGE) --cov-report=xml --cov-report=term $(TESTS_DIR)

# Building and distribution
build: $(VENV) clean
	$(UV) run build

dist: build

upload: $(VENV) build
	$(UV) run twine upload dist/*

upload-test: $(VENV) build
	$(UV) run twine upload --repository-url https://test.pypi.org/legacy/ dist/*

# Documentation
docs: $(VENV)
	$(UV) run sphinx-build -b html $(DOCS_DIR)/source $(DOCS_DIR)/build/html

# Run examples
examples-local: $(VENV)
	$(UV) run python $(EXAMPLES_DIR)/deploy_local_server.py

examples-router: $(VENV)
	$(UV) run python $(EXAMPLES_DIR)/deploy_with_router.py

examples-docker: $(VENV)
	$(UV) run python $(EXAMPLES_DIR)/deploy_with_docker.py

examples-multi: $(VENV)
	$(UV) run python $(EXAMPLES_DIR)/multi_agent_example.py

# Synchronize dependencies
sync-deps:
	$(UV) pip sync

# Generate requirements files
requirements:
	$(UV) pip export > requirements.txt
	$(UV) pip export --dev > requirements-dev.txt

# Cleaning
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .coverage
	rm -rf coverage.xml
	rm -rf .pytest_cache/
	rm -rf .ruff_cache/
	rm -rf $(DOCS_DIR)/build/
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name "*.pyc" -delete
	find . -type d -name ".DS_Store" -delete

clean-all: clean
	rm -rf $(VENV)/

# Help
help:
	@echo "Available commands (using uv):"
	@echo "  make install          Install the package"
	@echo "  make dev              Install the package with development dependencies"
	@echo "  make sync-deps        Synchronize dependencies"
	@echo "  make requirements     Generate requirements.txt files"
	@echo "  make format           Format code with black and isort"
	@echo "  make lint             Run linters (ruff, black, isort)"
	@echo "  make type-check       Run type checking with mypy"
	@echo "  make test             Run tests"
	@echo "  make integration-test Run integration tests"
	@echo "  make coverage         Run tests with coverage"
	@echo "  make build            Build package distribution"
	@echo "  make upload           Upload package to PyPI"
	@echo "  make upload-test      Upload package to Test PyPI"
	@echo "  make docs             Build documentation"
	@echo "  make examples-local   Run local server example"
	@echo "  make examples-router  Run router registration example"
	@echo "  make examples-docker  Run Docker deployment example"
	@echo "  make examples-multi   Run multi-agent example"
	@echo "  make clean            Clean build artifacts"
	@echo "  make clean-all        Clean build artifacts and virtual environment"
	@echo "  make all              Run clean, lint, test, and build"