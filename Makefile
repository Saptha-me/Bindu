# Test commands
# -------------

# Run all tests
test:
	@echo "Running all tests..."
	python -m pytest -n auto

# Run tests with coverage report
test-coverage:
	@echo "Running tests with coverage..."
	python -m pytest --cov=pebbling --cov-report=term-missing -n auto