"""Joke Agent - Engineered Version

A stateful Bindu agent that tells categorized jokes with memory,
retry logic, observability, and graceful fallback.

Features:
- Category detection from user input (tech, dad, dark, general)
- Memory: never repeats the last 5 jokes
- Retry with exponential backoff + jitter
- Structured logging for observability
- Graceful fallback to local jokes if API fails
- No API key required

Usage:
    python examples/joke_agent/joke_agent.py
"""

import asyncio
import random
import logging
from collections import deque

import httpx

from bindu.penguin.bindufy import bindufy

# ─── Logging / Observability ─────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("joke_agent")

# ─── Stats tracker ───────────────────────────────────────────────────────────

stats = {
    "total_served": 0,
    "api_hits": 0,
    "fallback_hits": 0,
    "by_category": {"tech": 0, "dad": 0, "dark": 0, "general": 0},
}

# ─── Memory: avoid repeating last 5 jokes ────────────────────────────────────

joke_history: deque = deque(maxlen=5)

# ─── Local joke dataset (fallback + category support) ────────────────────────

LOCAL_JOKES = {
    "tech": [
        ("Why do programmers prefer dark mode?", "Because light attracts bugs!"),
        ("Why did the developer go broke?", "Because he used up all his cache!"),
        ("How do you comfort a JavaScript bug?", "You console it!"),
        ("Why do Java developers wear glasses?", "Because they don't C#!"),
        ("What is a computer's favourite snack?", "Microchips!"),
        ("Why was the function sad?", "Because it didn't get called!"),
        ("What do you call 8 hobbits?", "A hobbyte!"),
    ],
    "dad": [
        ("Why don't scientists trust atoms?", "Because they make up everything!"),
        ("Did you hear about the claustrophobic astronaut?", "He just needed a little space!"),
        ("Why can't you give Elsa a balloon?", "Because she'll let it go!"),
        ("What do you call cheese that isn't yours?", "Nacho cheese!"),
        ("Why did the scarecrow win an award?", "Because he was outstanding in his field!"),
    ],
    "dark": [
        ("Why don't graveyards ever get crowded?", "Because people are dying to get in!"),
        ("What's the best part about living in Switzerland?", "Well, the flag is a big plus!"),
        ("I told my doctor I broke my arm in two places.", "He told me to stop going to those places!"),
    ],
    "general": [
        ("Why did the bicycle fall over?", "Because it was two-tired!"),
        ("What do you call a fake noodle?", "An impasta!"),
        ("Why did the math book look so sad?", "Because it had too many problems!"),
        ("What do you call a sleeping dinosaur?", "A dino-snore!"),
    ],
}


# ─── Category detection ───────────────────────────────────────────────────────

def detect_category(user_input: str) -> str:
    """Detect joke category from user message.

    Args:
        user_input: Raw user message string

    Returns:
        Category string: 'tech', 'dad', 'dark', or 'general'
    """
    text = user_input.lower()

    if any(word in text for word in ["tech", "code", "programming", "developer", "software", "computer"]):
        return "tech"
    elif any(word in text for word in ["dad", "father", "pun", "cheesy"]):
        return "dad"
    elif any(word in text for word in ["dark", "morbid", "twisted"]):
        return "dark"
    else:
        return "general"


# ─── Joke fetching with retry ─────────────────────────────────────────────────

async def fetch_joke_with_retry(max_attempts: int = 3) -> tuple[str, str] | None:
    """Fetch a joke from the public API with retry + exponential backoff + jitter.

    Args:
        max_attempts: Maximum retry attempts before giving up

    Returns:
        Tuple of (setup, punchline) or None if all attempts fail
    """
    for attempt in range(max_attempts):
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    "https://official-joke-api.appspot.com/random_joke"
                )
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"API joke fetched successfully (attempt {attempt + 1})")
                    return data["setup"], data["punchline"]

                wait = (2 ** attempt) + random.uniform(0, 1)
                logger.warning(f"API returned {response.status_code}, retrying in {wait:.1f}s")
                await asyncio.sleep(wait)

        except Exception as e:
            wait = (2 ** attempt) + random.uniform(0, 1)
            logger.warning(f"API error on attempt {attempt + 1}: {e}. Retrying in {wait:.1f}s")
            if attempt < max_attempts - 1:
                await asyncio.sleep(wait)

    logger.error("All API attempts failed. Falling back to local jokes.")
    return None


def get_local_joke(category: str) -> tuple[str, str]:
    """Get a non-repeated local joke for the given category.

    Args:
        category: Joke category

    Returns:
        Tuple of (setup, punchline)
    """
    pool = LOCAL_JOKES.get(category, LOCAL_JOKES["general"])

    # Filter out recently told jokes
    available = [j for j in pool if j not in joke_history]

    # If all jokes have been told recently, reset and use full pool
    if not available:
        logger.info("All jokes in category seen recently, resetting history.")
        joke_history.clear()
        available = pool

    joke = random.choice(available)
    joke_history.append(joke)
    return joke


# ─── Main handler ─────────────────────────────────────────────────────────────

def handler(messages: list[dict]) -> list[dict]:
    """Process incoming messages and respond with a categorized joke.

    Args:
        messages: List of message dicts with 'role' and 'content' keys

    Returns:
        List containing the assistant's joke response
    """
    user_message = messages[-1]["content"]
    category = detect_category(user_message)

    logger.info(f"Request received | category='{category}' | message='{user_message[:50]}'")

    # Try API first, fall back to local
    api_result = asyncio.run(fetch_joke_with_retry())

    if api_result:
        setup, punchline = api_result
        source = "api"
        stats["api_hits"] += 1
    else:
        setup, punchline = get_local_joke(category)
        source = "local"
        stats["fallback_hits"] += 1

    # Update stats
    stats["total_served"] += 1
    stats["by_category"][category] += 1

    logger.info(
        f"Joke served | source={source} | category={category} | "
        f"total_served={stats['total_served']}"
    )

    response = (
        f"😄 Here's a **{category}** joke for you!\n\n"
        f"**{setup}**\n\n"
        f"...{punchline} 🥁"
    )

    return [{"role": "assistant", "content": response}]


# ─── Bindu config ─────────────────────────────────────────────────────────────

config = {
    "author": "kartiklahare122@gmail.com",
    "name": "joke_agent",
    "description": (
        "A stateful joke agent with category detection, memory, "
        "retry logic, and observability. No API key required."
    ),
    "deployment": {
        "url": "http://localhost:3773",
        "expose": True,
        "cors_origins": ["http://localhost:5173"],
    },
    "skills": [],
}

if __name__ == "__main__":
    bindufy(config, handler)