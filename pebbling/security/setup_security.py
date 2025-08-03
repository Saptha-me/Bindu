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

"""

import inspect
import os
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

from pebbling.protocol.types import AgentSecurity, AgentIdentity
from pebbling.security.common.keys import generate_csr, generate_key_pair
from pebbling.security.did.manager import DIDManager
from pebbling.common.models.models import SecuritySetupResult
from pebbling.utils.constants import (
    CHALLENGE_EXPIRATION_SECONDS, 
    DEFAULT_KEY_ALGORITHM,
    ENDPOINT_TYPE_JSON_RPC,
    CERTIFICATE_AUTHORITY,
    PRIVATE_KEY_FILENAME,
    PUBLIC_KEY_FILENAME
)

from pebbling.utils.logging import get_logger

logger = get_logger("pebbling.security.setup_security")


def create_security_config(
    id: str,
    did_required: bool = False,
    recreate_keys: bool = False,
    require_challenge_response: bool = False,
    verify_requests: bool = False,
    allow_anonymous: bool = False,
    create_csr: bool = False,
    pki_dir: Optional[Path] = None,
    cert_dir: Optional[Path] = None,
) -> SecuritySetupResult:
    """Optimized security setup for both agent servers and MCP servers.
    
    Args:
        id: Agent ID (required, must be valid string)
        did_required: Enable DID-based identity (for agent-to-agent communication)
        recreate_keys: Force regeneration of existing keys
        require_challenge_response: Require challenge-response verification for agent communication
        verify_requests: Whether to verify incoming requests
        allow_anonymous: Whether to allow anonymous access
        create_csr: Whether to generate Certificate Signing Request
        pki_dir: Directory for cryptographic keys
        cert_dir: Directory for certificates
        
    Returns:
        Tuple of AgentSecurity and AgentIdentity with all necessary security information
        
    Raises:
        ValueError: If id is empty, None, or contains invalid characters
        OSError: If directory creation fails
        RuntimeError: If key generation or DID setup fails
    """
    
    # Input validation
    if not id or not isinstance(id, str) or not id.strip():
        raise ValueError("Agent ID must be a non-empty string")
    
    # Sanitize agent ID - remove invalid characters for filesystem
    sanitized_id = "".join(c for c in id if c.isalnum() or c in "-_").strip()
    if not sanitized_id:
        raise ValueError(f"Agent ID '{id}' contains only invalid characters")
    
    logger.info(f"Setting up security for agent: {sanitized_id}")
    
    try:        
        # Create directories with proper error handling
        _ensure_directories_exist(pki_dir, cert_dir)
        
        # Handle key generation/recreation
        if recreate_keys or not _keys_exist(pki_dir):
            logger.info(f"{'Recreating' if recreate_keys else 'Generating'} cryptographic keys")
            try:
                generate_key_pair(
                    pki_dir=str(pki_dir),
                    key_type=DEFAULT_KEY_ALGORITHM,
                    recreate=recreate_keys
                )
            except Exception as e:
                logger.error(f"Failed to generate key pair: {e}")
                raise RuntimeError(f"Key generation failed: {e}") from e
        else:
            logger.debug("Using existing cryptographic keys")
        
        # Create security configuration
        security_config = AgentSecurity(
            challenge_expiration_seconds=CHALLENGE_EXPIRATION_SECONDS,
            require_challenge_response=require_challenge_response,
            signature_algorithm=DEFAULT_KEY_ALGORITHM,
            pki_dir=str(pki_dir),
            endpoint_type=ENDPOINT_TYPE_JSON_RPC,
            verify_requests=verify_requests,
            cert_dir=str(cert_dir),
            certificate_authority=CERTIFICATE_AUTHORITY,
            allow_anonymous=allow_anonymous,
            did_required=did_required,
            recreate_keys=recreate_keys
        )
        
        # Initialize identity
        identity = AgentIdentity()
        
        # Set up DID identity if required
        if did_required:
            try:
                identity = _setup_did_identity(sanitized_id, pki_dir, recreate_keys)
            except Exception as e:
                logger.error(f"Failed to setup DID identity: {e}")
                raise RuntimeError(f"DID setup failed: {e}") from e
        
        # Generate Certificate Signing Request if requested
        if create_csr:
            try:
                logger.info("Generating Certificate Signing Request")
                csr_content = generate_csr(pki_dir=str(pki_dir), agent_id=sanitized_id)
                identity.csr = csr_content
            except Exception as e:
                logger.error(f"Failed to generate CSR: {e}")
                raise RuntimeError(f"CSR generation failed: {e}") from e
        
        logger.info(f"Security setup complete for agent: {sanitized_id}")
        return SecuritySetupResult(security_config, identity)
        
    except Exception as e:
        logger.error(f"Security setup failed for agent {sanitized_id}: {e}")
        raise RuntimeError(f"Security setup failed for agent {sanitized_id}: {e}") from e


def _ensure_directories_exist(pki_path: Path, cert_path: Path) -> None:
    """Ensure required directories exist with proper error handling."""
    for path_obj in [pki_path, cert_path]:
        try:
            if not path_obj.exists():
                path_obj.mkdir(parents=True, exist_ok=True)
                logger.debug(f"Created directory: {path_obj}")
            else:
                logger.debug(f"Using existing directory: {path_obj}")
                
            # Verify directory is writable
            if not os.access(str(path_obj), os.W_OK):
                raise OSError(f"Directory {path_obj} is not writable")
                
        except OSError as e:
            logger.error(f"Failed to create/access directory {path_obj}: {e}")
            raise OSError(f"Directory setup failed for {path_obj}: {e}") from e


def _keys_exist(pki_path: Path) -> bool:
    """Check if cryptographic keys already exist."""
    private_key_path = pki_path / PRIVATE_KEY_FILENAME
    public_key_path = pki_path / PUBLIC_KEY_FILENAME
    
    exists = private_key_path.exists() and public_key_path.exists()
    logger.debug(f"Keys exist check: {exists} (private: {private_key_path.exists()}, public: {public_key_path.exists()})")
    return exists


def _setup_did_identity(agent_id: str, pki_path: Path, recreate: bool) -> AgentIdentity:
    """Set up DID identity with proper error handling."""
    logger.info("Setting up DID identity")
    
    identity = AgentIdentity()
    did_config_path = pki_path / "did.json"
    
    try:
        did_manager = DIDManager(
            agent_id=agent_id,
            config_path=str(did_config_path),
            pki_dir=str(pki_path),
            recreate=recreate
        )
        
        identity.did = did_manager.get_did()
        identity.did_document = did_manager.get_did_document()
        
        if not identity.did:
            raise ValueError("DID generation returned empty result")
            
        logger.debug(f"DID identity created: {identity.did}")
        return identity
        
    except Exception as e:
        logger.error(f"DID identity setup failed: {e}")
        raise RuntimeError(f"Failed to setup DID identity: {e}") from e