"""
Utilities for DID key management including rotation and backup.

This module provides utilities for managing DID keys including
key rotation, backup, and recovery functionality.
"""

import os
import shutil
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

import logging

logger = logging.getLogger(__name__)


class DIDKeyRotation:
    """Handles key rotation and backup for DID keys."""
    
    def __init__(self, key_dir: Path, max_backups: int = 3):
        """
        Initialize key rotation utility.
        
        Args:
            key_dir: Directory containing the keys
            max_backups: Maximum number of backup sets to keep
        """
        self.key_dir = key_dir
        self.max_backups = max_backups
        self.backup_dir = key_dir / "backups"
        
    def rotate_keys(self, did_extension, backup: bool = True) -> bool:
        """
        Rotate keys for a DID extension.
        
        Args:
            did_extension: The DIDAgentExtension instance
            backup: Whether to backup existing keys
            
        Returns:
            True if rotation successful, False otherwise
        """
        try:
            # Backup existing keys if requested
            if backup:
                backup_path = self._backup_keys(did_extension)
                logger.info(f"Keys backed up to: {backup_path}")
            
            # Clear cached keys
            if hasattr(did_extension, 'private_key'):
                delattr(did_extension, 'private_key')
            if hasattr(did_extension, 'public_key'):
                delattr(did_extension, 'public_key')
            if hasattr(did_extension, 'did'):
                delattr(did_extension, 'did')
            
            # Invalidate cache
            did_extension._invalidate_cache()
            
            # Force key regeneration
            did_extension.recreate_keys = True
            did_extension.generate_and_save_key_pair()
            
            # Cleanup old backups
            self._cleanup_old_backups()
            
            logger.info("Key rotation completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Key rotation failed: {e}")
            return False
    
    def _backup_keys(self, did_extension) -> Path:
        """Create a backup of existing keys."""
        # Create backup directory
        self.backup_dir.mkdir(exist_ok=True)
        
        # Create timestamped backup folder
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"keys_{timestamp}"
        backup_path.mkdir(exist_ok=True)
        
        # Copy keys
        if os.path.exists(did_extension.private_key_path):
            shutil.copy2(did_extension.private_key_path, backup_path / "private.pem")
        
        if os.path.exists(did_extension.public_key_path):
            shutil.copy2(did_extension.public_key_path, backup_path / "public.pem")
        
        # Save metadata
        metadata = {
            "timestamp": timestamp,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "did": did_extension.did if hasattr(did_extension, '_did') else None,
            "author": did_extension.author,
            "agent_name": did_extension.agent_name
        }
        
        with open(backup_path / "metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)
        
        return backup_path
    
    def _cleanup_old_backups(self):
        """Remove old backups exceeding max_backups limit."""
        if not self.backup_dir.exists():
            return
        
        # Get all backup directories
        backups = sorted([
            d for d in self.backup_dir.iterdir() 
            if d.is_dir() and d.name.startswith("keys_")
        ])
        
        # Remove oldest backups if exceeding limit
        while len(backups) > self.max_backups:
            oldest = backups.pop(0)
            shutil.rmtree(oldest)
            logger.debug(f"Removed old backup: {oldest}")
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """List all available key backups."""
        if not self.backup_dir.exists():
            return []
        
        backups = []
        for backup_dir in sorted(self.backup_dir.iterdir(), reverse=True):
            if backup_dir.is_dir() and backup_dir.name.startswith("keys_"):
                metadata_path = backup_dir / "metadata.json"
                if metadata_path.exists():
                    with open(metadata_path) as f:
                        metadata = json.load(f)
                    metadata["path"] = str(backup_dir)
                    backups.append(metadata)
        
        return backups
    
    def restore_backup(self, did_extension, backup_timestamp: str) -> bool:
        """
        Restore keys from a specific backup.
        
        Args:
            did_extension: The DIDAgentExtension instance
            backup_timestamp: Timestamp of the backup to restore
            
        Returns:
            True if restore successful, False otherwise
        """
        backup_path = self.backup_dir / f"keys_{backup_timestamp}"
        
        if not backup_path.exists():
            logger.error(f"Backup not found: {backup_path}")
            return False
        
        try:
            # Backup current keys before restore
            current_backup = self._backup_keys(did_extension)
            logger.info(f"Current keys backed up to: {current_backup}")
            
            # Clear cached keys
            if hasattr(did_extension, 'private_key'):
                delattr(did_extension, 'private_key')
            if hasattr(did_extension, 'public_key'):
                delattr(did_extension, 'public_key')
            if hasattr(did_extension, 'did'):
                delattr(did_extension, 'did')
            
            # Restore keys
            shutil.copy2(backup_path / "private.pem", did_extension.private_key_path)
            shutil.copy2(backup_path / "public.pem", did_extension.public_key_path)
            
            # Set permissions
            os.chmod(did_extension.private_key_path, 0o600)
            os.chmod(did_extension.public_key_path, 0o644)
            
            # Invalidate cache
            did_extension._invalidate_cache()
            
            logger.info(f"Keys restored from backup: {backup_timestamp}")
            return True
            
        except Exception as e:
            logger.error(f"Key restore failed: {e}")
            return False


class DIDValidation:
    """Validation utilities for DID formats and documents."""
    
    @staticmethod
    def validate_did_format(did: str) -> tuple[bool, Optional[str]]:
        """
        Validate DID format according to W3C spec.
        
        Args:
            did: The DID string to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not did:
            return False, "DID cannot be empty"
        
        parts = did.split(":")
        
        if len(parts) < 3:
            return False, "DID must have at least 3 parts separated by ':'"
        
        if parts[0] != "did":
            return False, "DID must start with 'did:'"
        
        # Validate method (parts[1])
        if not parts[1]:
            return False, "DID method cannot be empty"
        
        # For pebbling DIDs, validate specific format
        if parts[1] == "pebbling":
            if len(parts) != 4:
                return False, "Pebbling DID must have format did:pebbling:author:agent_name"
            
            if not parts[2] or not parts[3]:
                return False, "Author and agent name cannot be empty in Pebbling DID"
        
        return True, None
    
    @staticmethod
    def validate_did_document(did_doc: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        Validate a DID document structure.
        
        Args:
            did_doc: The DID document dictionary
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Required fields
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
            if not isinstance(did_doc["authentication"], list):
                errors.append("Authentication must be an array")
            else:
                for i, auth in enumerate(did_doc["authentication"]):
                    if "type" not in auth:
                        errors.append(f"Authentication[{i}] missing type")
                    if "controller" not in auth:
                        errors.append(f"Authentication[{i}] missing controller")
        
        return len(errors) == 0, errors
