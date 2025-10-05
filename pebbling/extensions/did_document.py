"""DID document generation and formatting utilities."""

from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
import base58
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519


class DIDDocument:
    """Handles DID document generation and formatting."""
    
    @staticmethod
    def generate_did(author: Optional[str], agent_name: Optional[str], public_key_path: Optional[str] = None) -> str:
        """Generate DID identifier.
        
        Args:
            author: Agent author/owner
            agent_name: Name of the agent
            public_key_path: Path to public key file (for did:key fallback)
            
        Returns:
            DID string
        """
        # Use custom Pebbling format if author and agent_name provided
        if author and agent_name:
            sanitized_author = author.lower().replace(' ', '_').replace('@', '_at_').replace('.', '_')
            sanitized_agent_name = agent_name.lower().replace(' ', '_')
            return f"did:pebbling:{sanitized_author}:{sanitized_agent_name}"
        
        # Fallback to did:key format
        if public_key_path:
            with open(public_key_path, "rb") as f:
                public_key_pem = f.read()
            
            public_key = serialization.load_pem_public_key(public_key_pem)
            raw_bytes = public_key.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw
            )
            
            # Encode in base58btc with 'z' prefix (multibase convention for ed25519)
            multibase_encoded = "z" + base58.b58encode(raw_bytes).decode("ascii")
            return f"did:key:{multibase_encoded}"
        
        raise ValueError("Cannot generate DID without author/agent_name or public_key_path")
    
    @staticmethod
    def create_did_document(
        did: str,
        public_key: ed25519.Ed25519PublicKey,
        author: Optional[str] = None,
        agent_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a W3C-compliant DID document.
        
        Args:
            did: DID identifier
            public_key: Ed25519 public key
            author: Agent author/owner
            agent_name: Name of the agent
            metadata: Additional metadata to include
            
        Returns:
            DID document dictionary
        """
        # Get public key in base58 format
        public_key_b58 = base58.b58encode(
            public_key.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw
            )
        ).decode("ascii")
        
        did_doc = {
            "@context": ["https://www.w3.org/ns/did/v1", "https://pebbling.ai/ns/v1"],
            "id": did,
            "created": datetime.now(timezone.utc).isoformat() + "Z",
            
            # Authentication method
            "authentication": [{
                "id": f"{did}#key-1",
                "type": "Ed25519VerificationKey2020",
                "controller": did,
                "publicKeyBase58": public_key_b58
            }],
            
            # Pebbling-specific metadata
            "pebbling": {
                "agentName": agent_name,
                "author": author,
            }
        }
        
        # Add additional metadata if provided
        if metadata:
            did_doc["pebbling"].update(metadata)
            
            # Add service endpoints if URL is available
            if "url" in metadata:
                did_doc["service"] = [{
                    "id": f"{did}#agent-service",
                    "type": "PebblingAgentService",
                    "serviceEndpoint": metadata["url"]
                }]
        
        return did_doc
    
    @staticmethod
    def create_agent_info(
        did: str,
        public_key: ed25519.Ed25519PublicKey,
        author: Optional[str] = None,
        agent_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create simplified agent info (user-friendly format).
        
        Args:
            did: DID identifier
            public_key: Ed25519 public key
            author: Agent author/owner
            agent_name: Name of the agent
            metadata: Additional metadata to include
            
        Returns:
            Agent info dictionary
        """
        info = {
            "did": did,
            "agentName": agent_name,
            "author": author,
            "publicKey": base58.b58encode(
                public_key.public_bytes(
                    encoding=serialization.Encoding.Raw,
                    format=serialization.PublicFormat.Raw
                )
            ).decode("ascii"),
            "created": datetime.now(timezone.utc).isoformat(),
        }
        
        # Add all metadata fields
        if metadata:
            info.update(metadata)
        
        return info
