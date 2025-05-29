import didkit
import json
import os
import asyncio


class DIDManager:
    """DID Manager class for managing DIDs."""
    async def get_or_create_did(self, key_path="pebble_private_key.json"):
        """Get existing DID or create a new one."""
        # Load or generate private key
        if os.path.exists(key_path):
            with open(key_path, "r") as file:
                private_key = file.read().strip()
        else:
            private_key = didkit.generate_ed25519_key()
            with open(key_path, "w") as file:
                file.write(private_key)
    
        # Get DID from key
        did = didkit.key_to_did("key", private_key)
    
        # Create DID document
        did_document = {
            "@context": ["https://www.w3.org/ns/did/v1"],
            "id": did,
            "verificationMethod": [{
                "id": f"{did}#keys-1",
                "type": "Ed25519VerificationKey2018",
                "controller": did,
                "publicKeyBase58": await didkit.key_to_verification_method("key", private_key)
            }],
            "authentication": [f"{did}#keys-1"],
            "service": [{
                "id": f"{did}#agent-card",
                "type": "PebbleAgentCard",
                "serviceEndpoint": "https://example.com/agent-card"
            }]
        }
    
        return private_key, did, did_document

    def __init__(self, key_path="pebble_private_key.json"):
        self.key_path = key_path
        self.private_key, self.did, self.did_document = asyncio.run(self.get_or_create_did(key_path))

    def get_did(self):
        return self.did

    def get_did_document(self):
        return self.did_document

    def get_private_key(self):
        return self.private_key
