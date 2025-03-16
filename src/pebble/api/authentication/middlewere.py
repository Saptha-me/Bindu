from fastapi import Depends, HTTPException, Request
from fastapi.security import APIKeyHeader
from typing import Optional, Dict
from fastapi import HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

class APIKeyPermission:
    """Permission class for API key authentication.
    
    This class handles API key-based authentication using the X-API-Key header.
    It validates the API key against the configured key in settings.
    
    Usage:
        @app.get("/protected")
        async def protected_route(auth = Depends(APIKeyPermission())):
            return {"message": "Access granted"}
    """
    
    def __init__(self, auto_error: bool = True):
        self.auto_error = auto_error
        self.api_key_header = APIKeyHeader(name="X-API-Key", auto_error=auto_error)
        self.api_key = "1234"  # API key from settings
    
    async def __call__(
        self, request: Request
    ) -> Optional[str]:
        """Validate the API key in the request.
        
        Args:
            request: The incoming request
            
        Returns:
            str: The validated API key
            
        Raises:
            HTTPException: If API key is invalid or missing
        """
        api_key: str = await self.api_key_header(request)
        
        if not api_key:
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Missing API key"
                )
            return None
            
        if not self._is_valid_api_key(api_key):
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Invalid API key"
                )
            return None
            
        return api_key
    
    def _is_valid_api_key(self, api_key: str) -> bool:
        """Check if the provided API key is valid.
        
        Args:
            api_key: The API key to validate
            
        Returns:
            bool: True if API key is valid, False otherwise
        """
        return api_key == self.api_key


class Permission:
    """Enum-like class for defining permissions"""
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"


class PermissionChecker:
    """Check specific permissions for API keys.
    
    This class can be extended to implement more sophisticated permission checking,
    such as role-based access control or database-backed permissions.
    """
    
    def __init__(self, required_permission: str):
        self.required_permission = required_permission
        self.api_key_auth = APIKeyPermission()
        
        # Define permission levels (can be moved to settings/database)
        self.permission_levels = {
            Permission.READ: 1,
            Permission.WRITE: 2,
            Permission.ADMIN: 3
        }
        
        # Define API key permissions (can be moved to settings/database)
        self.api_key_permissions = {
            get_settings().api_key: Permission.ADMIN  # Give admin access to configured key
        }
    
    async def __call__(self, request: Request) -> str:
        """Check if the API key has the required permission.
        
        Args:
            request: The incoming request
            
        Returns:
            str: The validated API key
            
        Raises:
            HTTPException: If API key lacks required permission
        """
        api_key = await self.api_key_auth(request)
        
        if not self.has_permission(api_key, self.required_permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"API key missing required permission: {self.required_permission}"
            )
            
        return api_key
    
    def has_permission(self, api_key: str, required_permission: str) -> bool:
        """Check if an API key has a specific permission.
        
        Args:
            api_key: The API key to check
            required_permission: The required permission level
            
        Returns:
            bool: True if API key has required permission, False otherwise
        """
        if api_key not in self.api_key_permissions:
            return False
            
        key_permission = self.api_key_permissions[api_key]
        key_level = self.permission_levels.get(key_permission, 0)
        required_level = self.permission_levels.get(required_permission, 0)
        
        return key_level >= required_level


def require_permission(permission: str):
    """Dependency function for checking specific permissions.
    
    Usage:
        @app.get("/admin")
        async def admin_route(auth = Depends(require_permission(Permission.ADMIN))):
            return {"message": "Admin access granted"}
    """
    return PermissionChecker(permission)