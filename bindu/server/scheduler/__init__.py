# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/Saptha-me/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""SCHEDULER MODULE EXPORTS.

This module provides the scheduler layer for the bindu framework.
It exposes different scheduler implementations for task queue management.

BURGER STORE ANALOGY:

Think of this as the restaurant's order board system catalog:

1. SCHEDULER INTERFACE (Scheduler):
   - Abstract base class defining the scheduler contract
   - All scheduler implementations must follow this interface
   - Ensures consistent API across different scheduling backends

2. SCHEDULER IMPLEMENTATIONS:
   - InMemoryScheduler: Simple whiteboard system (development/testing)
   - RedisScheduler: Distributed cloud system (production/multi-process)

3. TASK OPERATIONS:
   - TaskOperation: Union type for all task operations (run, cancel, pause, resume)
   - Individual operation types for type safety and validation

4. USAGE PATTERNS:
    - Import the base Scheduler class for type hints and interfaces
    - Import specific implementations based on your deployment needs
    - All implementations are interchangeable through the Scheduler interface

AVAILABLE SCHEDULER OPTIONS:
- InMemoryScheduler: Fast in-memory task queue for single-process deployments
- RedisScheduler: Distributed task queue using Redis for multi-process systems # TODO: Add RedisScheduler
"""

from __future__ import annotations as _annotations

# Export the base scheduler interface
from .base import Scheduler, TaskOperation

# Export all scheduler implementations
from .memory_scheduler import InMemoryScheduler

# from .redis_scheduler import RedisScheduler # TODO: Add RedisScheduler

__all__ = [
    # Base interface
    "Scheduler",
    "TaskOperation",
    # Scheduler implementations
    "InMemoryScheduler",
    # "RedisScheduler", # TODO: Add RedisScheduler
]
