# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""Configuration constants for DSPy integration.

This module defines the constants used for DSPy prompt optimization,
including model settings, filtering thresholds, and optimization parameters.
"""

from __future__ import annotations

# DSPy Model Configuration
DEFAULT_DSPY_MODEL = "gpt-3.5-turbo"
"""Default language model for DSPy optimization."""

# Dataset Filtering Thresholds
MIN_RATING_THRESHOLD = 4
"""Minimum rating for interactions to be included in training dataset (1-5 scale)."""

MIN_SCORE_THRESHOLD = 0.7
"""Minimum score for interactions to be included in training dataset (0.0-1.0 scale)."""

# Prompt Optimization Parameters
NUM_PROMPT_CANDIDATES = 3
"""Number of optimized prompt candidates to generate and return."""

MAX_BOOTSTRAPPED_DEMOS = 8
"""Maximum number of bootstrapped demonstrations for few-shot learning."""

# Database Query Limits
MAX_INTERACTIONS_QUERY_LIMIT = 10000
"""Maximum number of interactions to fetch from database in a single query."""
