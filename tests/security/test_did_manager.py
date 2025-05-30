import pytest
import os
import json
import tempfile
import asyncio
from unittest.mock import patch

from pebbling.security.did_manager import DIDManager

# Fixture for a temporary key file
@pytest.fixture
def temp_key_file():
    fd, path = tempfile.mkstemp()
    yield path
    os.close(fd)
    if os.path.exists(path):
        os.unlink(path)

# Fixture for a DIDManager instance
@pytest.fixture
async def did_manager(temp_key_file):
    manager = DIDManager(key_path=temp_key_file)
    return manager

@pytest.mark.asyncio
async def test_create_new_did(temp_key_file):
    """Test creating a new DID when key file doesn't exist."""
    # Ensure the file doesn't exist
    if os.path.exists(temp_key_file):
        os.unlink(temp_key_file)
        
    # Create a new DID manager
    manager = DIDManager(key_path=temp_key_file)
    
    # Check that DID was generated and file was created
    assert manager.get_did().startswith("did:pebble:")
    assert os.path.exists(temp_key_file)
    
    # Verify the file structure
    with open(temp_key_file, "r") as f:
        data = json.load(f)
        
    assert "did" in data
    assert "privateKeyBase58" in data
    assert "didDocument" in data
    
    # Check DID document structure
    did_document = data["didDocument"]
    assert did_document["id"] == data["did"]
    assert "verificationMethod" in did_document
    assert "authentication" in did_document
    assert "service" in did_document

@pytest.mark.asyncio
async def test_load_existing_did(temp_key_file):
    """Test loading an existing DID from key file."""
    # First create a DID
    original_manager = DIDManager(key_path=temp_key_file)
    original_did = original_manager.get_did()
    
    # Create a new manager with the same file
    new_manager = DIDManager(key_path=temp_key_file)
    
    # Check that the DID is the same
    assert new_manager.get_did() == original_did
    assert new_manager.get_did_document() == original_manager.get_did_document()

@pytest.mark.asyncio
async def test_sign_and_verify(did_manager):
    """Test signing and verifying messages."""
    # Message to sign
    message = {"test": "message", "value": 123}
    
    # Sign message
    signature = await did_manager.sign_message(message)
    
    # Verify the message with the same manager
    verification_method = f"{did_manager.get_did()}#keys-1"
    is_valid = await did_manager.verify_message(message, signature, verification_method)
    
    assert is_valid

@pytest.mark.asyncio
async def test_sign_and_verify_modified_message(did_manager):
    """Test that verification fails if the message is modified."""
    # Original message
    message = {"test": "message", "value": 123}
    
    # Sign message
    signature = await did_manager.sign_message(message)
    
    # Modified message
    modified_message = message.copy()
    modified_message["value"] = 456
    
    # Verify should fail with modified message
    verification_method = f"{did_manager.get_did()}#keys-1"
    is_valid = await did_manager.verify_message(modified_message, signature, verification_method)
    
    assert not is_valid

@pytest.mark.asyncio
async def test_update_service_endpoint(did_manager):
    """Test updating the service endpoint."""
    # Original endpoint
    original_endpoint = None
    for service in did_manager.get_did_document()["service"]:
        if service["type"] == "PebbleAgentCard":
            original_endpoint = service["serviceEndpoint"]
            break
            
    # Update the endpoint
    new_endpoint = "https://example.com/agent"
    did_manager.update_service_endpoint(new_endpoint)
    
    # Check the endpoint was updated
    updated_endpoint = None
    for service in did_manager.get_did_document()["service"]:
        if service["type"] == "PebbleAgentCard":
            updated_endpoint = service["serviceEndpoint"]
            break
            
    assert updated_endpoint == new_endpoint
    assert updated_endpoint != original_endpoint

@pytest.mark.asyncio
async def test_export_did_document(did_manager, temp_key_file):
    """Test exporting the DID document."""
    # Export the DID document to a string
    did_doc_str = did_manager.export_did_document()
    did_doc = json.loads(did_doc_str)
    
    # Check the structure
    assert did_doc["id"] == did_manager.get_did()
    
    # Export to a file
    export_path = f"{temp_key_file}_export"
    did_manager.export_did_document(export_path)
    
    # Verify file was created
    assert os.path.exists(export_path)
    
    # Clean up
    os.unlink(export_path)
