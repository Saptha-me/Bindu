"""Tests for mTLS security."""

import pytest
import os
from unittest.mock import MagicMock, patch
from pathlib import Path
import tempfile

from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

# Import the security modules assuming they've been added as discussed
from pebble.security.certificates import (
    generate_key_pair,
    generate_self_signed_cert,
    save_certificate,
    generate_agent_certificate
)

from pebble.security.mtls_client import SecureAgentClient


class TestCertificates:
    """Tests for certificate management."""
    
    def test_generate_key_pair(self):
        """Test key pair generation."""
        private_key = generate_key_pair()
        
        # Verify it's an RSA private key
        assert isinstance(private_key, rsa.RSAPrivateKey)
        
        # Get public key and verify
        public_key = private_key.public_key()
        assert isinstance(public_key, rsa.RSAPublicKey)
    
    def test_generate_self_signed_cert(self):
        """Test self-signed certificate generation."""
        # Generate a key pair
        private_key = generate_key_pair()
        
        # Generate certificate
        cert = generate_self_signed_cert(private_key, "test-agent")
        
        # Verify it's a certificate
        assert isinstance(cert, x509.Certificate)
        
        # Verify the subject CN contains the agent ID
        cn = cert.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)[0].value
        assert "test-agent" in cn
        
        # Verify the cert is valid (not expired)
        assert cert.not_valid_before < cert.not_valid_after
    
    def test_save_certificate(self, temp_dir):
        """Test saving certificate and key."""
        # Generate key and certificate
        private_key = generate_key_pair()
        cert = generate_self_signed_cert(private_key, "test-agent")
        
        # Save to temp directory
        cert_path, key_path = save_certificate(cert, private_key, "test-agent", temp_dir)
        
        # Verify files exist
        assert os.path.exists(cert_path)
        assert os.path.exists(key_path)
        
        # Verify content is correct
        with open(cert_path, "rb") as f:
            cert_data = f.read()
            assert b"BEGIN CERTIFICATE" in cert_data
        
        with open(key_path, "rb") as f:
            key_data = f.read()
            assert b"BEGIN PRIVATE KEY" in key_data
    
    def test_generate_agent_certificate(self, temp_dir):
        """Test end-to-end certificate generation."""
        # Generate certificate
        cert_path, key_path = generate_agent_certificate("test-agent", temp_dir)
        
        # Verify files exist
        assert os.path.exists(cert_path)
        assert os.path.exists(key_path)
        
        # Verify correct filenames
        assert cert_path.name == "test-agent.crt"
        assert key_path.name == "test-agent.key"


class TestSecureClient:
    """Tests for the secure client."""
    
    def test_secure_client_init(self, temp_dir):
        """Test secure client initialization."""
        # Generate certificate for testing
        cert_path, key_path = generate_agent_certificate("test-client", temp_dir)
        
        # Create client
        client = SecureAgentClient("test-client", cert_path, key_path)
        
        # Verify client has correct properties
        assert client.agent_id == "test-client"
        assert client.cert_path == cert_path
        assert client.key_path == key_path
        assert client.verify is True  # Default
        
        # Verify httpx client was created
        assert hasattr(client, "client")
    
    def test_secure_client_request(self, temp_dir):
        """Test secure client request method."""
        with patch("httpx.Client") as mock_client_class:
            # Setup mock
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"success": True}
            mock_client.request.return_value = mock_response
            
            # Generate certificate for testing
            cert_path, key_path = generate_agent_certificate("test-client", temp_dir)
            
            # Create client
            client = SecureAgentClient("test-client", cert_path, key_path)
            
            # Make request
            response = client.request(
                method="POST",
                url="https://example.com/api",
                json={"data": "test"},
                headers={"Custom": "Header"}
            )
            
            # Verify response
            assert response == mock_response
            
            # Verify request was made with correct parameters
            mock_client.request.assert_called_once()
            args, kwargs = mock_client.request.call_args
            assert kwargs["method"] == "POST"
            assert kwargs["url"] == "https://example.com/api"
            assert kwargs["json"] == {"data": "test"}
            assert "headers" in kwargs
            assert kwargs["headers"]["Custom"] == "Header"
            assert kwargs["headers"]["X-Pebble-Agent-ID"] == "test-client"