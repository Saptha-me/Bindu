import pytest
import asyncio
import json
import secrets
import uuid
from unittest.mock import Mock, AsyncMock, patch

from pebbling.security.did_manager import DIDManager
from pebbling.server.server_security import SecurityMiddleware


# Fixture for a mocked DID manager
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
        "authentication": ["did:pebble:test-agent#keys-1"],
        "service": [{
            "id": "did:pebble:test-agent#agent",
            "type": "PebbleAgentCard",
            "serviceEndpoint": "http://localhost:8000"
        }]
    })
    did_manager.sign_message = AsyncMock(return_value="test-signature")
    did_manager.verify_message = AsyncMock(return_value=True)
    return did_manager


# Fixture for a security middleware instance
@pytest.fixture
def security_middleware(mock_did_manager):
    return SecurityMiddleware(did_manager=mock_did_manager, agent_id="test-agent")


@pytest.mark.asyncio
async def test_exchange_did(security_middleware):
    """Test DID exchange request."""
    # Prepare a request
    sender_did_document = {
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
    
    request_params = {
        "source_agent_id": "test-client",
        "did_document": sender_did_document
    }
    
    # Call exchange_did
    result = await security_middleware.handle_exchange_did(request_params)
    
    # Check results
    assert result["status"] == "success"
    assert result["agent_id"] == "test-agent"
    assert result["did"] == "did:pebble:test-agent"
    assert "did_document" in result
    
    # Check that the client's DID was registered
    assert "test-client" in security_middleware.agent_did_documents
    assert security_middleware.agent_did_documents["test-client"] == sender_did_document


@pytest.mark.asyncio
async def test_exchange_did_missing_params(security_middleware):
    """Test DID exchange with missing parameters."""
    # Missing source_agent_id
    result1 = await security_middleware.handle_exchange_did({
        "did_document": {}
    })
    assert result1["status"] == "error"
    
    # Missing did_document
    result2 = await security_middleware.handle_exchange_did({
        "source_agent_id": "test-client"
    })
    assert result2["status"] == "error"


@pytest.mark.asyncio
async def test_verify_identity_request_challenge(security_middleware, monkeypatch):
    """Test requesting a challenge for identity verification."""
    # Mock UUID and secrets for predictable results
    mock_uuid = "test-challenge-id"
    mock_challenge = "test-challenge-value"
    
    monkeypatch.setattr(uuid, "uuid4", lambda: mock_uuid)
    monkeypatch.setattr(secrets, "token_hex", lambda _: mock_challenge)
    
    # Request a challenge
    result = await security_middleware.handle_verify_identity({
        "source_agent_id": "test-client"
    })
    
    # Check results
    assert result["status"] == "success"
    assert result["challenge_id"] == mock_uuid
    assert result["challenge"] == mock_challenge
    assert result["signature"] == "test-signature"
    assert result["verification_method"] == "did:pebble:test-agent#keys-1"
    
    # Check the challenge was stored
    assert mock_uuid in security_middleware.challenges
    assert security_middleware.challenges[mock_uuid]["agent_id"] == "test-client"
    assert security_middleware.challenges[mock_uuid]["challenge"] == mock_challenge


@pytest.mark.asyncio
async def test_verify_identity_respond_to_challenge(security_middleware):
    """Test responding to a challenge for identity verification."""
    # Store a challenge first
    challenge_id = "test-challenge-id"
    security_middleware.challenges[challenge_id] = {
        "agent_id": "test-client",
        "challenge": "test-challenge-value",
        "timestamp": asyncio.get_event_loop().time()
    }
    
    # Respond to the challenge with test signature
    result = await security_middleware.handle_verify_identity({
        "source_agent_id": "test-client",
        "challenge_id": challenge_id,
        "signature": "simulated_signature_for_demo_purposes_only"
    })
    
    # Check results
    assert result["status"] == "success"
    assert "test mode" in result["message"]
    
    # Challenge should be removed after verification
    assert challenge_id not in security_middleware.challenges


@pytest.mark.asyncio
async def test_verify_identity_expired_challenge(security_middleware):
    """Test handling an expired challenge."""
    # First register the agent's DID
    await security_middleware.register_agent_did("test-client", {
        "id": "did:pebble:test-client",
        "verificationMethod": [{
            "id": "did:pebble:test-client#keys-1",
            "type": "Ed25519VerificationKey2020",
            "controller": "did:pebble:test-client",
            "publicKeyBase58": "client-public-key"
        }]
    })
    
    # Store an expired challenge
    import datetime
    challenge_id = "test-expired-challenge"
    security_middleware.challenges[challenge_id] = {
        "agent_id": "test-client",
        "challenge": "test-challenge-value",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).timestamp() - 700  # 700s old (> 600s limit)
    }
    
    # Respond to the challenge
    result = await security_middleware.handle_verify_identity({
        "source_agent_id": "test-client",
        "challenge_id": challenge_id,
        "signature": "test-signature"
    })
    
    # Check results
    assert result["status"] == "error"
    assert "expired" in result["message"]
    
    # Challenge should be removed
    assert challenge_id not in security_middleware.challenges


@pytest.mark.asyncio
async def test_secure_request_handler(security_middleware):
    """Test the secure_request_handler method."""
    # Test dispatching to exchange_did
    exchange_request = {
        "method": "exchange_did",
        "params": {
            "source_agent_id": "test-client",
            "did_document": {"id": "did:pebble:test-client"}
        }
    }
    
    with patch.object(security_middleware, "handle_exchange_did", AsyncMock()) as mock_exchange:
        mock_exchange.return_value = {"status": "success"}
        result = await security_middleware.secure_request_handler(exchange_request, None)
        
        # Check the handler was called with correct parameters
        mock_exchange.assert_called_once_with(exchange_request["params"])
        assert result == {"status": "success"}
    
    # Test dispatching to verify_identity
    verify_request = {
        "method": "verify_identity",
        "params": {
            "source_agent_id": "test-client"
        }
    }
    
    with patch.object(security_middleware, "handle_verify_identity", AsyncMock()) as mock_verify:
        mock_verify.return_value = {"status": "success"}
        result = await security_middleware.secure_request_handler(verify_request, None)
        
        # Check the handler was called with correct parameters
        mock_verify.assert_called_once_with(verify_request["params"])
        assert result == {"status": "success"}
    
    # Test using a handler function for other methods
    other_request = {
        "method": "act",
        "params": {"message": "hello"}
    }
    
    handler_func = AsyncMock(return_value={"content": "response"})
    result = await security_middleware.secure_request_handler(other_request, handler_func)
    
    # Check the handler function was called
    handler_func.assert_called_once()
    assert result == {"content": "response"}
    
    # Test missing handler function
    result = await security_middleware.secure_request_handler(other_request, None)
    assert result["status"] == "error"
    assert "No handler function provided" in result["message"]
