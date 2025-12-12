from typing import Any, Optional, Callable, Dict
from datetime import datetime, timedelta
from .logger import get_logger


class CacheEntry:
    """Represents a cache entry with TTL"""
    
    def __init__(self, value: Any, ttl_seconds: int = 3600):
        self.value = value
        self.created_at = datetime.utcnow()
        self.ttl_seconds = ttl_seconds
    
    def is_expired(self) -> bool:
        """Check if cache entry has expired"""
        age = (datetime.utcnow() - self.created_at).total_seconds()
        return age > self.ttl_seconds


class Cache:
    """Simple in-memory cache with TTL support"""
    
    def __init__(self, default_ttl: int = 3600):
        self.logger = get_logger(__name__)
        self.cache: Dict[str, CacheEntry] = {}
        self.default_ttl = default_ttl
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if key not in self.cache:
            return None
        
        entry = self.cache[key]
        if entry.is_expired():
            del self.cache[key]
            return None
        
        self.logger.debug(f"Cache hit: {key}")
        return entry.value
    
    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """Set value in cache"""
        ttl = ttl_seconds or self.default_ttl
        self.cache[key] = CacheEntry(value, ttl)
        self.logger.debug(f"Cache set: {key} (TTL: {ttl}s)")
    
    def delete(self, key: str) -> bool:
        """Delete value from cache"""
        if key in self.cache:
            del self.cache[key]
            self.logger.debug(f"Cache delete: {key}")
            return True
        return False
    
    def clear(self) -> None:
        """Clear entire cache"""
        self.cache.clear()
        self.logger.info("Cache cleared")
    
    def get_or_compute(self, key: str, compute_func: Callable, 
                      ttl_seconds: Optional[int] = None) -> Any:
        """Get from cache or compute if missing"""
        # Try to get from cache
        value = self.get(key)
        if value is not None:
            return value
        
        # Compute value
        value = compute_func()
        
        # Store in cache
        self.set(key, value, ttl_seconds)
        
        return value
    
    def get_size(self) -> int:
        """Get cache size"""
        return len(self.cache)
    
    def cleanup_expired(self) -> int:
        """Remove expired entries"""
        expired_keys = [k for k, v in self.cache.items() if v.is_expired()]
        for key in expired_keys:
            del self.cache[key]
        
        if expired_keys:
            self.logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")
        
        return len(expired_keys)


