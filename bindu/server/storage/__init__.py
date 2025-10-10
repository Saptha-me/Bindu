# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/Saptha-me/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""STORAGE MODULE EXPORTS.

This module provides the storage layer for the bindu framework.
It exposes different storage implementations for tasks and contexts.

BURGER STORE ANALOGY:

Think of this as the restaurant's order management system catalog:

1. STORAGE INTERFACE (Storage):
   - Abstract base class defining the storage contract
   - All storage implementations must follow this interface
   - Ensures consistent API across different storage backends

2. STORAGE IMPLEMENTATIONS:
   - InMemoryStorage: Fast whiteboard system (development/testing)

3. USAGE PATTERNS:
   - Import the base Storage class for type hints and interfaces
   - Import specific implementations based on your needs
   - All implementations are interchangeable through the Storage interface

AVAILABLE STORAGE OPTIONS:
- InMemoryStorage: Lightning-fast temporary storage
"""

from __future__ import annotations as _annotations

# Export the base storage interface
from .base import Storage

# Export all storage implementations
from .memory_storage import InMemoryStorage

__all__ = [
    # Base interface
    "Storage",
    # Storage implementations
    "InMemoryStorage",
]
