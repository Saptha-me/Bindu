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
In-memory store implementation for Pebbling server.

Simple dictionary-based storage for development and testing.
Thread-safe with asyncio locks.
"""

import asyncio
from typing import Dict, List, Optional, TypeVar
from .base import BaseStore

T = TypeVar('T')


class MemoryStore(BaseStore[T]):
    """Simple in-memory store implementation using a dictionary."""
    
    def __init__(self):
        self._data: Dict[str, T] = {}
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[T]:
        """Retrieve an item by key."""
        async with self._lock:
            return self._data.get(key)
    
    async def set(self, key: str, value: T) -> None:
        """Store an item by key."""
        async with self._lock:
            self._data[key] = value
    
    async def delete(self, key: str) -> bool:
        """Delete an item by key. Returns True if item existed."""
        async with self._lock:
            if key in self._data:
                del self._data[key]
                return True
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if an item exists by key."""
        async with self._lock:
            return key in self._data
    
    async def list_keys(self, prefix: Optional[str] = None) -> List[str]:
        """List all keys, optionally filtered by prefix."""
        async with self._lock:
            if prefix is None:
                return list(self._data.keys())
            return [key for key in self._data.keys() if key.startswith(prefix)]
    
    async def clear(self) -> None:
        """Clear all items from the store."""
        async with self._lock:
            self._data.clear()
    
    async def size(self) -> int:
        """Get the number of items in the store."""
        async with self._lock:
            return len(self._data)
    
    def __len__(self) -> int:
        """Synchronous length check (use size() for async)."""
        return len(self._data)
