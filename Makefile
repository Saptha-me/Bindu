# Makefile for Pebbling project using uv

.PHONY: install dev test coverage lint format build publish clean

# Install production dependencies
install:
	uv sync

# Install development dependencies
dev:
	uv sync --dev

# Run tests
test:
	uv run pytest -n auto

# Run tests with coverage
coverage:
	uv run pytest --cov=pebbling --cov-report=term-missing -n auto

# Lint code using ruff and mypy
lint:
	uv run ruff check .
	uv run mypy pebbling

# Format code using ruff
format:
	uv run ruff format .

# Build the package
build:
	uv build

# Publish the package to PyPI
publish:
	uv publish

# Clean build artifacts
clean:
	rm -rf dist/ build/ *.egg-info .coverage .pytest_cache coverage_html_report
	find . -type d -name '__pycache__' -exec rm -rf {} +
