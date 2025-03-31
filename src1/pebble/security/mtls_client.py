# src/pebble/security/mtls_client.py
"""mTLS client for secure agent-to-agent communication."""

import os
from pathlib import Path
from typing import Optional, Dict, Any, Union
import httpx
import logging

logger = logging.getLogger("pebble.security")

class SecureAgentClient:
    """HTTP client with mTLS for secure agent-to-agent communication."""
    
    def __init__(
        self,
        agent_id: str,
        cert_path: Optional[Union[str, Path]] = None,
        key_path: Optional[Union[str, Path]] = None,
        ca_bundle_path: Optional[Union[str, Path]] = None,
        verify: bool = True,
    ):
        """Initialize secure client with mTLS certificates.
        
        Args:
            agent_id: The ID of the agent this client belongs to
            cert_path: Path to the client certificate
            key_path: Path to the client private key
            ca_bundle_path: Path to the CA bundle for verifying server certificates
            verify: Whether to verify server certificates
        """
        self.agent_id = agent_id
        
        # Default certificate paths if not provided
        if cert_path is None or key_path is None:
            certs_dir = Path.home() / ".pebble" / "certs"
            if cert_path is None:
                cert_path = certs_dir / f"{agent_id}.crt"
            if key_path is None:
                key_path = certs_dir / f"{agent_id}.key"
        
        self.cert_path = Path(cert_path)
        self.key_path = Path(key_path)
        
        # Verify the certificate and key exist
        if not self.cert_path.exists():
            raise FileNotFoundError(f"Certificate not found: {self.cert_path}")
        if not self.key_path.exists():
            raise FileNotFoundError(f"Private key not found: {self.key_path}")
        
        # CA bundle for verifying server certificates
        self.ca_bundle_path = ca_bundle_path
        self.verify = verify
        
        # Create the HTTP client with mTLS
        self.client = self._create_client()
    
    def _create_client(self) -> httpx.Client:
        """Create an HTTP client with mTLS configuration."""
        # Determine verification settings
        if self.verify and self.ca_bundle_path:
            verify = self.ca_bundle_path
        else:
            verify = self.verify
        
        # Create client with cert, key, and verification settings
        return httpx.Client(
            cert=(str(self.cert_path), str(self.key_path)),
            verify=verify,
            timeout=60.0
        )
    
    def request(
        self,
        method: str,
        url: str,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> httpx.Response:
        """Make a secure request to another agent."""
        # Add agent ID to headers
        if headers is None:
            headers = {}
        headers["X-Pebble-Agent-ID"] = self.agent_id
        
        logger.debug(f"Making secure request to {url}")
        return self.client.request(
            method=method,
            url=url,
            json=json,
            headers=headers,
        )
    
    def __del__(self):
        """Close the client when garbage collected."""
        if hasattr(self, "client"):
            self.client.close()