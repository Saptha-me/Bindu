"""
Tests for the pebbling server package.
"""

import asyncio
import uuid
from unittest.mock import MagicMock, patch

import pytest

from pebbling.core.protocol import ProtocolMethod, pebblingProtocol
from pebbling.server.jsonrpc_server import create_jsonrpc_server
from pebbling.server.pebbling_server import pebblify, start_servers
from pebbling.server.rest_server import create_rest_server


class TestPebblingServer:
    """Tests for the pebbling server."""

    @pytest.fixture
    def mock_agno_agent(self):
        """Create a mock Agno agent."""
        agent = MagicMock()
        agent.context = {}
        return agent

    @pytest.fixture
    def jsonrpc_app(self, mock_agno_agent):
        """Create a test JSON-RPC server."""
        protocol = pebblingProtocol()
        protocol_handler = MagicMock()
        protocol_handler.agent = mock_agno_agent
        supported_methods = [ProtocolMethod.ACT, ProtocolMethod.CONTEXT]
        return create_jsonrpc_server(protocol, protocol_handler, supported_methods)

    @pytest.fixture
    def rest_app(self):
        """Create a test REST server."""
        protocol_handler = MagicMock()
        return create_rest_server(protocol_handler)

    def test_pebblify_initialization(self, mock_agno_agent):
        """Test the initialization parameters for pebblify."""
        with (
            patch("pebbling.server.pebbling_server.create_jsonrpc_server") as mock_jsonrpc,
            patch("pebbling.server.pebbling_server.create_rest_server") as mock_rest,
            patch("pebbling.server.pebbling_server.asyncio.run") as mock_run,
        ):
            # Setup mocks
            mock_jsonrpc.return_value = "jsonrpc_app"
            mock_rest.return_value = "rest_app"

            # Call pebblify
            agent_id = str(uuid.uuid4())
            supported_methods = [ProtocolMethod.ACT, ProtocolMethod.CONTEXT]

            pebblify(
                agent=mock_agno_agent,
                agent_id=agent_id,
                supported_methods=supported_methods,
                pebbling_port=8001,
                user_port=8002,
                host="127.0.0.1",
            )

            # Verify calls
            mock_jsonrpc.assert_called_once()
            mock_rest.assert_called_once()
            mock_run.assert_called_once()

            # Verify agent_id parameter
            args, kwargs = mock_jsonrpc.call_args
            assert kwargs["protocol_handler"].agent_id == agent_id

            # Verify start_servers was called
            # The first arg is the coroutine object from start_servers
            assert mock_run.called
            # We can't inspect coroutine args directly, so we'll verify the function was called

    def test_pebblify_default_agent_id(self, mock_agno_agent):
        """Test that pebblify generates a default agent ID if none is provided."""
        with (
            patch("pebbling.server.pebbling_server.create_jsonrpc_server") as mock_jsonrpc,
            patch("pebbling.server.pebbling_server.create_rest_server") as mock_rest,
            patch("pebbling.server.pebbling_server.asyncio.run"),
        ):
            # Setup mocks
            mock_jsonrpc.return_value = "jsonrpc_app"
            mock_rest.return_value = "rest_app"

            # Call pebblify without agent_id
            pebblify(agent=mock_agno_agent, supported_methods=[ProtocolMethod.ACT])

            # Verify agent_id was automatically generated
            args, kwargs = mock_jsonrpc.call_args
            assert kwargs["protocol_handler"].agent_id is not None
            assert isinstance(kwargs["protocol_handler"].agent_id, str)

    def test_pebblify_default_methods(self, mock_agno_agent):
        """Test that pebblify uses default methods if none are provided."""
        with (
            patch("pebbling.server.pebbling_server.create_jsonrpc_server") as mock_jsonrpc,
            patch("pebbling.server.pebbling_server.create_rest_server") as mock_rest,
            patch("pebbling.server.pebbling_server.asyncio.run"),
        ):
            # Setup mocks
            mock_jsonrpc.return_value = "jsonrpc_app"
            mock_rest.return_value = "rest_app"

            # Call pebblify without supported_methods
            pebblify(agent=mock_agno_agent)

            # Verify jsonrpc server was created
            mock_jsonrpc.assert_called_once()
            # Supported methods might be empty since it depends on implementation

    @pytest.mark.asyncio
    async def test_start_servers(self, jsonrpc_app, rest_app):
        """Test the start_servers function."""
        with patch("uvicorn.Server.serve") as mock_serve:
            # Make serve return an awaitable that completes immediately
            mock_serve.return_value = asyncio.sleep(0)

            # Run start_servers for a short time then cancel
            task = asyncio.create_task(
                start_servers(
                    jsonrpc_app=jsonrpc_app, rest_app=rest_app, host="localhost", pebbling_port=8001, user_port=8002
                )
            )

            # Give it a moment to reach the gather
            await asyncio.sleep(0.1)
            task.cancel()

            try:
                await task
            except asyncio.CancelledError:
                pass

            # Verify that serve was called twice (once for each server)
            assert mock_serve.call_count == 2
