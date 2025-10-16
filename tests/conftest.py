"""Pytest configuration and fixtures for Bindu tests."""

# Provide a lightweight opentelemetry.trace stub unconditionally for tests
import sys
from types import ModuleType

ot_trace = ModuleType("opentelemetry.trace")


class _Span:
    def is_recording(self):
        return True

    def add_event(self, *args, **kwargs):  # noqa: D401
        return None

    def set_attributes(self, *args, **kwargs):  # noqa: D401
        return None

    def set_attribute(self, *args, **kwargs):  # noqa: D401
        return None

    def set_status(self, *args, **kwargs):  # noqa: D401
        return None


def get_current_span():  # noqa: D401
    return _Span()


class _SpanCtx:
    def __enter__(self):
        return _Span()

    def __exit__(self, exc_type, exc, tb):  # noqa: D401
        return False


class _Tracer:
    def start_as_current_span(self, name: str):  # noqa: ARG002
        return _SpanCtx()

    def start_span(self, name: str):  # noqa: ARG002
        return _Span()


class _StatusCode:
    OK = "OK"
    ERROR = "ERROR"


class _Status:
    def __init__(self, *args, **kwargs):  # noqa: D401, ARG002
        pass


ot_trace.get_current_span = get_current_span  # type: ignore[attr-defined]
ot_trace.get_tracer = lambda name: _Tracer()  # type: ignore[attr-defined]
ot_trace.Status = _Status  # type: ignore[attr-defined]
ot_trace.StatusCode = _StatusCode  # type: ignore[attr-defined]
ot_trace.Span = _Span  # type: ignore[attr-defined]
ot_trace.use_span = lambda span: _SpanCtx()  # type: ignore[attr-defined]

# Build minimal opentelemetry root and metrics stub
op_root = ModuleType("opentelemetry")

metrics_mod = ModuleType("opentelemetry.metrics")

class _Counter:
    def add(self, *_args, **_kwargs):  # noqa: D401
        return None


class _Histogram:
    def record(self, *_args, **_kwargs):  # noqa: D401
        return None


class _UpDownCounter:
    def add(self, *_args, **_kwargs):  # noqa: D401
        return None


class _Meter:
    def create_counter(self, *_args, **_kwargs):  # noqa: D401
        return _Counter()

    def create_histogram(self, *_args, **_kwargs):  # noqa: D401
        return _Histogram()

    def create_up_down_counter(self, *_args, **_kwargs):  # noqa: D401
        return _UpDownCounter()


def get_meter(name: str):  # noqa: D401, ARG001
    return _Meter()


metrics_mod.get_meter = get_meter  # type: ignore[attr-defined]

op_root.metrics = metrics_mod  # type: ignore[attr-defined]
op_root.trace = ot_trace  # type: ignore[attr-defined]

sys.modules["opentelemetry"] = op_root
sys.modules["opentelemetry.trace"] = ot_trace
sys.modules["opentelemetry.metrics"] = metrics_mod

import asyncio
from typing import AsyncGenerator, cast
from uuid import uuid4

import pytest
import pytest_asyncio  # type: ignore[import-untyped]

from bindu.common.models import AgentManifest
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
        manifest=cast(AgentManifest, mock_manifest_with_push),
    )
    tm.notification_service = cast(MockNotificationService, mock_notification_service)  # type: ignore[assignment]
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
        manifest=cast(AgentManifest, mock_manifest),
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
