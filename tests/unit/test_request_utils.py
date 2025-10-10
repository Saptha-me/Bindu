"""Unit tests for request utilities."""

from unittest.mock import Mock

from bindu.utils.request_utils import (
    get_client_ip,
    jsonrpc_error,
)


class TestGetClientIP:
    """Test get_client_ip function."""

    def test_get_client_ip_with_client(self):
        """Test getting client IP when client is available."""
        request = Mock()
        request.client = Mock()
        request.client.host = "192.168.1.1"
        
        ip = get_client_ip(request)
        assert ip == "192.168.1.1"

    def test_get_client_ip_without_client(self):
        """Test getting client IP when client is None."""
        request = Mock()
        request.client = None
        
        ip = get_client_ip(request)
        assert ip == "unknown"


class TestJsonRpcError:
    """Test jsonrpc_error function."""

    def test_basic_error(self):
        """Test creating basic JSON-RPC error."""
        response = jsonrpc_error(code=-32600, message="Invalid Request")
        
        assert response.status_code == 400
        content = response.body.decode()
        assert "-32600" in content
        assert "Invalid Request" in content

    def test_error_with_data(self):
        """Test creating error with additional data."""
        response = jsonrpc_error(
            code=-32602,
            message="Invalid params",
            data="Missing required field",
        )
        
        content = response.body.decode()
        assert "Missing required field" in content

    def test_error_with_request_id(self):
        """Test creating error with request ID."""
        response = jsonrpc_error(
            code=-32601,
            message="Method not found",
            request_id="123",
        )
        
        content = response.body.decode()
        assert '"id":"123"' in content or '"id": "123"' in content

    def test_error_with_custom_status(self):
        """Test creating error with custom HTTP status."""
        response = jsonrpc_error(
            code=-32000,
            message="Server error",
            status=500,
        )
        
        assert response.status_code == 500

    def test_error_response_format(self):
        """Test that error response has correct JSON-RPC format."""
        response = jsonrpc_error(code=-32600, message="Invalid Request")
        
        content = response.body.decode()
        assert '"jsonrpc"' in content and '"2.0"' in content
        assert '"error"' in content
        assert '"code"' in content
        assert '"message"' in content
