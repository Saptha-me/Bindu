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
Pebbling Server Workers.

Worker classes for task execution in the Pebbling framework.
Workers are responsible for executing tasks received from schedulers.

This module provides:
- Base Worker class for implementing custom workers
- ManifestWorker for executing AgentManifest-based tasks
- Utility classes for message conversion and artifact building
"""

from .manifest_worker import ManifestWorker

__all__ = [
    "ManifestWorker",
]
