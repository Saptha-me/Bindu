# 
# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/Pebbling-ai/pebble/issues/new/choose |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🐧

"""Security setup utilities for the Pebbling framework.

This module provides functionality for setting up security features
including DID (Decentralized Identifier) configuration and key management
for Pebbling agents.
"""

import inspect
import os

from pebbling.protocol.types import AgentIdentity, AgentManifest, AgentSecurity
from pebbling.security.common.keys import generate_key_pair, load_public_key, generate_csr

# Import necessary components
from pebbling.security.did.manager import DIDManager

# Import logging from pebbling utils
from pebbling.utils.logging import get_logger

logger = get_logger("pebbling.security.setup_security")

def setup_security(
    agent_manifest: AgentManifest,
    keys_dir: str,
    did_required: bool = False,
    keys_required: bool = False,
    recreate_keys: bool = False,
    create_csr: bool = False
) -> AgentManifest:
    """Set up security features for an agent.
    
    Configures cryptographic keys and DID (Decentralized Identifier) for an agent,
    updating its manifest with the necessary security information.
    
    Args:
        agent_manifest: The agent manifest to update with security information
        keys_dir: Directory to store cryptographic keys
        did_required: Whether a DID is required for the agent
        keys_required: Whether keys are required for the agent
        recreate_keys: Whether to recreate keys if they already exist
        create_csr: Whether to create a CSR for the agent
        
    Returns:
        Updated agent manifest with security information
    """
    # Access the keys_dir from the outer scope
    current_keys_dir = keys_dir
    
    # Set up keys directory if needed
    if not current_keys_dir:
        # Create keys directory relative to the calling script
        caller_file = inspect.getframeinfo(inspect.currentframe().f_back).filename
        caller_dir = os.path.dirname(os.path.abspath(caller_file))
        current_keys_dir = os.path.join(caller_dir, 'keys')
        os.makedirs(current_keys_dir, exist_ok=True)
        logger.debug(f"Created keys directory: {current_keys_dir}")
        
    # Generate keys if needed
    if keys_required:
        logger.info(f"Generating key pair in {current_keys_dir}")
        generate_key_pair(current_keys_dir, recreate=recreate_keys)
    
    # Set up DID if required
    if did_required:
        if not current_keys_dir:
            logger.error("Keys directory not set but required for DID functionality")
            raise ValueError("Keys are required for DID functionality")
        
        logger.info("Initializing DID Manager")
        did_config_path = os.path.join(current_keys_dir, "did.json")
        did_manager = DIDManager(
            config_path=did_config_path,
            keys_dir=current_keys_dir,
            capabilities=agent_manifest.capabilities,
            skills=agent_manifest.skills,
            recreate=recreate_keys
        )
        
        # Set the DID and DID document in the agent manifest
        # This directly follows the memory about enhancing AgentManifest with DID-related fields
        agent_manifest.did = did_manager.get_did()
        agent_manifest.did_document = did_manager.get_did_document()
        
        # Set up the agent identity
        agent_manifest.identity = AgentIdentity(
            did=did_manager.get_did(),
            did_document=did_manager.get_did_document(),
            public_key=load_public_key(current_keys_dir)
        )

    # Create CSR if requested and set up security configuration
    if create_csr:
        logger.info("Creating CSR for agent")
        generate_csr(
            keys_dir=current_keys_dir, 
            agent_id=agent_manifest.id
        )
        logger.debug(f"CSR created at {csr_path}")
        cert_type = "sheldon"
        cert_path = os.path.join(current_keys_dir, "agent.cert")  # Using standard name for consistency
    else:
        cert_type = None
        cert_path = None
    
    # Set up security configuration aligned with DID-based security architecture
    agent_manifest.security = AgentSecurity(
        challenge_expiration_seconds=300,
        require_challenge_response=False,  # Default to False, can be enabled when needed
        signature_algorithm="Ed25519",     # Using Ed25519 which is optimal for DIDs
        key_storage_path=current_keys_dir,
        endpoint_type="json-rpc",          # For Docker/Fly.io deployed JSON-RPC servers
        verify_requests=True,
        certificate_type=cert_type,
        certificate_path=cert_path,
        max_retries=3,
        allow_anonymous=False
    )

    return agent_manifest