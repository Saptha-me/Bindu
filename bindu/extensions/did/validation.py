from __future__ import annotations
import re
from typing import Optional, Dict, Any, List, Tuple


class DIDValidation:
    """Validation utilities for DID formats and documents."""
    
    # Regex patterns for DID validation
    DID_PATTERN = re.compile(r'^did:[a-z0-9]+:.+$', re.IGNORECASE)
    bindu_DID_PATTERN = re.compile(r'^did:bindu:[^:]+:[^:]+$', re.IGNORECASE)
    
    @staticmethod
    def validate_did_format(did: str) -> Tuple[bool, Optional[str]]:
        """
        Validate DID format according to W3C spec.
        
        Args:
            did: The DID string to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not did:
            return False, "DID cannot be empty"
        
        # Quick prefix check before splitting
        if not did.startswith("did:"):
            return False, "DID must start with 'did:'"
        
        # Basic pattern validation
        if not DIDValidation.DID_PATTERN.match(did):
            return False, "DID format is invalid"
        
        # Extract method efficiently (only split once, limit splits)
        parts = did.split(":", 3)  # Split into max 4 parts: ['did', 'method', 'id', ...]
        
        if len(parts) < 3:
            return False, "DID must have at least 3 parts separated by ':'"
        
        method = parts[1]
        
        # For bindu DIDs, validate specific format
        if method == "bindu":
            if not DIDValidation.bindu_DID_PATTERN.match(did):
                return False, "bindu DID must have format did:bindu:author:agent_name"
            
            # Validate non-empty components
            if len(parts) != 4 or not parts[2] or not parts[3]:
                return False, "Author and agent name cannot be empty in bindu DID"
        
        return True, None
    
    @staticmethod
    def validate_did_document(did_doc: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate a DID document structure.
        
        Args:
            did_doc: The DID document dictionary
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Required fields validation
        if "@context" not in did_doc:
            errors.append("Missing @context field")
        
        if "id" not in did_doc:
            errors.append("Missing id field")
        else:
            valid, error = DIDValidation.validate_did_format(did_doc["id"])
            if not valid:
                errors.append(f"Invalid DID in id field: {error}")
        
        # Validate authentication if present
        if "authentication" in did_doc:
            auth_list = did_doc["authentication"]
            if not isinstance(auth_list, list):
                errors.append("Authentication must be an array")
            else:
                # Use list comprehension for more efficient validation
                for i, auth in enumerate(auth_list):
                    if not isinstance(auth, dict):
                        errors.append(f"Authentication[{i}] must be an object")
                        continue
                    
                    if "type" not in auth:
                        errors.append(f"Authentication[{i}] missing type")
                    if "controller" not in auth:
                        errors.append(f"Authentication[{i}] missing controller")
        
        return len(errors) == 0, errors
