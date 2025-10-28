"""Response detection utilities for ManifestWorker.

This module handles parsing and detection of agent responses to determine
task states (input-required, auth-required, completed, etc.).
"""

from __future__ import annotations

import json
import re
from typing import Any, Optional

from bindu.common.protocol.types import TaskState
from bindu.settings import app_settings


class ResponseDetector:
    """Detects and parses agent responses for state transitions.

    This class provides static methods for:
    - Parsing structured JSON responses
    - Determining task state from agent responses
    - Handling both structured and unstructured responses

    All methods are stateless and can be used independently.
    """

    @staticmethod
    def parse_structured_response(result: Any) -> Optional[dict[str, Any]]:
        """Parse agent response for structured state transitions.

        Handles multiple response types:
        - dict: Direct structured response
        - str: JSON string or plain text
        - list: Array of messages/content
        - other: Images, binary data, etc.

        Structured format:
        {"state": "input-required|auth-required", "prompt": "...", ...}

        Strategy:
        1. If dict with "state" key → return directly
        2. If string → try JSON parsing
        3. If string → try regex extraction of JSON blocks
        4. Otherwise → return None (normal completion)

        Args:
            result: Agent execution result (any type)

        Returns:
            Dict with state info if structured response found, None otherwise
        """
        # Strategy 1: Direct dict response
        if isinstance(result, dict):
            if "state" in result:
                return result
            return None

        # Strategy 2: String response - try JSON parsing
        if isinstance(result, str):
            # Try parsing entire response as JSON
            try:
                parsed = json.loads(result)
                if isinstance(parsed, dict) and "state" in parsed:
                    return parsed
            except (json.JSONDecodeError, ValueError):
                pass

            # Try extracting JSON from text using regex
            json_pattern = r'\{[^{}]*"state"[^{}]*\}'
            matches = re.findall(json_pattern, result, re.DOTALL)

            for match in matches:
                try:
                    parsed = json.loads(match)
                    if isinstance(parsed, dict) and "state" in parsed:
                        return parsed
                except (json.JSONDecodeError, ValueError):
                    continue

        # Strategy 3: Other types (list, bytes, etc.) - no state transition
        return None

    @staticmethod
    def determine_task_state(
        result: Any, structured: Optional[dict[str, Any]]
    ) -> tuple[TaskState, Any]:
        """Determine task state from agent response.

        Handles multiple response types:
        - Structured dict: {"state": "...", "prompt": "..."}
        - Plain string: "Hello! How can I assist you?"
        - Rich content: {"text": "...", "image": "..."}
        - Binary data: images, files, etc.

        Args:
            result: Agent execution result (any type)
            structured: Parsed structured response if available

        Returns:
            Tuple of (state, message_content)
            message_content can be str, dict, list, or any serializable type
        """
        # Check structured response first (preferred)
        if structured:
            state = structured.get("state")
            if state == "input-required":
                prompt = structured.get("prompt", result)
                return ("input-required", prompt)
            elif state == "auth-required":
                prompt = structured.get("prompt", result)
                return ("auth-required", prompt)
            elif state == app_settings.x402.status_required:
                # Keep overall task state as input-required; carry structured info forward
                return ("input-required", structured)

        # Default: task completion with any result type
        return ("completed", result)
