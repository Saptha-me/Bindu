# 
# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/Pebbling-ai/pebble/issues/new/choose |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🐧

"""
Base store interface for Pebbling server.

Provides abstract base class for all store implementations.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TypeVar, Generic

T = TypeVar('T')


class BaseStore(Generic[T], ABC):
    """Abstract base class for all store implementations."""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[T]:
        """Retrieve an item by key."""
        pass
    
    @abstractmethod
    async def set(self, key: str, value: T) -> None:
        """Store an item by key."""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete an item by key. Returns True if item existed."""
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if an item exists by key."""
        pass
    
    @abstractmethod
    async def list_keys(self, prefix: Optional[str] = None) -> List[str]:
        """List all keys, optionally filtered by prefix."""
        pass
    
    @abstractmethod
    async def clear(self) -> None:
        """Clear all items from the store."""
        pass
    
    async def get_all(self, keys: List[str]) -> Dict[str, Optional[T]]:
        """Get multiple items by keys."""
        result = {}
        for key in keys:
            result[key] = await self.get(key)
        return result
    
    async def set_all(self, items: Dict[str, T]) -> None:
        """Set multiple items."""
        for key, value in items.items():
            await self.set(key, value)
