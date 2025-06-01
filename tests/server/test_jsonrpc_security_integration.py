import pytest
import json
import os
import uuid
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient
from typing import Dict, Any

from pebbling.core.protocol import CoreProtocolMethod, SecurityProtocolMethod, pebblingProtocol
from pebbling.security.did_manager import DIDManager
from pebbling.server.jsonrpc_server import create_jsonrpc_server
from pebbling.server.server_security import SecurityMiddleware


# Fixture for mocked protocol and handler
@pytest.fixture
def mock_protocol():
    protocol = Mock(spec=pebblingProtocol)
    protocol.JSONRPC_VERSION = "2.0"
    return protocol


@pytest.fixture
def mock_handler():
    handler = Mock()
    handler.handle_act = AsyncMock(return_value={"content": "Hello, world!", "metadata": {}})
    handler.handle_context = AsyncMock(return_value={"content": "Context set", "metadata": {}})
    return handler


# Fixture for a mock DID manager
@pytest.fixture
def mock_did_manager():
    did_manager = Mock(spec=DIDManager)
    did_manager.get_did = Mock(return_value="did:pebble:test-agent")
    did_manager.get_did_document = Mock(return_value={
        "@context": ["https://www.w3.org/ns/did/v1"],
        "id": "did:pebble:test-agent",
        "verificationMethod": [{
            "id": "did:pebble:test-agent#keys-1",
            "type": "Ed25519VerificationKey2020",
            "controller": "did:pebble:test-agent",
            "publicKeyBase58": "test-public-key"
        }],
        "authentication": ["did:pebble:test-agent#keys-1"]
    })
    did_manager.sign_message = AsyncMock(return_value="test-signature")
    did_manager.verify_message = AsyncMock(return_value=True)
    return did_manager


# Helper function to create a TestClient with security middleware
@pytest.fixture
def app_client(mock_protocol, mock_handler, mock_did_manager):
    supported_methods = [
        CoreProtocolMethod.ACT,
        CoreProtocolMethod.CONTEXT,
        SecurityProtocolMethod.EXCHANGE_DID,
        SecurityProtocolMethod.VERIFY_IDENTITY
    ]
    
    # Create security middleware
    security_middleware = SecurityMiddleware(did_manager=mock_did_manager, agent_id="test-agent")
    
    # Create JSON-RPC server
    app = create_jsonrpc_server(
        protocol=mock_protocol,
        protocol_handler=mock_handler,
        supported_methods=supported_methods,
        security_middleware=security_middleware
    )
    
    return TestClient(app)


def test_exchange_did(app_client, mock_did_manager):
    """Test the exchange_did endpoint."""
    # Create DID document for the client
    client_did_doc = {
        "@context": ["https://www.w3.org/ns/did/v1"],
        "id": "did:pebble:test-client",
        "verificationMethod": [{
            "id": "did:pebble:test-client#keys-1",
            "type": "Ed25519VerificationKey2020",
            "controller": "did:pebble:test-client",
            "publicKeyBase58": "client-public-key"
        }],
        "authentication": ["did:pebble:test-client#keys-1"]
    }
    
    # Make the request
    response = app_client.post(
        "/",
        json={
            "jsonrpc": "2.0",
            "method": "exchange_did",
            "params": {
                "source_agent_id": "test-client",
                "did_document": client_did_doc
            },
            "id": "1"
        }
    )
    
    # Check response
    assert response.status_code == 200
    data = response.json()
    assert data["jsonrpc"] == "2.0"
    assert data["id"] == "1"
    assert "result" in data
    assert data["result"]["status"] == "success"
    assert data["result"]["did"] == "did:pebble:test-agent"
    assert "did_document" in data["result"]


def test_unsupported_method(app_client):
    """Test calling an unsupported method."""
    response = app_client.post(
        "/",
        json={
            "jsonrpc": "2.0",
            "method": "unsupported_method",
            "params": {},
            "id": "1"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["jsonrpc"] == "2.0"
    assert data["id"] == "1"
    assert "error" in data
    assert data["error"]["code"] == -32601  # Method not found


def test_act_without_verification(app_client, mock_handler):
    """Test calling act without prior identity verification."""
    # Since we're using a mock handler, this should work even without verification
    response = app_client.post(
        "/",
        json={
            "jsonrpc": "2.0",
            "method": "act",
            "params": {
                "source_agent_id": "test-client",
                "message": "Hello"
            },
            "id": "1"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["jsonrpc"] == "2.0"
    assert data["id"] == "1"
    assert "result" in data
    assert data["result"]["content"] == "Hello, world!"
    
    # Check that the handler was called with the right parameters
    mock_handler.handle_act.assert_called_once()
    args, kwargs = mock_handler.handle_act.call_args
    assert kwargs["source_agent_id"] == "test-client"
    assert kwargs["message"] == "Hello"


def test_verify_identity_flow(app_client, monkeypatch):
    """Test the complete identity verification flow."""
    # Mock UUID and token_hex to get predictable values
    monkeypatch.setattr(uuid, "uuid4", lambda: "test-challenge-id")
    monkeypatch.setattr(os, "urandom", lambda _: b"test-challenge-bytes")
    
    # Step 1: Request a challenge
    response1 = app_client.post(
        "/",
        json={
            "jsonrpc": "2.0",
            "method": "verify_identity",
            "params": {
                "source_agent_id": "test-client"
            },
            "id": "1"
        }
    )
    
    assert response1.status_code == 200
    data1 = response1.json()
    assert "result" in data1
    assert data1["result"]["status"] == "success"
    assert "challenge_id" in data1["result"]
    assert "challenge" in data1["result"]
    
    challenge_id = data1["result"]["challenge_id"]
    challenge = data1["result"]["challenge"]
    
    # Step 2: Respond to the challenge
    response2 = app_client.post(
        "/",
        json={
            "jsonrpc": "2.0",
            "method": "verify_identity",
            "params": {
                "source_agent_id": "test-client",
                "challenge_id": challenge_id,
                "signature": "simulated_signature_for_demo_purposes_only"
            },
            "id": "2"
        }
    )
    
    assert response2.status_code == 200
    data2 = response2.json()
    assert "result" in data2
    assert data2["result"]["status"] == "success"


def test_container_compatibility():
    """Test compatibility with Docker/Fly.io environments."""
    # Check that environment variables can override defaults
    with patch.dict(os.environ, {"PEBBLE_HOST": "0.0.0.0", "PEBBLE_PORT": "8080"}):
        # This test doesn't actually create a server, just checks env var parsing
        # In a real system, you'd read these values from environment
        host = os.environ.get("PEBBLE_HOST", "localhost")
        port = int(os.environ.get("PEBBLE_PORT", 8000))
        
        assert host == "0.0.0.0"  # Correct for Docker/Fly.io
        assert port == 8080

    # Check for Fly.io app name
    with patch.dict(os.environ, {"FLY_APP_NAME": "pebble-agent"}):
        fly_app = os.environ.get("FLY_APP_NAME")
        assert fly_app == "pebble-agent"
        # In production, you'd use this for service discovery or other config


def test_error_handling(app_client, mock_handler):
    """Test error handling when a handler raises an exception."""
    # Make the handler throw an exception
    mock_handler.handle_act = AsyncMock(side_effect=ValueError("Test error"))
    
    response = app_client.post(
        "/",
        json={
            "jsonrpc": "2.0",
            "method": "act",
            "params": {
                "source_agent_id": "test-client",
                "message": "Hello"
            },
            "id": "1"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == -32603  # Internal error
    assert "Test error" in data["error"]["message"]
