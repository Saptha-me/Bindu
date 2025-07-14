"""
SSL context management for mTLS.

This module handles creating and managing SSL contexts for mTLS connections.
"""

import os
import ssl
import logging
from typing import Dict, Any, Optional

from pebbling.security.mtls.utils import create_ssl_context
from pebbling.security.mtls.exceptions import SSLContextError

logger = logging.getLogger(__name__)


class SSLContextManager:
    """Manages SSL contexts for mTLS connections.
    
    This class handles:
    1. Creating SSL contexts for server and client connections
    2. Managing certificate and key paths
    """
    
    def __init__(
        self,
        cert_path: str,
        key_path: str,
        ca_cert_path: str
    ):
        """Initialize the SSL context manager.
        
        Args:
            cert_path: Path to the certificate file
            key_path: Path to the private key file
            ca_cert_path: Path to the CA certificate file
        """
        self.cert_path = cert_path
        self.key_path = key_path
        self.ca_cert_path = ca_cert_path
            
    def create_ssl_context(self, server_side: bool = False) -> ssl.SSLContext:
        """Create an SSL context for mTLS connections.
        
        Args:
            server_side: Whether this is for a server (True) or client (False)
            
        Returns:
            SSL context configured for mTLS
            
        Raises:
            SSLContextError: If creating the context fails
        """
        try:
            # Ensure we have all required files
            for path, description in [
                (self.cert_path, "certificate"),
                (self.key_path, "private key"),
                (self.ca_cert_path, "CA certificate")
            ]:
                if not os.path.exists(path):
                    raise SSLContextError(f"Missing {description} file: {path}")
            
            # Create context
            context = create_ssl_context(
                self.cert_path,
                self.key_path,
                self.ca_cert_path,
                server_side=server_side
            )
            
            return context
            
        except Exception as e:
            if not isinstance(e, SSLContextError):
                error_msg = f"Failed to create SSL context: {str(e)}"
                logger.error(error_msg)
                raise SSLContextError(error_msg) from e
            raise
