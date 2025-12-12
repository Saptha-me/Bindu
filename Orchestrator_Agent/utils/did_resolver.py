import hashlib
import json
from typing import Optional, Dict, Any
from .logger import get_logger


class DIDResolver:
    """Resolves and verifies Bindu DIDs"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.did_cache: Dict[str, Dict[str, Any]] = {}
    
    def resolve_did(self, did: str) -> Optional[Dict[str, Any]]:

        # Check cache first
        if did in self.did_cache:
            return self.did_cache[did]
        
        self.logger.debug(f"Resolving DID: {did}")
        
        # Parse DID
        did_doc = self._parse_did(did)
        if not did_doc:
            self.logger.error(f"Invalid DID format: {did}")
            return None
        
        # Cache the result
        self.did_cache[did] = did_doc
        return did_doc
    
    def _parse_did(self, did: str) -> Optional[Dict[str, Any]]:
        """Parse DID and extract components"""
        try:
            # Expected format: did:bindu:type:name:id
            parts = did.split(":")
            if len(parts) < 5 or parts[0] != "did" or parts[1] != "bindu":
                return None
            
            return {
                "did": did,
                "method": parts[1],
                "type": parts[2],
                "name": parts[3],
                "id": parts[4],
                "created_at": "2025-01-01T00:00:00Z"
            }
        except Exception as e:
            self.logger.error(f"Error parsing DID: {str(e)}")
            return None
    
    def verify_signature(self, did: str, message: str, signature: str) -> bool:

        self.logger.debug(f"Verifying signature for {did}")
        
        # In production, would use actual cryptographic verification
        # For now, verify format
        if not did.startswith("did:bindu:"):
            self.logger.warning(f"Invalid DID format: {did}")
            return False
        
        if not signature or len(signature) < 16:
            self.logger.warning(f"Invalid signature format")
            return False
        
        # Calculate expected signature hash
        expected_hash = hashlib.sha256(f"{did}{message}".encode()).hexdigest()
        
        return signature.startswith(expected_hash[:8])
    
    def create_signature(self, did: str, message: str) -> str:

        self.logger.debug(f"Creating signature for {did}")
        
        # Create hash-based signature
        data = f"{did}{message}".encode()
        signature = hashlib.sha256(data).hexdigest()
        
        return signature
    
    def clear_cache(self) -> None:
        """Clear the DID cache"""
        self.did_cache.clear()
        self.logger.info("Cleared DID resolver cache")
