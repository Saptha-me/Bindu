# 
# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/Pebbling-ai/pebble/issues/new/choose |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🐧

"""🔐 Security Fortress: Zero-Trust Agent Identity & Authentication

Transform your agents from vulnerable processes into cryptographically secured entities
with just one function call. This module orchestrates a symphony of security technologies:

🌊 Like pebbles creating ripples across a digital pond, each agent generates its own
   unique identity that reverberates through the entire network, establishing trust
   through mathematical certainty rather than blind faith.

🚀 Features:
   • DID-Based Identity: Each agent becomes a sovereign digital citizen
   • JWT Powerhouse: MCP servers get instant bearer token authentication  
   • Auto-Magic Setup: One call configures everything (keys, certs, tokens)
   • Framework Agnostic: Works with any agent architecture
   • Production Ready: Fly.io, Docker, localhost - deploy anywhere

💡 Example - From Zero to Secure in Seconds:
   ```python
   # For MCP servers (fastmcp compatible)
   security = create_security_config(
       server_type="mcp",
       agent_id="weather_oracle",
       jwt_expiry_hours=48
   )
   # Now your agent has: JWT tokens, DID identity, crypto keys, certificates
   # Ready for: fastmcp.Client(auth=security.jwt_token) 🎯
   
   # For agent-to-agent networks
   security = create_security_config(
       server_type="agent", 
       did_required=True,
       agent_id="social_coordinator"
   )
   # Now your agents can verify each other's identity cryptographically 🤝
   ```

🎭 Philosophy: Security shouldn't be an afterthought or a complexity burden.
   It should be as natural as breathing - invisible when working, impenetrable when needed.
"""

import inspect
import os
import uuid
from typing import Dict, Any

from pebbling.security.common.keys import generate_key_pair, generate_csr, generate_jwt_token
from pebbling.common.models.models import SecurityCredentials
from pebbling.security.did.manager import DIDManager
from pebbling.utils.constants import PKI_DIR

from pebbling.utils.logging import get_logger

logger = get_logger("pebbling.security.setup_security")


def create_security_config(
    server_type: str = "agent",
    pki_dir: str = None,
    agent_id: str = None,
    # Security features
    did_required: bool = False,
    keys_required: bool = True,
    jwt_required: bool = True,  # Auto-detect based on server_type
    # Key management
    recreate_keys: bool = False,
    create_csr: bool = True,
    # JWT configuration
    jwt_payload: Dict[str, Any] = None,
    jwt_expiry_hours: int = 24
) -> SecurityCredentials:
    """Optimized security setup for both agent servers and MCP servers.
    
    Args:
        server_type: Type of server ("agent" or "mcp")
        pki_dir: Directory for cryptographic keys (auto-created if None)
        agent_id: Agent identifier (required for CSR and JWT)
        did_required: Enable DID-based identity (for agent-to-agent communication)
        keys_required: Generate cryptographic key pairs
        jwt_required: Generate JWT tokens (auto-enabled for MCP servers)
        recreate_keys: Force regeneration of existing keys
        create_csr: Generate Certificate Signing Request
        jwt_payload: Custom payload for JWT token
        jwt_expiry_hours: JWT token expiry time in hours
        
    Returns:
        SecurityCredentials with all necessary security information
    """
    # Auto-configure based on server type
    if jwt_required is None:
        jwt_required = (server_type == "mcp")
    
    # Set up keys directory
    if pki_dir:
        caller_file = inspect.getframeinfo(inspect.currentframe().f_back).filename
        caller_dir = os.path.dirname(os.path.abspath(caller_file))
        pki_dir = os.path.join(caller_dir, PKI_DIR)
        os.makedirs(pki_dir, exist_ok=True)
        logger.debug(f"Auto-created keys directory: {pki_dir}")
    
    if not agent_id:
        agent_id = uuid.uuid4().hex
    
    credentials = SecurityCredentials(
        pki_dir=pki_dir,
        server_type=server_type,
        agent_id=agent_id
    )
    
    # Generate cryptographic keys
    if keys_required:
        logger.info(f"Setting up cryptographic keys for {server_type} server")
        credentials.key_paths = generate_key_pair(
            pki_dir, recreate=recreate_keys
        )
    
    # Set up DID identity (primarily for agent servers)
    if did_required:
        if not credentials.key_paths:
            raise ValueError("Keys are required for DID functionality")
        
        logger.info("Setting up DID identity")
        did_config_path = os.path.join(pki_dir, "did.json")
        credentials.did_document = DIDManager(
            agent_id=agent_id,
            config_path=did_config_path,
            pki_dir=pki_dir,
            recreate=recreate_keys
        ).get_did_document()
    
    # Generate Certificate Signing Request
    if create_csr:
        if not agent_id:
            raise ValueError("agent_id is required for CSR generation")
        logger.info("Generating Certificate Signing Request")
        credentials.csr_path = generate_csr(pki_dir=pki_dir, agent_id=agent_id)
    
    # Generate JWT tokens (primarily for MCP servers)
    if jwt_required:
        if not agent_id:
            raise ValueError("agent_id is required for JWT token generation")
        
        logger.info(f"Generating JWT tokens for {server_type} server")
        
        # Generate JWT secret
        import secrets
        credentials.jwt_secret = secrets.token_urlsafe(32)
        
        # Default JWT payload
        default_payload = {
            'sub': agent_id,
            'server_type': server_type,
            'scope': 'mcp:access' if server_type == 'mcp' else 'agent:access'
        }
        
        # Merge with custom payload
        if jwt_payload:
            default_payload.update(jwt_payload)
        
        # Generate JWT token
        credentials.jwt_token = generate_jwt_token(
            payload=default_payload,
            secret=credentials.jwt_secret,
            expiry_hours=jwt_expiry_hours
        )
        
        # For MCP servers, also generate a simple access token
        if server_type == "mcp":
            credentials.access_token = f"mcp_{secrets.token_urlsafe(24)}"
        
        logger.debug(f"JWT token generated with {jwt_expiry_hours}h expiry")
    
    logger.info(f"Security setup complete for {server_type} server")
    return credentials