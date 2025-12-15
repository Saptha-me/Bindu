# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""Negotiation module for capability-based agent selection.

This module implements Phase 1 of the negotiation system, enabling orchestrators
to evaluate agent capabilities and select the best agent for a task.
"""

from .capability_calculator import CapabilityCalculator

__all__ = ["CapabilityCalculator"]
