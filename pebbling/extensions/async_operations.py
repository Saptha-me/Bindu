"""Async utilities for DID operations."""

import os
import asyncio
import logging
from typing import Tuple, Callable, TypeVar, Any
from cryptography.hazmat.primitives.asymmetric import ed25519

logger = logging.getLogger(__name__)

# Check for aiofiles availability
try:
    import aiofiles
    AIOFILES_AVAILABLE = True
except ImportError:
    AIOFILES_AVAILABLE = False
    logger.warning("aiofiles not installed. Async file operations will fall back to sync.")


T = TypeVar('T')


class AsyncOperations:
    """Provides async wrappers for file and CPU-bound operations."""
    
    @staticmethod
    async def run_in_executor(func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Run a sync function in an executor."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, func, *args, **kwargs)
    
    @staticmethod
    async def write_file_async(path: str, content: bytes) -> None:
        """Write content to file asynchronously."""
        if AIOFILES_AVAILABLE:
            async with aiofiles.open(path, "wb") as f:
                await f.write(content)
        else:
            # Fallback to sync in executor
            await AsyncOperations.run_in_executor(AsyncOperations._write_file_sync, path, content)
    
    @staticmethod
    def _write_file_sync(path: str, content: bytes) -> None:
        """Helper method for sync file write."""
        with open(path, "wb") as f:
            f.write(content)
    
    @staticmethod
    async def generate_keys_async(key_manager, recreate: bool = False) -> Tuple[str, str]:
        """Generate and save keys asynchronously."""
        # Check if we need to create keys
        if key_manager.key_files_exist() and not recreate:
            return key_manager.private_key_path, key_manager.public_key_path
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(key_manager.private_key_path), exist_ok=True)
        
        # Generate keys (CPU-bound operation)
        private_key = await AsyncOperations.run_in_executor(ed25519.Ed25519PrivateKey.generate)
        public_key = private_key.public_key()
        
        # Serialize keys
        private_pem = key_manager.serialize_private_key(private_key)
        public_pem = key_manager.serialize_public_key(public_key)
        
        # Write keys asynchronously
        await AsyncOperations.write_file_async(key_manager.private_key_path, private_pem)
        await AsyncOperations.write_file_async(key_manager.public_key_path, public_pem)
        
        # Set permissions
        await AsyncOperations.run_in_executor(os.chmod, key_manager.private_key_path, 0o600)
        await AsyncOperations.run_in_executor(os.chmod, key_manager.public_key_path, 0o644)
        
        return key_manager.private_key_path, key_manager.public_key_path
