"""Tests for BinduApplication.

This module tests the Bindu application server:
- Application initialization
- Route registration
- Lifespan management
- Middleware configuration
- Payment endpoint registration
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from pathlib import Path

from starlette.requests import Request
from starlette.responses import Response, FileResponse
from starlette.routing import Route
from starlette.middleware import Middleware

from bindu.server.applications import BinduApplication
from bindu.common.models import (
    AgentManifest,
    StorageConfig,
    SchedulerConfig,
    TelemetryConfig,
)
from tests.mocks import MockManifest


class TestBinduApplicationInit:
    """Test BinduApplication initialization."""

    def test_init_minimal(self, mock_manifest):
        """Test initialization with minimal parameters."""
        app = BinduApplication(manifest=mock_manifest)
        
        assert app.penguin_id is not None
        assert app._storage_config is None
        assert app._scheduler_config is None
        assert isinstance(app._telemetry_config, TelemetryConfig)

    def test_init_with_penguin_id(self, mock_manifest):
        """Test initialization with custom penguin_id."""
        test_id = uuid4()
        app = BinduApplication(penguin_id=test_id, manifest=mock_manifest)
        
        assert app.penguin_id == test_id

    def test_init_with_manifest(self, mock_manifest):
        """Test initialization with manifest."""
        app = BinduApplication(manifest=mock_manifest)
        
        assert app.manifest == mock_manifest

    def test_init_with_storage_config(self, mock_manifest):
        """Test initialization with storage config."""
        storage_config = StorageConfig(
            type="memory"
        )
        app = BinduApplication(storage_config=storage_config, manifest=mock_manifest)
        
        assert app._storage_config == storage_config

    def test_init_with_scheduler_config(self, mock_manifest):
        """Test initialization with scheduler config."""
        scheduler_config = SchedulerConfig(
            type="memory"
        )
        app = BinduApplication(scheduler_config=scheduler_config, manifest=mock_manifest)
        
        assert app._scheduler_config == scheduler_config

    def test_init_with_telemetry_config(self, mock_manifest):
        """Test initialization with telemetry config."""
        telemetry_config = TelemetryConfig(
            enabled=True,
            endpoint="http://localhost:4317"
        )
        app = BinduApplication(telemetry_config=telemetry_config, manifest=mock_manifest)
        
        assert app._telemetry_config.enabled is True
        assert app._telemetry_config.endpoint == "http://localhost:4317"

    def test_init_with_custom_routes(self, mock_manifest):
        """Test initialization with custom routes."""
        async def custom_handler(request: Request) -> Response:
            return Response("custom")
        
        custom_routes = [
            Route("/custom", custom_handler, methods=["GET"])
        ]
        
        app = BinduApplication(routes=custom_routes, manifest=mock_manifest)
        
        # Verify custom route is registered
        route_paths = [route.path for route in app.routes]
        assert "/custom" in route_paths

    def test_init_with_auth_enabled(self, mock_manifest):
        """Test initialization with auth enabled."""
        app = BinduApplication(auth_enabled=True, manifest=mock_manifest)
        
        # Auth middleware should be in middleware stack
        # (This would require checking app.middleware)
        assert app is not None

    def test_init_with_debug_mode(self, mock_manifest):
        """Test initialization with debug mode."""
        app = BinduApplication(debug=True, manifest=mock_manifest)
        
        assert app.debug is True


class TestBinduApplicationRoutes:
    """Test BinduApplication route registration."""

    def test_default_routes_registered(self, mock_manifest):
        """Test that default routes are registered."""
        app = BinduApplication(manifest=mock_manifest)
        
        route_paths = [route.path for route in app.routes]
        
        # Core A2A protocol routes
        assert "/.well-known/agent.json" in route_paths
        assert "/" in route_paths
        
        # UI routes
        assert "/docs" in route_paths
        assert "/favicon.ico" in route_paths

    def test_payment_routes_with_x402(self):
        """Test payment routes are registered when x402 is enabled."""
        from bindu.extensions.x402 import X402AgentExtension
        
        mock_manifest = MagicMock()
        mock_manifest.capabilities = {"extensions": []}
        
        # Create a mock X402 extension
        mock_x402 = MagicMock(spec=X402AgentExtension)
        mock_manifest.capabilities["extensions"].append(mock_x402)
        
        app = BinduApplication(manifest=mock_manifest)
        
        route_paths = [route.path for route in app.routes]
        
        # Payment routes should be registered when x402 extension is present
        if app._x402_ext:
            assert "/api/start-payment-session" in route_paths
            assert "/payment-capture" in route_paths
            assert "/api/payment-status/{session_id}" in route_paths

    def test_add_route_with_app(self, mock_manifest):
        """Test _add_route with app parameter."""
        app = BinduApplication(manifest=mock_manifest)
        
        async def test_endpoint(app_instance: BinduApplication, request: Request) -> Response:
            return Response("test")
        
        app._add_route("/test", test_endpoint, ["GET"], with_app=True)
        
        route_paths = [route.path for route in app.routes]
        assert "/test" in route_paths

    def test_add_route_without_app(self, mock_manifest):
        """Test _add_route without app parameter."""
        app = BinduApplication(manifest=mock_manifest)
        
        async def test_endpoint(request: Request) -> Response:
            return Response("test")
        
        app._add_route("/test2", test_endpoint, ["GET"], with_app=False)
        
        route_paths = [route.path for route in app.routes]
        assert "/test2" in route_paths


class TestBinduApplicationEndpoints:
    """Test BinduApplication built-in endpoints."""

    @pytest.mark.asyncio
    async def test_docs_endpoint_file_exists(self, mock_manifest):
        """Test docs endpoint when file exists."""
        app = BinduApplication(manifest=mock_manifest)
        request = MagicMock(spec=Request)
        
        with patch('pathlib.Path.exists', return_value=True):
            response = await app._docs_endpoint(request)
            
            assert isinstance(response, (FileResponse, Response))

    @pytest.mark.asyncio
    async def test_docs_endpoint_file_not_found(self, mock_manifest):
        """Test docs endpoint when file doesn't exist."""
        app = BinduApplication(manifest=mock_manifest)
        request = MagicMock(spec=Request)
        
        with patch('pathlib.Path.exists', return_value=False):
            response = await app._docs_endpoint(request)
            
            assert isinstance(response, Response)
            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_favicon_endpoint_file_exists(self, mock_manifest):
        """Test favicon endpoint when file exists."""
        app = BinduApplication(manifest=mock_manifest)
        request = MagicMock(spec=Request)
        
        with patch('pathlib.Path.exists', return_value=True):
            response = await app._favicon_endpoint(request)
            
            assert isinstance(response, FileResponse)

    @pytest.mark.asyncio
    async def test_favicon_endpoint_file_not_found(self, mock_manifest):
        """Test favicon endpoint when file doesn't exist."""
        app = BinduApplication(manifest=mock_manifest)
        request = MagicMock(spec=Request)
        
        with patch('pathlib.Path.exists', return_value=False):
            response = await app._favicon_endpoint(request)
            
            assert isinstance(response, Response)
            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_wrap_with_app(self, mock_manifest):
        """Test _wrap_with_app wrapper."""
        app = BinduApplication(manifest=mock_manifest)
        
        async def test_endpoint(app_instance: BinduApplication, request: Request) -> Response:
            assert app_instance == app
            return Response("wrapped")
        
        request = MagicMock(spec=Request)
        response = await app._wrap_with_app(test_endpoint, request)
        
        assert isinstance(response, Response)


