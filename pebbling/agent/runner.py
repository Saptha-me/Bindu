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
Framework-agnostic agent runner for Pebbling framework.

This module provides utilities for running agents in different modes (sync, async, streaming)
regardless of their underlying implementation, using the standard Pebbling protocol.
"""

import uuid
from typing import Any, AsyncGenerator, Dict, List, Optional, Union
from uuid import UUID

# Import existing protocol types
from pebbling.protocol.types import DataPart, Message, MessageSendConfiguration, Part, Role, RunMode, TextPart
from pebbling.agent.agent_adapter import AgentAdapter, PebblingContext, PebblingMessage
from pebbling.utils.logging import get_logger

logger = get_logger("pebbling.agent.runner")

