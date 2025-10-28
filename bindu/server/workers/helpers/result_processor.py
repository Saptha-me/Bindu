"""Result processing utilities for ManifestWorker.

This module handles collection and normalization of agent execution results,
supporting various return types including generators, async generators, and
different data structures.
"""

from __future__ import annotations

from typing import Any

from bindu.utils.logging import get_logger

logger = get_logger("bindu.server.workers.helpers.result_processor")


class ResultProcessor:
    """Handles result collection and normalization from agent execution.

    This class provides static methods for:
    - Collecting results from generators and async generators
    - Normalizing results to extract final responses
    - Serializing results to strings

    All methods are stateless and can be used independently.
    """

    @staticmethod
    async def collect_results(raw_results: Any) -> Any:
        """Collect results from manifest execution.

        Handles different result types:
        - Direct return: str, dict, list, etc.
        - Generator: Collect all yielded values
        - Async generator: Await and collect all yielded values

        Args:
            raw_results: Raw result from manifest.run()

        Returns:
            Collected result (single value or last yielded value)
        """
        # Check if it's an async generator
        if hasattr(raw_results, "__anext__"):
            collected = []
            try:
                async for chunk in raw_results:
                    collected.append(chunk)
            except StopAsyncIteration:
                pass
            # Return last chunk or all chunks if multiple
            return collected[-1] if collected else None

        # Check if it's a sync generator
        elif hasattr(raw_results, "__next__"):
            collected = []
            try:
                for chunk in raw_results:
                    collected.append(chunk)
            except StopIteration:
                pass
            # Return last chunk or all chunks if multiple
            return collected[-1] if collected else None

        # Direct return value (str, dict, list, etc.)
        else:
            return raw_results

    @staticmethod
    def normalize_result(result: Any) -> Any:
        """Intelligently normalize agent result to extract final response.

        This method gives users full control over what they return from handlers:
        - Return raw agent output → System extracts intelligently
        - Return pre-extracted string → System uses directly
        - Return structured dict → System respects state transitions

        Handles multiple formats from different frameworks:
        - Plain string: "Hello!" → "Hello!"
        - Dict with state: {"state": "input-required", ...} → pass through
        - Dict with content: {"content": "Hello!"} → "Hello!"
        - List of messages: [Message(...), Message(content="Hello!")] → "Hello!"
        - Message object: Message(content="Hello!") → "Hello!"
        - Custom objects: Try .content, .to_dict()["content"], or str()

        Args:
            result: Raw result from handler function

        Returns:
            Normalized result (str, dict with state, or original if can't normalize)
        """
        # Strategy 1: Already a string - use directly
        if isinstance(result, str):
            return result

        # Strategy 2: Dict with "state" key - structured response (pass through)
        if isinstance(result, dict):
            if "state" in result:
                return result  # Structured state transition
            elif "content" in result:
                return result["content"]  # Extract content from dict
            else:
                return result  # Unknown dict format, pass through

        # Strategy 3: List (e.g., list of Message objects from Agno)
        if isinstance(result, list) and result:
            last_item = result[-1]

            # Try to extract content from last item
            if hasattr(last_item, "content"):
                return last_item.content
            elif hasattr(last_item, "to_dict"):
                item_dict = last_item.to_dict()
                if "content" in item_dict:
                    return item_dict["content"]
            elif isinstance(last_item, dict) and "content" in last_item:
                return last_item["content"]
            elif isinstance(last_item, str):
                return last_item

            # Can't extract, return last item as-is
            return last_item

        # Strategy 4: Object with .content attribute (e.g., Message object)
        if hasattr(result, "content"):
            return result.content

        # Strategy 5: Object with .to_dict() method
        if hasattr(result, "to_dict"):
            try:
                result_dict = result.to_dict()
                if "content" in result_dict:
                    return result_dict["content"]
                return result_dict
            except Exception as e:
                logger.debug(
                    "Failed to extract content from .to_dict() method", error=str(e)
                )

        # Strategy 6: Fallback to string conversion
        return str(result) if result is not None else ""
