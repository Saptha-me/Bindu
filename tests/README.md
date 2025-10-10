# Bindu Test Suite

Comprehensive test suite for the Bindu A2A protocol implementation.

## Test Structure

```
tests/
├── unit/                           # Unit tests (fast, isolated)
│   ├── test_protocol_types.py     # Protocol type validation
│   ├── test_storage.py             # Storage layer tests
│   ├── test_scheduler.py           # Task scheduler tests
│   ├── test_manifest_worker.py     # Worker & hybrid pattern tests
│   └── test_task_manager.py        # TaskManager tests
├── integration/                    # Integration tests
│   └── test_postman_scenarios.py   # Postman collection scenarios
├── e2e/                            # End-to-end tests
├── conftest.py                     # Pytest fixtures
├── utils.py                        # Test utilities
└── mocks.py                        # Mock objects
```

## Running Tests

### Run All Tests
```bash
pytest
```

### Run Specific Test Categories
```bash
# Unit tests only
pytest tests/unit/

# Integration tests only
pytest tests/integration/

# Specific test file
pytest tests/unit/test_protocol_types.py

# Specific test class
pytest tests/unit/test_storage.py::TestTaskStorage

# Specific test
pytest tests/unit/test_storage.py::TestTaskStorage::test_save_and_load_task
```

### Run with Coverage
```bash
# Install pytest-cov first
uv add --dev pytest-cov

# Run with coverage
pytest --cov=bindu --cov-report=html --cov-report=term-missing

# View HTML coverage report
open htmlcov/index.html
```

### Run with Markers
```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run only asyncio tests
pytest -m asyncio

# Exclude slow tests
pytest -m "not slow"
```

### Verbose Output
```bash
# Extra verbose
pytest -vv

# Show print statements
pytest -s

# Show local variables on failure
pytest -l
```

## Test Coverage

Current test coverage by module:

- **Protocol Types**: Message, Task, Artifact, Context validation
- **Storage**: CRUD operations, concurrency, data integrity
- **Scheduler**: Task queuing, FIFO ordering, lifecycle
- **ManifestWorker**: Hybrid pattern (normal, input-required, auth-required)
- **TaskManager**: All JSON-RPC handlers
- **Postman Scenarios**: Complete A2A protocol flows

## Writing New Tests

### Test File Template
```python
"""Description of what this module tests."""

import pytest
from uuid import uuid4

from bindu.common.protocol.types import Task
from tests.utils import create_test_task, assert_task_state


class TestFeatureName:
    """Test specific feature."""

    @pytest.mark.asyncio
    async def test_specific_behavior(self, storage):
        """Test description."""
        # Arrange
        message = create_test_message(text="Test request")

        # Act - Use submit_task to create tasks
        task = await storage.submit_task(message["context_id"], message)

        # Assert
        loaded = await storage.load_task(task["id"])
        assert_task_state(loaded, "submitted")
```

### Using Fixtures
```python
# Available fixtures (see conftest.py):
- storage: InMemoryStorage instance
- scheduler: InMemoryScheduler instance
- task_manager: Fully configured TaskManager
- mock_agent: Mock agent with normal responses
- mock_agent_input_required: Mock agent requiring input
- mock_agent_auth_required: Mock agent requiring auth
- mock_manifest: Mock AgentManifest
- sample_message: Sample Message object
- sample_task: Sample Task object
- sample_context: Sample Context object
```

### Using Utilities
```python
from tests.utils import (
    create_test_message,
    create_test_task,
    create_test_artifact,
    create_test_context,
    assert_task_state,
    assert_jsonrpc_error,
    assert_jsonrpc_success,
)

# Create test data
message = create_test_message(text="Hello")
task = create_test_task(state="working")
artifact = create_test_artifact(text="Result")

# Assertions
assert_task_state(task, "completed")
assert_jsonrpc_error(response, -32001)  # TaskNotFoundError
assert_jsonrpc_success(response)
```

## Continuous Integration

Tests are run automatically on:
- Every commit (unit tests)
- Pull requests (all tests)
- Main branch (all tests + coverage)

## Troubleshooting

### Common Issues

**Import errors:**
```bash
# Make sure bindu is installed in development mode
uv sync --dev
```

**Async warnings:**
```bash
# Install pytest-asyncio
uv add --dev pytest-asyncio
```

**Fixture not found:**
```bash
# Check conftest.py is in the right location
# Fixtures are auto-discovered from conftest.py
```

**Tests hanging:**
```bash
# Add timeout to async tests
pytest --timeout=10
```

## Test Principles

1. **DRY**: Use fixtures and utilities to avoid duplication
2. **Type-Safe**: Use protocol types throughout
3. **Async**: All I/O tests use pytest-asyncio
4. **Isolation**: Each test is independent
5. **Fast**: Unit tests should be < 100ms each
6. **Readable**: Clear test names and assertions
7. **A2A Compliant**: Follow protocol exactly

## Contributing

When adding new features:
1. Write tests first (TDD)
2. Ensure all tests pass
3. Maintain >90% coverage for new code
4. Add integration tests for new endpoints
5. Update this README if needed
