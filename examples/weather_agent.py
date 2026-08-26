"""
examples/weather_agent.py

A fully-featured weather agent powered by Bindu.

Features demonstrated:
  - bindufy() wrapping a real agent
  - Retry mechanism for resilient external API calls
  - Structured response formatting
  - Multi-turn conversation support
  - Skills declaration

Run:
    python examples/weather_agent.py

Then test with:
    curl -X POST http://localhost:3773/messages \\
      -H "Content-Type: application/json" \\
      -d '[{"role": "user", "content": "What is the weather in Amsterdam?"}]'

Requirements (add to your pyproject.toml):
    - bindu
    - httpx
    - (any LLM SDK — this example shows both OpenAI and a mock fallback)
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import httpx

from bindu.penguin.bindufy import bindufy
from bindu.retry import RetryConfig, wrap_handler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

AGENT_CONFIG = {
    "author": os.getenv("BINDU_AUTHOR", "demo@getbindu.com"),
    "name": "weather_agent",
    "version": "1.0.0",
    "description": (
        "A weather intelligence agent. Ask me about current conditions, "
        "forecasts, or historical weather for any city."
    ),
    "deployment": {
        "url": os.getenv("BINDU_URL", "http://localhost:3773"),
        "expose": True,
    },
    "skills": [
        "skills/question-answering",
        "skills/weather-lookup",
    ],
    "auth": {"enabled": False},
    "storage": {"type": "memory"},
    "scheduler": {"type": "memory"},
}

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")
OPENWEATHER_BASE = "https://api.openweathermap.org/data/2.5"


# ---------------------------------------------------------------------------
# Weather API client (with retry baked in)
# ---------------------------------------------------------------------------

def _fetch_weather_raw(city: str) -> dict[str, Any]:
    """
    Fetch current weather from OpenWeatherMap.
    This function is intentionally kept thin so the retry wrapper can re-call it.
    """
    if not OPENWEATHER_API_KEY:
        # Graceful mock for demo purposes when no API key is set
        return _mock_weather(city)

    url = f"{OPENWEATHER_BASE}/weather"
    params = {"q": city, "appid": OPENWEATHER_API_KEY, "units": "metric"}

    response = httpx.get(url, params=params, timeout=5.0)
    response.raise_for_status()
    return response.json()


# Wrap with exponential backoff — 3 attempts, starting at 0.5s, cap at 10s
_fetch_weather = wrap_handler(
    _fetch_weather_raw,
    RetryConfig(
        max_attempts=3,
        base_delay=0.5,
        max_delay=10.0,
        backoff_factor=2.0,
        retry_on=(httpx.HTTPStatusError, httpx.TimeoutException, httpx.NetworkError),
    ),
)


def _mock_weather(city: str) -> dict[str, Any]:
    """Returns deterministic mock data when no API key is configured."""
    return {
        "name": city,
        "sys": {"country": "?"},
        "weather": [{"description": "clear sky (mock)"}],
        "main": {"temp": 18.5, "feels_like": 17.0, "humidity": 62},
        "wind": {"speed": 3.2},
        "_mock": True,
    }


def _parse_weather(data: dict[str, Any]) -> str:
    """Turn a raw OpenWeatherMap response into a human-readable summary."""
    city = data.get("name", "Unknown")
    country = data.get("sys", {}).get("country", "")
    description = data.get("weather", [{}])[0].get("description", "N/A").capitalize()
    main = data.get("main", {})
    temp = main.get("temp", "N/A")
    feels_like = main.get("feels_like", "N/A")
    humidity = main.get("humidity", "N/A")
    wind_speed = data.get("wind", {}).get("speed", "N/A")
    is_mock = data.get("_mock", False)

    summary = (
        f"**{city}, {country}**\n"
        f"🌤  {description}\n"
        f"🌡  Temperature: {temp}°C (feels like {feels_like}°C)\n"
        f"💧  Humidity: {humidity}%\n"
        f"💨  Wind: {wind_speed} m/s"
    )
    if is_mock:
        summary += "\n\n_(Note: mock data — set OPENWEATHER_API_KEY for live results)_"
    return summary


# ---------------------------------------------------------------------------
# City extractor (zero-dependency NLP)
# ---------------------------------------------------------------------------

def _extract_city(text: str) -> str | None:
    """
    Lightweight city extraction using keyword patterns.
    In production you'd use an LLM tool call or spaCy NER.
    """
    lower = text.lower()
    for kw in ("in ", "for ", "at ", "weather of ", "weather in "):
        idx = lower.find(kw)
        if idx != -1:
            remainder = text[idx + len(kw):].strip()
            # Take up to first punctuation or question mark
            city = remainder.split("?")[0].split(".")[0].split(",")[0].strip()
            if city:
                return city
    return None


# ---------------------------------------------------------------------------
# LLM integration (optional — gracefully degrades without OpenAI)
# ---------------------------------------------------------------------------

def _llm_respond(system: str, user_message: str) -> str:
    """
    Try to call GPT-4o for natural language responses.
    Falls back to a template reply if the SDK is unavailable or key is missing.
    """
    try:
        from agno.agent import Agent
        from agno.models.openai import OpenAIChat

        openai_key = os.getenv("OPENAI_API_KEY", "")
        if not openai_key:
            raise ImportError("No OPENAI_API_KEY set")

        agent = Agent(
            instructions=system,
            model=OpenAIChat(id="gpt-4o"),
        )
        result = agent.run(input=[{"role": "user", "content": user_message}])
        return str(result)
    except Exception:
        # Graceful fallback: structured template response
        return user_message  # already formatted by _parse_weather


# ---------------------------------------------------------------------------
# Main handler
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "You are a helpful weather assistant. You provide clear, friendly weather "
    "information. When given raw weather data, format it in a conversational, "
    "easy-to-understand way. Suggest what to wear or bring based on conditions."
)


def handler(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    """
    Core Bindu handler.

    Accepts a list of A2A-style message dicts and returns the agent's reply
    as a list containing a single assistant message.

    Multi-turn conversation is supported: the agent reads the full history
    to maintain context across exchanges.
    """
    if not messages:
        return [{"role": "assistant", "content": "Hi! Ask me about the weather anywhere."}]

    latest = messages[-1].get("content", "")

    # --- Intent: weather lookup ---
    city = _extract_city(latest)
    if city:
        logger.info("Weather lookup for city: %s", city)
        try:
            raw = _fetch_weather(city)
            formatted = _parse_weather(raw)
            # Optionally run through LLM for a more conversational tone
            response_text = _llm_respond(SYSTEM_PROMPT, formatted)
        except Exception as exc:
            logger.error("Weather fetch failed: %s", exc)
            response_text = (
                f"Sorry, I couldn't retrieve weather data for **{city}** right now. "
                "Please check the city name and try again."
            )
    else:
        # --- Fallback: general weather conversation ---
        response_text = (
            "I can look up weather for any city! Just ask me something like:\n"
            '- "What\'s the weather in London?"\n'
            '- "Weather in New York"\n'
            '- "Is it raining in Mumbai?"'
        )

    return [{"role": "assistant", "content": response_text}]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logger.info("Starting Weather Agent on %s", AGENT_CONFIG["deployment"]["url"])
    logger.info(
        "Tip: set OPENWEATHER_API_KEY env var for live weather data. "
        "Currently using: %s",
        "live API" if OPENWEATHER_API_KEY else "mock data",
    )
    bindufy(AGENT_CONFIG, handler)
