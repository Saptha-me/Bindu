"""Pytest configuration and fixtures for Bindu tests."""

import asyncio
from typing import AsyncGenerator
from uuid import uuid4

import pytest
import pytest_asyncio

from bindu.server.scheduler.memory_scheduler import InMemoryScheduler

# Import directly from submodules to avoid circular imports
from bindu.server.storage.memory_storage import InMemoryStorage
from tests.mocks import (
    MockAgent,
    MockDIDExtension,
    MockManifest,
    MockNotificationService,
)
from tests.utils import create_test_context, create_test_message, create_test_task


# Configure asyncio for pytest
@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def storage() -> InMemoryStorage:
    """Create an in-memory storage instance."""
    return InMemoryStorage()


@pytest_asyncio.fixture
async def scheduler() -> AsyncGenerator[InMemoryScheduler, None]:
    """Create an in-memory scheduler instance."""
    sched = InMemoryScheduler()
    async with sched:
        yield sched


@pytest.fixture
def mock_agent() -> MockAgent:
    """Create a mock agent that returns normal responses."""
    return MockAgent(response="Test agent response")


@pytest.fixture
def mock_agent_input_required() -> MockAgent:
    """Create a mock agent that requires input."""
    return MockAgent(response="What is your name?", response_type="input-required")


@pytest.fixture
def mock_agent_auth_required() -> MockAgent:
    """Create a mock agent that requires authentication."""
    return MockAgent(response="Please provide API key", response_type="auth-required")


@pytest.fixture
def mock_agent_error() -> MockAgent:
    """Create a mock agent that raises an error."""
    return MockAgent(response="Agent execution failed", response_type="error")


@pytest.fixture
def mock_manifest(mock_agent: MockAgent) -> MockManifest:
    """Create a mock manifest with default agent."""
    return MockManifest(agent_fn=mock_agent)


@pytest.fixture
def mock_manifest_with_push() -> MockManifest:
    """Create a mock manifest with push notifications enabled."""
    return MockManifest(capabilities={"push_notifications": True})


@pytest.fixture
def mock_did_extension() -> MockDIDExtension:
    """Create a mock DID extension."""
    return MockDIDExtension()


@pytest.fixture
def mock_notification_service() -> MockNotificationService:
    """Create a mock notification service."""
    return MockNotificationService()


@pytest_asyncio.fixture
async def task_manager(
    storage: InMemoryStorage,
    scheduler: InMemoryScheduler,
):
    """Create a TaskManager for unit testing (without worker)."""
    # Import here to avoid circular import
    from bindu.server.task_manager import TaskManager

    # Create TaskManager without manifest to avoid worker startup issues in unit tests
    tm = TaskManager(
        scheduler=scheduler,
        storage=storage,
        manifest=None,
    )
    yield tm


@pytest_asyncio.fixture
async def task_manager_with_push(
    storage: InMemoryStorage,
    scheduler: InMemoryScheduler,
    mock_manifest_with_push: MockManifest,
    mock_notification_service: MockNotificationService,
):
    """Create a TaskManager with push notifications enabled."""
    # Import here to avoid circular import
    from bindu.server.task_manager import TaskManager

    tm = TaskManager(
        scheduler=scheduler,
        storage=storage,
        manifest=mock_manifest_with_push,
    )
    tm.notification_service = mock_notification_service
    await tm.__aenter__()
    yield tm
    await tm.__aexit__(None, None, None)


@pytest_asyncio.fixture
async def bindu_app(
    mock_manifest: MockManifest,
    storage: InMemoryStorage,
    scheduler: InMemoryScheduler,
):
    """Create a BinduApplication for endpoint testing."""
    # Import here to avoid circular import
    from bindu.server.applications import BinduApplication

    app = BinduApplication(
        manifest=mock_manifest,
        storage=storage,
        scheduler=scheduler,
        url="http://localhost:8030",
        version="1.0.0",
    )

    async with app:
        yield app


# Sample data fixtures
@pytest.fixture
def sample_message():
    """Create a sample message."""
    return create_test_message(text="Hello, agent!")


@pytest.fixture
def sample_task():
    """Create a sample task."""
    return create_test_task(state="submitted")


@pytest.fixture
def sample_context():
    """Create a sample context."""
    return create_test_context()


@pytest.fixture
def sample_task_with_history(sample_message):
    """Create a task with message history."""
    msg1 = create_test_message(text="First message")
    msg2 = create_test_message(text="Second message")
    return create_test_task(state="working", history=[msg1, msg2])


# Deterministic UUIDs for testing
@pytest.fixture
def test_uuid_1():
    """First test UUID."""
    return uuid4()


@pytest.fixture
def test_uuid_2():
    """Second test UUID."""
    return uuid4()


@pytest.fixture
def test_uuid_3():
    """Third test UUID."""
    return uuid4()
