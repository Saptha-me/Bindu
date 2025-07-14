"""
Token manager for handling verification tokens from Sheldon CA.

This module manages the lifecycle of verification tokens obtained from
the Sheldon Certificate Authority, including storage, validation, and
renewal.
"""

import json
import time
import logging
import os.path
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta

from pebbling.security.config import DEFAULT_TOKEN_VALIDITY
from pebbling.security.mtls.exceptions import TokenError, TokenExpiredError

logger = logging.getLogger(__name__)


class TokenManager:
    """Manages verification tokens from the Sheldon CA.
    
    This class handles:
    1. Storing tokens with their expiration timestamps
    2. Checking token validity
    3. Loading/saving tokens from persistent storage
    """
    
    def __init__(
        self, 
        token_file: Optional[str] = None,
        token_validity: timedelta = DEFAULT_TOKEN_VALIDITY
    ):
        """Initialize the token manager.
        
        Args:
            token_file: Path to the file for storing tokens. If None, tokens
                        will not be persisted to disk
            token_validity: Default validity period for tokens
        """
        self.token_file = token_file
        self.token_validity = token_validity
        self.tokens: Dict[str, Dict[str, Any]] = {}
        
        # Try to load existing tokens if token_file is specified
        if token_file and os.path.exists(token_file):
            try:
                self.load_tokens()
            except Exception as e:
                logger.warning(f"Failed to load tokens from {token_file}: {e}")
    
    def store_token(
        self, 
        certificate_id: str, 
        token: str, 
        expires_at: Optional[datetime] = None
    ) -> None:
        """Store a verification token with expiration.
        
        Args:
            certificate_id: Identifier for the certificate (usually fingerprint)
            token: The verification token from Sheldon CA
            expires_at: When the token expires. If None, uses default validity
            
        Raises:
            TokenError: If there's an issue storing the token
        """
        try:
            if expires_at is None:
                expires_at = datetime.utcnow() + self.token_validity
                
            self.tokens[certificate_id] = {
                "token": token,
                "expires_at": expires_at.timestamp()
            }
            
            if self.token_file:
                self.save_tokens()
                
            logger.info(f"Stored verification token for certificate {certificate_id}, "
                      f"expires at {expires_at.isoformat()}")
                      
        except Exception as e:
            error_msg = f"Failed to store token: {str(e)}"
            logger.error(error_msg)
            raise TokenError(error_msg) from e
    
    def get_token(self, certificate_id: str) -> Tuple[str, bool]:
        """Get a token and check if it's valid.
        
        Args:
            certificate_id: Identifier for the certificate
            
        Returns:
            Tuple of (token, is_valid)
            
        Raises:
            TokenError: If the token doesn't exist
            TokenExpiredError: If the token has expired
        """
        if certificate_id not in self.tokens:
            error_msg = f"No token found for certificate {certificate_id}"
            logger.error(error_msg)
            raise TokenError(error_msg)
            
        token_data = self.tokens[certificate_id]
        token = token_data["token"]
        expires_at = token_data["expires_at"]
        
        # Check if token has expired
        if time.time() > expires_at:
            error_msg = f"Token for certificate {certificate_id} has expired"
            logger.warning(error_msg)
            raise TokenExpiredError(error_msg)
            
        # Calculate remaining validity period
        valid_for = expires_at - time.time()
        is_expiring_soon = valid_for < (self.token_validity.total_seconds() / 4)
        
        if is_expiring_soon:
            logger.info(f"Token for certificate {certificate_id} will expire soon "
                      f"(in {valid_for:.1f} seconds)")
            
        return token, is_expiring_soon
        
    def is_token_valid(self, certificate_id: str) -> bool:
        """Check if a token is valid and not expired.
        
        Args:
            certificate_id: Identifier for the certificate
            
        Returns:
            True if the token exists and is valid, False otherwise
        """
        try:
            self.get_token(certificate_id)
            return True
        except (TokenError, TokenExpiredError):
            return False
    
    def remove_token(self, certificate_id: str) -> None:
        """Remove a token.
        
        Args:
            certificate_id: Identifier for the certificate
            
        Raises:
            TokenError: If the token doesn't exist
        """
        if certificate_id not in self.tokens:
            error_msg = f"No token found for certificate {certificate_id}"
            logger.error(error_msg)
            raise TokenError(error_msg)
            
        del self.tokens[certificate_id]
        
        if self.token_file:
            self.save_tokens()
            
        logger.info(f"Removed token for certificate {certificate_id}")
        
    def remove_expired_tokens(self) -> int:
        """Remove all expired tokens.
        
        Returns:
            Number of tokens removed
        """
        current_time = time.time()
        expired_ids = [
            cert_id for cert_id, data in self.tokens.items()
            if data["expires_at"] < current_time
        ]
        
        for cert_id in expired_ids:
            del self.tokens[cert_id]
            
        if expired_ids and self.token_file:
            self.save_tokens()
            
        if expired_ids:
            logger.info(f"Removed {len(expired_ids)} expired tokens")
            
        return len(expired_ids)
    
    def save_tokens(self) -> None:
        """Save tokens to the token file.
        
        Raises:
            TokenError: If saving fails
        """
        if not self.token_file:
            return
            
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.token_file), exist_ok=True)
            
            with open(self.token_file, "w") as f:
                json.dump(self.tokens, f)
                
        except Exception as e:
            error_msg = f"Failed to save tokens to {self.token_file}: {str(e)}"
            logger.error(error_msg)
            raise TokenError(error_msg) from e
    
    def load_tokens(self) -> None:
        """Load tokens from the token file.
        
        Raises:
            TokenError: If loading fails
        """
        if not self.token_file or not os.path.exists(self.token_file):
            return
            
        try:
            with open(self.token_file, "r") as f:
                self.tokens = json.load(f)
                
            # Remove any expired tokens during load
            self.remove_expired_tokens()
                
        except Exception as e:
            error_msg = f"Failed to load tokens from {self.token_file}: {str(e)}"
            logger.error(error_msg)
            raise TokenError(error_msg) from e
