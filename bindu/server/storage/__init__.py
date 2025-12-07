# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
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
   - PostgresStorage: Persistent database storage (production)

3. USAGE PATTERNS:
   - Import the base Storage class for type hints and interfaces
   - Import specific implementations based on your needs
   - All implementations are interchangeable through the Storage interface

AVAILABLE STORAGE OPTIONS:
- InMemoryStorage: Lightning-fast temporary storage
- PostgresStorage: Persistent PostgreSQL storage
"""

from __future__ import annotations as _annotations

# Export the base storage interface
from .base import Storage

# Export all storage implementations
from .memory_storage import InMemoryStorage

# Export factory functions
from .factory import create_storage, close_storage

# Export SQLAlchemy schema (tables, not models)
from .schema import contexts_table, metadata, task_feedback_table, tasks_table

# Conditional import of PostgresStorage (requires SQLAlchemy)
try:
    from .postgres_storage import PostgresStorage
except ImportError:
    PostgresStorage = None  # type: ignore[assignment]  # SQLAlchemy not installed

__all__ = [
    # Base interface
    "Storage",
    # Storage implementations
    "InMemoryStorage",
    "PostgresStorage",
    # Factory functions
    "create_storage",
    "close_storage",
    # SQLAlchemy schema
    "metadata",
    "tasks_table",
    "contexts_table",
    "task_feedback_table",
]
