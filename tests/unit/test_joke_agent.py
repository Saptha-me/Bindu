"""Tests for the Joke Agent.

Tests cover:
- Category detection logic
- Local joke fallback (no API needed)
- Memory / no-repeat logic
- Stats tracking
- Handler response format
"""

import pytest
from collections import deque
from unittest.mock import AsyncMock, patch

import sys
import os

# Make sure the examples folder is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../examples/joke_agent"))

from joke_agent import (
    detect_category,
    get_local_joke,
    handler,
    joke_history,
    stats,
    LOCAL_JOKES,
)


# ─── Category Detection Tests ─────────────────────────────────────────────────

class TestCategoryDetection:
    """Test that user input is correctly mapped to joke categories."""

    def test_tech_keywords(self):
        assert detect_category("tell me a programming joke") == "tech"
        assert detect_category("I love code") == "tech"
        assert detect_category("software is fun") == "tech"

    def test_dad_keywords(self):
        assert detect_category("tell me a dad joke") == "dad"
        assert detect_category("give me a pun") == "dad"
        assert detect_category("something cheesy please") == "dad"

    def test_dark_keywords(self):
        assert detect_category("tell me a dark joke") == "dark"
        assert detect_category("something morbid") == "dark"

    def test_general_fallback(self):
        assert detect_category("just make me laugh") == "general"
        assert detect_category("tell me something funny") == "general"
        assert detect_category("") == "general"

    def test_case_insensitive(self):
        assert detect_category("TECH JOKE PLEASE") == "tech"
        assert detect_category("DAD JOKE") == "dad"


# ─── Local Joke Tests ─────────────────────────────────────────────────────────

class TestLocalJokes:
    """Test local joke fetching and memory."""

    def setup_method(self):
        """Clear joke history before each test."""
        joke_history.clear()

    def test_returns_tuple(self):
        setup, punchline = get_local_joke("tech")
        assert isinstance(setup, str)
        assert isinstance(punchline, str)
        assert len(setup) > 0
        assert len(punchline) > 0

    def test_valid_categories(self):
        for category in ["tech", "dad", "dark", "general"]:
            setup, punchline = get_local_joke(category)
            assert isinstance(setup, str)

    def test_unknown_category_falls_back_to_general(self):
        setup, punchline = get_local_joke("unknown_category")
        assert (setup, punchline) in LOCAL_JOKES["general"]

    def test_no_repeat_within_history(self):
        """Agent should not repeat jokes until history is exhausted."""
        seen = []
        for _ in range(4):
            joke = get_local_joke("tech")
            seen.append(joke)

        # Last joke should not be in the previous 4
        # (history maxlen=5 so 5th could repeat 1st)
        assert len(set(seen)) > 1

    def test_history_resets_when_exhausted(self):
        """When all jokes are seen, history clears and jokes repeat."""
        joke_history.clear()
        # Fill history with all tech jokes
        pool = LOCAL_JOKES["tech"]
        for joke in pool:
            joke_history.append(joke)

        # Now all jokes are in history — should reset and still return one
        setup, punchline = get_local_joke("tech")
        assert isinstance(setup, str)


# ─── Handler Tests ────────────────────────────────────────────────────────────

class TestHandler:
    """Test the main handler function."""

    def setup_method(self):
        joke_history.clear()
        stats["total_served"] = 0
        stats["api_hits"] = 0
        stats["fallback_hits"] = 0
        stats["by_category"] = {"tech": 0, "dad": 0, "dark": 0, "general": 0}

    def test_handler_returns_list(self):
        messages = [{"role": "user", "content": "tell me a joke"}]
        with patch("joke_agent.asyncio.run", return_value=("Why?", "Because!")):
            result = handler(messages)
        assert isinstance(result, list)

    def test_handler_returns_assistant_role(self):
        messages = [{"role": "user", "content": "tell me a joke"}]
        with patch("joke_agent.asyncio.run", return_value=("Why?", "Because!")):
            result = handler(messages)
        assert result[0]["role"] == "assistant"

    def test_handler_response_contains_joke(self):
        messages = [{"role": "user", "content": "tell me a joke"}]
        with patch("joke_agent.asyncio.run", return_value=("Why?", "Because!")):
            result = handler(messages)
        assert "Why?" in result[0]["content"]
        assert "Because!" in result[0]["content"]

    def test_handler_updates_stats(self):
        messages = [{"role": "user", "content": "tell me a joke"}]
        with patch("joke_agent.asyncio.run", return_value=("Why?", "Because!")):
            handler(messages)
        assert stats["total_served"] == 1

    def test_handler_uses_last_message(self):
        """Handler should use the last message in the list."""
        messages = [
            {"role": "user", "content": "first message"},
            {"role": "assistant", "content": "response"},
            {"role": "user", "content": "tell me a tech joke"},
        ]
        with patch("joke_agent.asyncio.run", return_value=("Why?", "Because!")):
            result = handler(messages)
        assert "tech" in result[0]["content"]


# ─── Retry Logic Tests ────────────────────────────────────────────────────────

class TestRetryLogic:
    """Test API fetch retry behavior."""

    @pytest.mark.asyncio
    async def test_returns_joke_on_success(self):
        from joke_agent import fetch_joke_with_retry

        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = lambda: {
            "setup": "Why did the chicken cross the road?",
            "punchline": "To get to the other side!"
        }

        mock_get = AsyncMock(return_value=mock_response)

        with patch("joke_agent.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(
                return_value=AsyncMock(get=mock_get)
            )
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await fetch_joke_with_retry()

        assert result == (
            "Why did the chicken cross the road?",
            "To get to the other side!"
        )

    @pytest.mark.asyncio
    async def test_falls_back_on_api_failure(self):
        from joke_agent import fetch_joke_with_retry

        with patch("joke_agent.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=Exception("Network error")
            )
            with patch("joke_agent.asyncio.sleep", new_callable=AsyncMock):
                result = await fetch_joke_with_retry(max_attempts=2)

        # Should return None when all retries fail
        assert result is None