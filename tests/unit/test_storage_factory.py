"""Unit tests for storage factory."""

import pytest
from unittest.mock import AsyncMock, patch

from bindu.server.storage.factory import create_storage, close_storage
from bindu.server.storage.memory_storage import InMemoryStorage
from bindu.settings import app_settings


class TestStorageFactory:
    """Test storage factory functions."""

    @pytest.mark.asyncio
    async def test_create_memory_storage(self):
        """Test creating memory storage."""
        with patch.object(app_settings.storage, "backend", "memory"):
            storage = await create_storage()
            assert isinstance(storage, InMemoryStorage)

    @pytest.mark.asyncio
    async def test_create_postgres_storage(self):
        """Test creating PostgreSQL storage."""
        with (
            patch.object(app_settings.storage, "backend", "postgres"),
            patch.object(
                app_settings.storage,
                "postgres_url",
                "postgresql+asyncpg://test:test@localhost:5432/test",  # pragma: allowlist secret
            ),
            patch("bindu.server.storage.factory.PostgresStorage") as mock_postgres,
        ):
            mock_instance = AsyncMock()
            mock_postgres.return_value = mock_instance

            _storage = await create_storage()

            mock_postgres.assert_called_once()
            mock_instance.connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_storage_invalid_backend(self):
        """Test that invalid backend raises ValueError."""
        with patch.object(app_settings.storage, "backend", "invalid"):
            with pytest.raises(ValueError, match="Unknown storage backend"):
                await create_storage()

    @pytest.mark.asyncio
    async def test_close_memory_storage(self):
        """Test closing memory storage (no-op)."""
        storage = InMemoryStorage()
        # Should not raise an error
        await close_storage(storage)

    @pytest.mark.asyncio
    async def test_close_postgres_storage(self):
        """Test closing PostgreSQL storage."""
        with patch(
            "bindu.server.storage.factory.PostgresStorage", create=True
        ) as mock_postgres_class:
            # Create a mock instance that will pass isinstance check
            mock_storage = AsyncMock()
            mock_storage.disconnect = AsyncMock()
            mock_postgres_class.return_value = mock_storage

            # Make isinstance return True for our mock
            with patch("bindu.server.storage.factory.isinstance", return_value=True):
                await close_storage(mock_storage)

            mock_storage.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_storage_with_error(self):
        """Test that close_storage handles errors gracefully."""
        mock_storage = AsyncMock()
        mock_storage.close = AsyncMock(side_effect=Exception("Close failed"))

        # Should not raise an error
        await close_storage(mock_storage)