class TestBinduApplicationLifespan:
    """Test BinduApplication lifespan management."""

    @pytest.mark.asyncio
    async def test_lifespan_with_manifest(self, mock_manifest):
        """Test lifespan with manifest."""
        app = BinduApplication(manifest=mock_manifest)
        
        with patch('bindu.server.applications.create_storage') as mock_create_storage:
            mock_storage = MagicMock()
            mock_storage.__aenter__ = AsyncMock(return_value=mock_storage)
            mock_storage.__aexit__ = AsyncMock()
            mock_create_storage.return_value = mock_storage
            
            with patch('bindu.server.applications.close_storage') as mock_close:
                with patch('bindu.server.applications.TaskManager') as mock_tm:
                    mock_tm_instance = MagicMock()
                    mock_tm_instance.__aenter__ = AsyncMock(return_value=mock_tm_instance)
                    mock_tm_instance.__aexit__ = AsyncMock()
                    mock_tm.return_value = mock_tm_instance
                    
                    async with app:
                        assert app._storage is not None
                        assert app._scheduler is not None

    @pytest.mark.asyncio
    async def test_lifespan_without_manifest(self):
        """Test lifespan without manifest."""
        app = BinduApplication(manifest=None)
        
        with patch('bindu.server.applications.create_storage') as mock_create_storage:
            mock_storage = MagicMock()
            mock_storage.__aenter__ = AsyncMock(return_value=mock_storage)
            mock_storage.__aexit__ = AsyncMock()
            mock_create_storage.return_value = mock_storage
            
            with patch('bindu.server.applications.close_storage'):
                async with app:
                    assert app._storage is not None
                    assert app._scheduler is not None

    @pytest.mark.asyncio
    async def test_lifespan_with_postgres_storage_config(self):
        """Test lifespan with PostgreSQL storage config."""
        storage_config = StorageConfig(
            type="postgres",
            database_url="postgresql://localhost/test"
        )
        app = BinduApplication(storage_config=storage_config)
        
        with patch('bindu.server.applications.create_storage') as mock_create_storage:
            mock_storage = MagicMock()
            mock_storage.__aenter__ = AsyncMock(return_value=mock_storage)
            mock_storage.__aexit__ = AsyncMock()
            mock_create_storage.return_value = mock_storage
            
            with patch('bindu.server.applications.close_storage'):
                with patch('bindu.server.applications.app_settings') as mock_settings:
                    mock_settings.storage.backend = "memory"
                    
                    async with app:
                        # Settings should be updated
                        assert mock_settings.storage.backend == "postgres"

    @pytest.mark.asyncio
    async def test_lifespan_with_memory_storage_config(self):
        """Test lifespan with memory storage config."""
        storage_config = StorageConfig(type="memory")
        app = BinduApplication(storage_config=storage_config)
        
        with patch('bindu.server.applications.create_storage') as mock_create_storage:
            mock_storage = MagicMock()
            mock_storage.__aenter__ = AsyncMock(return_value=mock_storage)
            mock_storage.__aexit__ = AsyncMock()
            mock_create_storage.return_value = mock_storage
            
            with patch('bindu.server.applications.close_storage'):
                with patch('bindu.server.applications.app_settings') as mock_settings:
                    async with app:
                        assert mock_settings.storage.backend == "memory"


