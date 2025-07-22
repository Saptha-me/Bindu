# 
# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/Pebbling-ai/pebble/issues/new/choose |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - Raahul

import inspect
import os

from pebbling.protocol.types import AgentIdentity, AgentManifest
from pebbling.security.common.keys import generate_key_pair, load_public_key

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
) -> AgentManifest:
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

    return agent_manifest