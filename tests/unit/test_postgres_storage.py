"""Tests for PostgreSQL storage implementation.

This module tests the PostgreSQL storage backend with focus on:
- Connection management and retry logic
- Task CRUD operations
- Context management
- Transaction handling
- Error scenarios
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from bindu.server.storage.postgres_storage import PostgresStorage, _serialize_for_jsonb
from tests.utils import create_test_message


class TestSerializeForJsonb:
    """Test JSONB serialization helper."""

    def test_serialize_uuid(self):
        """Test UUID serialization."""
        test_uuid = uuid4()
        result = _serialize_for_jsonb(test_uuid)
        assert isinstance(result, str)
        assert result == str(test_uuid)

    def test_serialize_dict_with_uuid(self):
        """Test dict with UUID values."""
        test_uuid = uuid4()
        data = {"id": test_uuid, "name": "test"}
        result = _serialize_for_jsonb(data)
        assert result["id"] == str(test_uuid)
        assert result["name"] == "test"

    def test_serialize_list_with_uuid(self):
        """Test list with UUID values."""
        test_uuid = uuid4()
        data = [test_uuid, "test", 123]
        result = _serialize_for_jsonb(data)
        assert result[0] == str(test_uuid)
        assert result[1] == "test"
        assert result[2] == 123

    def test_serialize_nested_structure(self):
        """Test nested dict/list with UUIDs."""
        test_uuid = uuid4()
        data = {"outer": {"inner": [test_uuid, {"deep": test_uuid}]}}
        result = _serialize_for_jsonb(data)
        assert result["outer"]["inner"][0] == str(test_uuid)
        assert result["outer"]["inner"][1]["deep"] == str(test_uuid)

    def test_serialize_primitives(self):
        """Test primitive types pass through."""
        assert _serialize_for_jsonb("test") == "test"
        assert _serialize_for_jsonb(123) == 123
        assert _serialize_for_jsonb(True) is True
        assert _serialize_for_jsonb(None) is None


class TestPostgresStorageInit:
    """Test PostgresStorage initialization."""

    def test_init_default_values(self):
        """Test initialization with default values."""
        storage = PostgresStorage()
        assert storage._engine is None
        assert storage._session_factory is None
        assert "postgresql+asyncpg://" in storage.database_url

    def test_init_custom_url(self):
        """Test initialization with custom database URL."""
        custom_url = (
            "postgresql://user:pass@localhost:5432/testdb"  # pragma: allowlist secret
        )
        storage = PostgresStorage(database_url=custom_url)
        assert "postgresql+asyncpg://" in storage.database_url
        assert "user:pass@localhost:5432/testdb" in storage.database_url

    def test_init_asyncpg_url(self):
        """Test initialization with asyncpg URL."""
        custom_url = "postgresql+asyncpg://user:pass@localhost:5432/testdb"
        storage = PostgresStorage(database_url=custom_url)
        assert storage.database_url == custom_url

    def test_init_custom_pool_settings(self):
        """Test initialization with custom pool settings."""
        storage = PostgresStorage(
            pool_min=5, pool_max=20, timeout=60, command_timeout=120
        )
        assert storage.pool_min == 5
        assert storage.pool_max == 20
        assert storage.timeout == 60
        assert storage.command_timeout == 120


class TestPostgresStorageConnection:
    """Test PostgresStorage connection management."""

    @pytest.mark.asyncio
    async def test_ensure_connected_raises_when_not_connected(self):
        """Test _ensure_connected raises when engine not initialized."""
        storage = PostgresStorage()
        with pytest.raises(RuntimeError, match="PostgreSQL engine not initialized"):
            storage._ensure_connected()

    @pytest.mark.asyncio
    async def test_connect_success(self):
        """Test successful connection."""
        storage = PostgresStorage()

        with patch(
            "bindu.server.storage.postgres_storage.create_async_engine"
        ) as mock_engine:
            mock_engine_instance = MagicMock()

            # Create a proper async context manager for begin()
            mock_conn = MagicMock()
            mock_conn.execute = AsyncMock()

            mock_begin_context = AsyncMock()
            mock_begin_context.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_begin_context.__aexit__ = AsyncMock(return_value=None)

            mock_engine_instance.begin = MagicMock(return_value=mock_begin_context)
            mock_engine.return_value = mock_engine_instance

            with patch("bindu.server.storage.postgres_storage.async_sessionmaker"):
                await storage.connect()

                assert storage._engine is not None
                assert storage._session_factory is not None

    @pytest.mark.asyncio
    async def test_connect_failure(self):
        """Test connection failure handling."""
        storage = PostgresStorage()

        with patch(
            "bindu.server.storage.postgres_storage.create_async_engine"
        ) as mock_engine:
            mock_engine.side_effect = Exception("Connection failed")

            with pytest.raises(
                ConnectionError, match="Failed to connect to PostgreSQL"
            ):
                await storage.connect()

    @pytest.mark.asyncio
    async def test_disconnect(self):
        """Test disconnection."""
        storage = PostgresStorage()

        # Mock engine
        mock_engine = MagicMock()
        mock_engine.dispose = AsyncMock()
        storage._engine = mock_engine
        storage._session_factory = MagicMock()

        await storage.disconnect()

        assert storage._engine is None
        assert storage._session_factory is None
        mock_engine.dispose.assert_called_once()


class TestPostgresStorageTaskOperations:
    """Test PostgresStorage task operations."""

    @pytest.mark.asyncio
    async def test_load_task_invalid_type(self):
        """Test load_task with invalid task_id type."""
        storage = PostgresStorage()

        with pytest.raises(TypeError, match="task_id must be UUID"):
            await storage.load_task("not-a-uuid")  # type: ignore

    @pytest.mark.asyncio
    async def test_load_task_not_connected(self):
        """Test load_task when not connected."""
        storage = PostgresStorage()
        task_id = uuid4()

        with pytest.raises(RuntimeError, match="PostgreSQL engine not initialized"):
            await storage.load_task(task_id)

    @pytest.mark.asyncio
    async def test_submit_task_invalid_context_type(self):
        """Test submit_task with invalid context_id type."""
        storage = PostgresStorage()
        message = create_test_message()

        with pytest.raises(TypeError, match="context_id must be UUID"):
            await storage.submit_task("not-a-uuid", message)  # type: ignore

    @pytest.mark.asyncio
    async def test_row_to_task_conversion(self):
        """Test _row_to_task conversion."""
        storage = PostgresStorage()

        # Create mock row
        mock_row = MagicMock()
        mock_row.id = uuid4()
        mock_row.context_id = uuid4()
        mock_row.kind = "task"
        mock_row.state = "submitted"
        mock_row.state_timestamp = datetime.now(timezone.utc)
        mock_row.history = []
        mock_row.artifacts = []
        mock_row.metadata = {}

        task = storage._row_to_task(mock_row)

        assert task["id"] == mock_row.id
        assert task["context_id"] == mock_row.context_id
        assert task["kind"] == "task"
        assert task["status"]["state"] == "submitted"
        assert isinstance(task["history"], list)
        assert isinstance(task["artifacts"], list)


class TestPostgresStorageRetryLogic:
    """Test PostgresStorage retry logic."""

    @pytest.mark.asyncio
    async def test_retry_on_connection_error_success_first_try(self):
        """Test retry logic succeeds on first attempt."""
        storage = PostgresStorage()

        async def mock_func():
            return "success"

        result = await storage._retry_on_connection_error(mock_func)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_retry_on_connection_error_success_after_retry(self):
        """Test retry logic succeeds after one failure."""
        from sqlalchemy.exc import OperationalError

        storage = PostgresStorage()
        call_count = 0

        async def mock_func():
            nonlocal call_count
            call_count += 1  # type: ignore[has-type]
            if call_count == 1:
                raise OperationalError(
                    "Connection lost", None, Exception("Connection lost")
                )
            return "success"

        with patch(
            "bindu.server.storage.postgres_storage.app_settings"
        ) as mock_settings:
            mock_settings.storage.postgres_max_retries = 3
            mock_settings.storage.postgres_retry_delay = 0.01

            result = await storage._retry_on_connection_error(mock_func)
            assert result == "success"
            assert call_count == 2

    @pytest.mark.asyncio
    async def test_retry_on_connection_error_max_retries_exceeded(self):
        """Test retry logic fails after max retries."""
        from sqlalchemy.exc import OperationalError

        storage = PostgresStorage()

        async def mock_func():
            raise OperationalError(
                "Connection lost", None, Exception("Connection lost")
            )

        with patch(
            "bindu.server.storage.postgres_storage.app_settings"
        ) as mock_settings:
            mock_settings.storage.postgres_max_retries = 2
            mock_settings.storage.postgres_retry_delay = 0.01

            with pytest.raises(OperationalError):
                await storage._retry_on_connection_error(mock_func)


class TestPostgresStorageContextOperations:
    """Test PostgresStorage context operations."""

    @pytest.mark.asyncio
    async def test_load_context_not_connected(self):
        """Test load_context when not connected."""
        storage = PostgresStorage()
        context_id = uuid4()

        with pytest.raises(RuntimeError, match="PostgreSQL engine not initialized"):
            await storage.load_context(context_id)


class TestPostgresStorageEdgeCases:
    """Test edge cases and error scenarios."""

    def test_url_conversion_edge_cases(self):
        """Test various URL format conversions."""
        # Plain URL without scheme
        storage1 = PostgresStorage(database_url="localhost:5432/db")
        assert storage1.database_url.startswith("postgresql+asyncpg://")

        # URL with postgresql:// scheme
        storage2 = PostgresStorage(database_url="postgresql://localhost:5432/db")
        assert storage2.database_url.startswith("postgresql+asyncpg://")
        assert "postgresql://postgresql+asyncpg://" not in storage2.database_url

        # URL already with asyncpg
        storage3 = PostgresStorage(
            database_url="postgresql+asyncpg://localhost:5432/db"
        )
        assert storage3.database_url == "postgresql+asyncpg://localhost:5432/db"

    @pytest.mark.asyncio
    async def test_disconnect_when_not_connected(self):
        """Test disconnect when engine is None."""
        storage = PostgresStorage()
        # Should not raise error
        await storage.disconnect()
        assert storage._engine is None

    def test_serialize_empty_structures(self):
        """Test serialization of empty structures."""
        assert _serialize_for_jsonb({}) == {}
        assert _serialize_for_jsonb([]) == []
        assert _serialize_for_jsonb({"empty": []}) == {"empty": []}
