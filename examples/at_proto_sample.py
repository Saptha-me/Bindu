from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
import base58

class DIDManager:
    def __init__(self):
        # Generate a new Ed25519 key pair
        self.private_key = ed25519.Ed25519PrivateKey.generate()
        self.public_key = self.private_key.public_key()

        # Generate DID
        public_bytes = self.public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        public_base58 = base58.b58encode(public_bytes).decode('utf-8')
        self.did = f"did:key:{public_base58}"

    def get_did(self):
        return self.did

    def sign(self, message: bytes) -> bytes:
        return self.private_key.sign(message)

    def get_did_document(self):
        public_bytes = self.public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        public_base58 = base58.b58encode(public_bytes).decode('utf-8')

        return {
            "@context": "https://www.w3.org/ns/did/v1",
            "id": self.did,
            "verificationMethod": [{
                "id": f"{self.did}#key-1",
                "type": "Ed25519VerificationKey2018",
                "controller": self.did,
                "publicKeyBase58": public_base58
            }],
            "authentication": [
                f"{self.did}#key-1"
            ]
        }


from agno.agent import Agent

# Create the agent
agent = Agent(name="PlutoAgent")

# Create the DID manager
did_manager = DIDManager()
dpc = did_manager.get_did_document()

# Attach the DID to the agent
agent.extra_data = agent.extra_data or {}
agent.extra_data["did"] = did_manager.get_did()


# Run the agent
agent.run()