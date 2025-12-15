# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""DSPy integration for Bindu offline prompt optimization.

This module provides tools for training and optimizing prompts using DSPy's
teleprompter system. It is designed exclusively for offline training workflows,
not for live inference or deployment.

The module reads high-quality interaction data from the database, prepares
golden datasets, and optimizes prompts to improve agent performance.
"""

from __future__ import annotations

from .train import train

__all__ = ["train"]