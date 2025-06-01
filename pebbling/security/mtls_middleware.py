"""mTLS middleware for secure agent-to-agent communication."""

import json
import logging
import os
import ssl
import tempfile
from typing import Dict, Optional, Any, Tuple

from pebbling.security.cert_manager import CertificateManager
from pebbling.security.did_manager import DIDManager

logger = logging.getLogger(__name__)


class MTLSMiddleware:
    """Middleware for handling mTLS secure connections between agents.
    
    This middleware builds on top of the DID-based security system to provide 
    fully encrypted and authenticated connections between agents.
    """

    def __init__(
        self,
        did_manager: DIDManager,
        cert_manager: Optional[CertificateManager] = None,
        cert_path: Optional[str] = None,
        verify_mode: int = ssl.CERT_REQUIRED,
    ):
        """Initialize the mTLS middleware.
        
        Args:
            did_manager: DID manager for the agent
            cert_manager: Optional certificate manager (will create one if not provided)
            cert_path: Path to store certificates (if cert_manager not provided)
            verify_mode: SSL verification mode
        """
        self.did_manager = did_manager
        
        if cert_manager is None:
            self.cert_manager = CertificateManager(
                did_manager=did_manager,
                cert_path=cert_path
            )
        else:
            self.cert_manager = cert_manager
            
        self.verify_mode = verify_mode
        
        # Map from agent IDs to their certificate info
        self.peer_certs: Dict[str, Dict[str, Any]] = {}
        
    def get_server_ssl_context(self) -> ssl.SSLContext:
        """Create an SSL context for the server side.
        
        Returns:
            Configured SSL context object
        """
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        
        # Set verification mode
        context.verify_mode = self.verify_mode
        
        # Load certificates
        server_context = self.cert_manager.get_server_context()
        context.load_cert_chain(
            certfile=server_context["certfile"],
            keyfile=server_context["keyfile"]
        )
        
        # Load CA certificates for peer verification
        context.load_verify_locations(cafile=server_context["ca_certs"])
        
        # Load peer certificates if they exist
        peer_cert_dir = os.path.join(self.cert_manager.cert_path, "peers")
        if os.path.isdir(peer_cert_dir):
            for cert_file in os.listdir(peer_cert_dir):
                if cert_file.endswith(".crt"):
                    context.load_verify_locations(
                        cafile=os.path.join(peer_cert_dir, cert_file)
                    )
        
        # TLS settings for security
        context.options |= (
            ssl.OP_NO_SSLv2 | 
            ssl.OP_NO_SSLv3 | 
            ssl.OP_NO_TLSv1 
            #ssl.OP_NO_TLSv1_1
        )
        
        # Use strong ciphers
        context.set_ciphers("ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384")

        # Uvicorn checks for these specific attributes on the SSL context object
        context.certfile = server_context["certfile"]
        context.keyfile = server_context["keyfile"]
        context.ca_certs = server_context["ca_certs"]
        
        return context
        
    def get_client_ssl_context(self) -> ssl.SSLContext:
        """Create an SSL context for the client side.
        
        Returns:
            Configured SSL context object
        """
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        
        # Set verification mode
        context.verify_mode = self.verify_mode
        
        # Load certificates
        client_context = self.cert_manager.get_client_context()
        context.load_cert_chain(
            certfile=client_context["certfile"],
            keyfile=client_context["keyfile"]
        )
        
        # Load CA certificates for server verification
        context.load_verify_locations(cafile=client_context["ca_certs"])
        
        # Load peer certificates if they exist
        peer_cert_dir = os.path.join(self.cert_manager.cert_path, "peers")
        if os.path.isdir(peer_cert_dir):
            for cert_file in os.listdir(peer_cert_dir):
                if cert_file.endswith(".crt"):
                    context.load_verify_locations(
                        cafile=os.path.join(peer_cert_dir, cert_file)
                    )
        
        # TLS settings for security
        context.options |= (
            ssl.OP_NO_SSLv2 | 
            ssl.OP_NO_SSLv3 | 
            ssl.OP_NO_TLSv1  
            #ssl.OP_NO_TLSv1_1
        )
        
        # Use strong ciphers
        context.set_ciphers("ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384")

        # Uvicorn checks for these specific attributes on the SSL context object
        context.certfile = client_context["certfile"]
        context.keyfile = client_context["keyfile"]
        context.ca_certs = client_context["ca_certs"]
        
        return context

    def is_connection_verified(self, agent_id: str) -> bool:
        """Check if an agent has completed the mTLS verification process."""
        if agent_id not in self.peer_certs:
            return False
    
        return agent_id in getattr(self, "verified_connections", set())
    
    async def handle_exchange_certificates(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle certificate exchange request.
        
        Args:
            params: Request parameters containing agent ID and certificates
            
        Returns:
            Response with this agent's certificates
        """
        # Extract sender information
        sender_id = params.get("source_agent_id")
        sender_server_cert = params.get("server_cert")
        sender_ca_cert = params.get("ca_cert")
        
        if not sender_id or not sender_server_cert or not sender_ca_cert:
            return {
                "status": "error",
                "message": "Missing source_agent_id, server_cert, or ca_cert in request"
            }
        
        # Register the peer's certificates
        try:
            # Save CA cert
            self.cert_manager.register_peer_certificate(
                agent_id=f"{sender_id}_ca",
                cert_pem=sender_ca_cert
            )
            
            # Save server cert
            self.cert_manager.register_peer_certificate(
                agent_id=sender_id,
                cert_pem=sender_server_cert
            )
            
            logger.info(f"Registered certificates for agent {sender_id}")
            
            # Cache the peer's certificate info
            self.peer_certs[sender_id] = {
                "server_cert": sender_server_cert,
                "ca_cert": sender_ca_cert
            }
            
            # Return this agent's certificates
            cert_info = self.cert_manager.get_certificate_info()
            return {
                "status": "success",
                "agent_id": cert_info["agent_id"],
                "did": cert_info["did"],
                "server_cert": cert_info["server_cert"],
                "ca_cert": cert_info["ca_cert"]
            }
            
        except Exception as e:
            logger.error(f"Error registering certificates: {e}")
            return {
                "status": "error",
                "message": f"Error registering certificates: {str(e)}"
            }
            
    async def handle_verify_connection(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle connection verification request.
        
        This method can be used to test mTLS connections between agents.
        
        Args:
            params: Request parameters
            
        Returns:
            Response with connection status
        """
        sender_id = params.get("source_agent_id")
        
        if not sender_id:
            return {
                "status": "error",
                "message": "Missing source_agent_id in request"
            }
        
        # Check if we have the sender's certificates
        if sender_id not in self.peer_certs:
            return {
                "status": "error",
                "message": f"No certificates registered for agent {sender_id}"
            }

        if not hasattr(self, "verified_connections"):
            self.verified_connections = set()
        
        self.verified_connections.add(sender_id)
            
        return {
            "status": "success",
            "message": f"Secure mTLS connection verified with agent {sender_id}",
            "did": self.did_manager.get_did()
        }
        
    def get_peer_connection_info(self, peer_id: str) -> Optional[Dict[str, Any]]:
        """Get connection information for a peer agent.
        
        Args:
            peer_id: ID of the peer agent
            
        Returns:
            Dictionary with connection information or None if peer not found
        """
        if peer_id not in self.peer_certs:
            return None
            
        # Create temporary files for certificates
        with tempfile.NamedTemporaryFile(delete=False) as ca_file:
            ca_file.write(self.peer_certs[peer_id]["ca_cert"].encode('utf-8'))
            ca_path = ca_file.name
            
        with tempfile.NamedTemporaryFile(delete=False) as cert_file:
            cert_file.write(self.peer_certs[peer_id]["server_cert"].encode('utf-8'))
            cert_path = cert_file.name
            
        return {
            "agent_id": peer_id,
            "ca_path": ca_path,
            "cert_path": cert_path
        }
    
    def cleanup_temporary_files(self, connection_info: Dict[str, Any]) -> None:
        """Clean up temporary certificate files.
        
        Args:
            connection_info: Connection information from get_peer_connection_info
        """
        try:
            if "ca_path" in connection_info and os.path.exists(connection_info["ca_path"]):
                os.unlink(connection_info["ca_path"])
                
            if "cert_path" in connection_info and os.path.exists(connection_info["cert_path"]):
                os.unlink(connection_info["cert_path"])
        except Exception as e:
            logger.error(f"Error cleaning up temporary files: {e}")
    
    def get_mtls_connection_params(self) -> Dict[str, Any]:
        """Get mTLS connection parameters for setting up secure servers.
        
        Returns:
            Dictionary with SSL context and other parameters
        """
        server_context = self.cert_manager.get_server_context()
        
        return {
            "ssl_keyfile": server_context["keyfile"],
            "ssl_certfile": server_context["certfile"],
            "ssl_ca_certs": server_context["ca_certs"],
            "ssl_cert_reqs": self.verify_mode,
            "ssl_context": self.get_server_ssl_context()
        }
