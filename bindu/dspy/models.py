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
    
    Attributes:
        id: Unique identifier from the task
        user_input: The input from the user
        agent_output: The output from the agent/assistant
        feedback_score: Normalized feedback score [0.0, 1.0], None if no feedback
        feedback_type: Type of feedback (e.g., 'rating', 'thumbs_up'), None if no feedback
    """

    id: UUID
    user_input: str
    agent_output: str
    feedback_score: float | None = None
    feedback_type: str | None = None


@dataclass(frozen=True)
class PromptCandidate:
    """Represents an optimized prompt candidate.

    After DSPy optimization, multiple prompt candidates are generated
    with associated quality scores. This model captures one such candidate.
    """

    text: str
    score: float
    metadata: dict[str, Any]