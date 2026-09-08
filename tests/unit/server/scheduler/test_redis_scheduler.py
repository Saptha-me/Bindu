"""Unit tests for Redis Scheduler."""

import asyncio
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bindu.common.protocol.types import TaskSendParams
from bindu.server.scheduler.redis_scheduler import RedisScheduler


@pytest.fixture
def mock_redis_client():
    """Create a mock Redis client."""
    client = AsyncMock()
    # Setup default return values
    client.ping.return_value = True
    client.rpush.return_value = 1
    client.blpop.return_value = None
    client.llen.return_value = 0
    client.delete.return_value = 0
    client.aclose.return_value = None
    return client


@pytest.fixture
def scheduler(mock_redis_client):
    """Create a RedisScheduler instance with mocked Redis client."""
    with patch("redis.asyncio.from_url", return_value=mock_redis_client):
        # We start with a scheduler instance. 
        # Note: We rely on the async context manager in tests to initialize connections.
        sched = RedisScheduler(redis_url="redis://localhost:6379", poll_timeout=0.1)
        yield sched


@pytest.mark.asyncio
async def test_connection(scheduler, mock_redis_client):
    """Test Redis connection lifecycle."""
    # Test context manager entry (connect & ping)
    async with scheduler as s:
        assert s._redis_client == mock_redis_client
        mock_redis_client.ping.assert_called_once()
        assert await s.health_check() is True

    # Test context manager exit (close)
    mock_redis_client.aclose.assert_called_once()
    assert await scheduler.health_check() is False


@pytest.mark.asyncio
async def test_push_task(scheduler, mock_redis_client):
    """Test pushing a task to Redis."""
    async with scheduler:
        params = TaskSendParams(
            to="agent-id",
            input={"text": "hello"}
        )
        
        # Test run_task
        await scheduler.run_task(params)
        
        # Verify rpush was called
        assert mock_redis_client.rpush.call_count == 1
        args = mock_redis_client.rpush.call_args[0]
        assert args[0] == "bindu:tasks"  # queue name
        
        # Verify serialization
        payload = json.loads(args[1])
        assert payload["operation"] == "run"
        assert payload["params"]["to"] == "agent-id"
        assert payload["params"]["input"] == {"text": "hello"}
        # Span ID and trace ID might be null or present depending on OpenTelemetry mock state, 
        # checking structure is enough.
        assert "span_id" in payload
        assert "trace_id" in payload


@pytest.mark.asyncio
async def test_push_task_calls(scheduler, mock_redis_client):
    """Test other push operations (cancel, pause, resume)."""
    async with scheduler:
        task_id = str(uuid.uuid4())
        params = {"taskId": task_id}
        
        # Cancel
        await scheduler.cancel_task(params)
        assert mock_redis_client.rpush.call_count == 1
        payload = json.loads(mock_redis_client.rpush.call_args[0][1])
        assert payload["operation"] == "cancel"
        assert "span_id" in payload
        assert "trace_id" in payload
        mock_redis_client.rpush.reset_mock()
        
        # Pause
        await scheduler.pause_task(params)
        assert mock_redis_client.rpush.call_count == 1
        payload = json.loads(mock_redis_client.rpush.call_args[0][1])
        assert payload["operation"] == "pause"
        assert "span_id" in payload
        assert "trace_id" in payload
        mock_redis_client.rpush.reset_mock()

        # Resume
        await scheduler.resume_task(params)
        assert mock_redis_client.rpush.call_count == 1
        payload = json.loads(mock_redis_client.rpush.call_args[0][1])
        assert payload["operation"] == "resume"
        assert "span_id" in payload
        assert "trace_id" in payload


@pytest.mark.asyncio
async def test_receive_task(scheduler, mock_redis_client):
    """Test receiving a task from Redis."""
    async with scheduler:
        # Mock blpop return value
        # blpop returns (queue_name, data)
        task_data = {
            "operation": "run",
            "params": {
                "to": "agent-id",
                "input": {"text": "hello"}
            },
            "span_id": None,
            "trace_id": None
        }
        mock_redis_client.blpop.side_effect = [
            ("bindu:tasks", json.dumps(task_data)),
        ]
        
        # Consume generator
        operations = scheduler.receive_task_operations()
        operation = await asyncio.wait_for(anext(operations), timeout=1)
        assert operation["operation"] == "run"
        assert operation["params"]["to"] == "agent-id"
        await operations.aclose()
            
        mock_redis_client.blpop.assert_called()


@pytest.mark.asyncio
async def test_receive_task_uuids(scheduler, mock_redis_client):
    """Test UUID handling during deserialization."""
    async with scheduler:
        task_id = str(uuid.uuid4())
        task_data = {
            "operation": "cancel",
            "params": {"taskId": task_id},
            "span_id": None, 
            "trace_id": None
        }
        
        mock_redis_client.blpop.side_effect = [
            ("bindu:tasks", json.dumps(task_data)),
        ]
        
        operations = scheduler.receive_task_operations()
        operation = await asyncio.wait_for(anext(operations), timeout=1)
        assert operation["operation"] == "cancel"
        received_id = operation["params"]["taskId"]
        assert isinstance(received_id, uuid.UUID)
        assert str(received_id) == task_id
        await operations.aclose()


@pytest.mark.asyncio
async def test_receive_error_handling(scheduler, mock_redis_client):
    """Test resilience against errors in receive loop."""
    async with scheduler:
        # Sequence:
        # 1. Invalid JSON (should be logged and skipped)
        # 2. Redis Error (should be logged and skipped/retried)
        # 3. Valid Item
        
        valid_task = {
            "operation": "run", 
            "params": {"to": "agent", "input": {}},
            "span_id": None, "trace_id": None
        }
        
        import redis
        
        mock_redis_client.blpop.side_effect = [
            ("queue", "invalid-json"),
            redis.RedisError("Redis temporarily down"),
            ("queue", json.dumps(valid_task)),
        ]
        
        with patch("bindu.server.scheduler.redis_scheduler.asyncio.sleep") as mock_sleep:
            operations = scheduler.receive_task_operations()
            op = await asyncio.wait_for(anext(operations), timeout=1)
            assert op["operation"] == "run"
            await operations.aclose()
            mock_sleep.assert_called_once()
            
        # Verify it called blpop multiple times despite errors
        assert mock_redis_client.blpop.call_count >= 3


@pytest.mark.asyncio
async def test_queue_management(scheduler, mock_redis_client):
    """Test queue management methods."""
    async with scheduler:
        mock_redis_client.llen.return_value = 42
        assert await scheduler.get_queue_length() == 42
        mock_redis_client.llen.assert_called_with("bindu:tasks")
        
        mock_redis_client.delete.return_value = 1
        assert await scheduler.clear_queue() == 1
        mock_redis_client.delete.assert_called_with("bindu:tasks")
