# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""Data models for DSPy integration.

This module defines minimal dataclasses for representing database interactions
and prompt optimization results. These are pure data containers with no
validation or business logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class Interaction:
    """Represents a single database interaction for training.

    This is a read-only snapshot of a task interaction, containing the
    essential data needed for prompt optimization.
    """

    id: UUID
    text: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class PromptCandidate:
    """Represents an optimized prompt candidate.

    After DSPy optimization, multiple prompt candidates are generated
    with associated quality scores. This model captures one such candidate.
    """

    text: str
    score: float
    metadata: dict[str, Any]