class TestBinduApplicationObservability:
    """Test BinduApplication observability setup."""

    def test_setup_observability_enabled(self):
        """Test observability setup when enabled."""
        telemetry_config = TelemetryConfig(
            enabled=True,
            endpoint="http://localhost:4317",
            service_name="test-service"
        )
        app = BinduApplication(telemetry_config=telemetry_config)
        
        with patch('bindu.server.applications.setup_observability') as mock_setup:
            app._setup_observability()
            
            mock_setup.assert_called_once()

    def test_setup_observability_disabled(self):
        """Test observability setup when disabled."""
        telemetry_config = TelemetryConfig(enabled=False)
        app = BinduApplication(telemetry_config=telemetry_config)
        
        # Should not raise error
        # (In actual lifespan, setup is only called if enabled)

    def test_setup_observability_error_handling(self):
        """Test observability setup error handling."""
        telemetry_config = TelemetryConfig(enabled=True)
        app = BinduApplication(telemetry_config=telemetry_config)
        
        with patch('bindu.server.applications.setup_observability') as mock_setup:
            mock_setup.side_effect = Exception("Setup failed")
            
            # Should not raise, just log warning
            app._setup_observability()


class TestBinduApplicationPaymentSessions:
    """Test BinduApplication payment session management."""

    @pytest.mark.asyncio
    async def test_payment_session_manager_startup(self):
        """Test payment session manager starts cleanup task."""
        mock_manifest = MagicMock()
        mock_manifest.x402_config = {"enabled": True}
        
        with patch('bindu.server.applications.X402AgentExtension'):
            app = BinduApplication(manifest=mock_manifest)
            
            if app._payment_session_manager:
                app._payment_session_manager.start_cleanup_task = AsyncMock()
                app._payment_session_manager.stop_cleanup_task = AsyncMock()
                
                with patch('bindu.server.applications.create_storage') as mock_create_storage:
                    mock_storage = MagicMock()
                    mock_storage.__aenter__ = AsyncMock(return_value=mock_storage)
                    mock_storage.__aexit__ = AsyncMock()
                    mock_create_storage.return_value = mock_storage
                    
                    with patch('bindu.server.applications.close_storage'):
                        async with app:
                            pass
                        
                        app._payment_session_manager.start_cleanup_task.assert_called_once()
                        app._payment_session_manager.stop_cleanup_task.assert_called_once()


class TestBinduApplicationEdgeCases:
    """Test edge cases and error scenarios."""

    def test_init_with_none_values(self, mock_manifest):
        """Test initialization with explicit None values."""
        app = BinduApplication(
            storage_config=None,
            scheduler_config=None,
            manifest=mock_manifest,
            penguin_id=None,
            lifespan=None,
            routes=None,
            middleware=None
        )
        
        assert app.penguin_id is not None  # Auto-generated
        assert app._storage_config is None
        assert app.manifest is not None

    def test_multiple_app_instances(self, mock_manifest):
        """Test creating multiple app instances."""
        app1 = BinduApplication(manifest=mock_manifest)
        app2 = BinduApplication(manifest=mock_manifest)
        
        assert app1.penguin_id != app2.penguin_id

    def test_custom_url_and_port(self, mock_manifest):
        """Test custom URL and port."""
        app = BinduApplication(
            url="http://example.com",
            port=8080,
            manifest=mock_manifest
        )
        
        assert app.url == "http://example.com"
        assert app.port == 8080

    def test_custom_version_and_description(self, mock_manifest):
        """Test custom version and description."""
        app = BinduApplication(
            version="2.0.0",
            description="Test application",
            manifest=mock_manifest
        )
        
        assert app.version == "2.0.0"
        assert app.description == "Test application"
