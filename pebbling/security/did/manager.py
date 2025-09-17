#
# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/Pebbling-ai/pebble/issues/new/choose |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🐧

"""DID (Decentralized Identifier) management functionality for Pebbling.

This module implements the DIDManager class which provides comprehensive
capabilities for DID creation, storage, verification, and challenge-response
authentication for agents in the Pebbling framework.
"""

import os
from typing import Any, Dict, Tuple

import orjson

from pebbling.security.common.keys import load_public_key
from pebbling.security.did.document import create_did_document, update_service_endpoint


class DIDManager:
    """DID manager for pebbling agents."""

    @staticmethod
    def get_or_create_did(
        agent_id: str, config_path: str, pki_dir: str, recreate: bool = False
    ) -> Tuple[str, Dict[str, Any]]:
        """Get or create a DID for the agent.

        Args:

            config_path: Path to the DID configuration file
            pki_dir: Directory containing the key files
            recreate: Whether to recreate the DID if it exists

        Returns:
            Tuple of (did, did_document)
        """
        # Check if the DID configuration file already exists
        if os.path.exists(config_path) and not recreate:
            try:
                with open(config_path, "rb") as f:
                    config_data = orjson.loads(f.read())
                    did = config_data["did"]
                    did_document = config_data["didDocument"]
                    return did, did_document
            except Exception:
                # If there's an error reading the file, we'll create a new DID
                pass

        # Make sure the keys directory exists
        os.makedirs(os.path.dirname(config_path), exist_ok=True)

        # Generate keys if needed
        public_key_pem = load_public_key(pki_dir)

        # Create a new DID
        did = f"did:pebble:{agent_id}"

        # Create a DID document
        did_document = create_did_document(
            did=did,
            public_key_pem=public_key_pem,
        )

        # Save the DID configuration
        with open(config_path, "wb") as f:
            f.write(orjson.dumps({"did": did, "didDocument": did_document}))

        return did, did_document

    def __init__(self, agent_id: str, config_path="did.json", pki_dir="keys", endpoint=None, recreate: bool = False):
        """Initialize the DID manager.

        Args:
            agent_id: The agent ID to use for the DID
            config_path: Path to the DID configuration file
            pki_dir: Directory containing the key files
            endpoint: Optional service endpoint to update in the DID document
            recreate: Whether to recreate the key file if it exists
            capabilities: Optional capabilities to include in the DID document
            skills: Optional skills to include in the DID document
        """
        self.agent_id = agent_id
        self.config_path = config_path
        self.did, self.did_document = self.get_or_create_did(
            agent_id=agent_id, config_path=config_path, pki_dir=pki_dir, recreate=recreate
        )

        # Update service endpoint if provided
        if endpoint:
            self.update_service_endpoint(endpoint)

    def update_service_endpoint(self, endpoint):
        """Update the service endpoint in the DID document.

        Args:
            endpoint: The new service endpoint
        """
        self.did_document = update_service_endpoint(self.did_document, endpoint)

    def get_did(self) -> str:
        """Get the DID of the agent.

        Returns:
            The DID as a string
        """
        return self.did

    def get_did_document(self) -> Dict[str, Any]:
        """Get the DID document of the agent.

        Returns:
            The DID document as a dictionary
        """
        return self.did_document
