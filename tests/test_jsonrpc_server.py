"""
Tests for the JSON-RPC server.
"""
import json
import pytest
from fastapi.testclient import TestClient

from pebble.server.jsonrpc_server import create_jsonrpc_server


class TestJsonRpcServer:
    """Tests for the JSON-RPC server."""
    
    @pytest.fixture
    def client(self, protocol, mock_protocol_handler):
        """Create a test client for the JSON-RPC server."""
        app = create_jsonrpc_server(
            protocol=protocol,
            protocol_handler=mock_protocol_handler,
            supported_methods=["Context"]
        )
        return TestClient(app)
    
    async def test_valid_request(self, client, sample_jsonrpc_request):
        """Test handling a valid JSON-RPC request."""
        response = client.post("/", json=sample_jsonrpc_request)
        assert response.status_code == 200
        data = response.json()
        assert data["jsonrpc"] == "2.0"
        assert data["id"] == sample_jsonrpc_request["id"]
        assert "result" in data
        assert data["result"]["status"] == "success"
    
    async def test_invalid_jsonrpc_version(self, client, sample_jsonrpc_request):
        """Test handling an invalid JSON-RPC version."""
        sample_jsonrpc_request["jsonrpc"] = "1.0"
        response = client.post("/", json=sample_jsonrpc_request)
        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == -32600
    
    async def test_unsupported_method(self, client, sample_jsonrpc_request):
        """Test handling an unsupported method."""
        sample_jsonrpc_request["method"] = "UnsupportedMethod"
        response = client.post("/", json=sample_jsonrpc_request)
        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == -32601
    
    async def test_invalid_json(self, client):
        """Test handling invalid JSON."""
        response = client.post("/", data="invalid JSON")
        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == -32700