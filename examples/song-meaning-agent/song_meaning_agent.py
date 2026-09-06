"""
Song Meaning Analyzer — Bindu Example

An expert agent that deeply researches songs, lyrics, artists, and context
to uncover and articulate the true meaning behind any musical work.

Prerequisites
-------------
    uv add bindu agno python-dotenv

Usage
-----
    export OPENROUTER_API_KEY="your_api_key_here"  # pragma: allowlist secret
    python song_meaning_agent.py

The agent will be live at http://localhost:3773
Send it a message like:
    {"role": "user", "content": "What does 'Bohemian Rhapsody' really mean?"}
or:
    {"role": "user", "content": "Analyze the meaning of 'The Sound of Silence' by Simon & Garfunkel"}
"""

import os

from agno.agent import Agent
from agno.models.openrouter import OpenRouter
from bindu.penguin.bindufy import bindufy
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# 1. Agent definition
# ---------------------------------------------------------------------------

INSTRUCTIONS = """
You are an expert songwriter, musicologist, and cultural analyst with deep knowledge
of music history, lyrical symbolism, and artistic context across all genres and eras.

When asked to analyze a song, you MUST follow this exact structure:

**SUMMARY**
A single sentence (25 words max) capturing the song's core meaning.

**MEANING**
3–5 bullet points (each ~65 words) exploring:
- Central themes and emotional narrative
- Symbolic imagery and metaphors used
- Cultural, historical, or biographical context
- The artist's intent or stated interpretation (if known)
- How the musical elements reinforce the lyrical meaning

**EVIDENCE**
3–5 bullet points (each ~15 words) citing:
- Specific lyrics that support your interpretation
- Artist interviews, liner notes, or documented statements
- Fan analysis or cultural reception where relevant

Rules:
- Output in plain Markdown without bold or italics inside bullet points
- Be evidence-based: ground every claim in lyrics, artist statements, or documented context
- If the song or artist is unfamiliar, say so clearly rather than speculating
- Cover multiple interpretations when the song is genuinely ambiguous
""".strip()

agent = Agent(
    instructions=INSTRUCTIONS,
    model=OpenRouter(
        id="openai/gpt-4o-mini",
        api_key=os.getenv("OPENROUTER_API_KEY"),  # pragma: allowlist secret
    ),
    markdown=True,
)


# ---------------------------------------------------------------------------
# 2. Bindu configuration
# ---------------------------------------------------------------------------

config = {
    "author": "your.email@example.com",
    "name": "song_meaning_agent",
    "description": (
        "An expert songwriter and musician that deeply researches songs, lyrics, "
        "artists, and context to uncover and articulate the true meaning behind "
        "any musical work."
    ),
    "version": "1.0.0",
    "capabilities": {
        "text_analysis": ["lyric-interpretation", "thematic-extraction", "musical-symbolism"],
        "research": ["artist-context-research", "evidence-based-conclusion"],
        "streaming": False,
    },
    "skills": ["skills/song-meaning-skill"],
    "auth": {"enabled": False},
    "storage": {"type": "memory"},
    "scheduler": {"type": "memory"},
    "deployment": {
        "url": os.getenv("BINDU_DEPLOYMENT_URL", "http://localhost:3773"),
        "expose": True,
        "cors_origins": ["http://localhost:5173"],
    },
}


# ---------------------------------------------------------------------------
# 3. Handler
# ---------------------------------------------------------------------------

def _message_text(message: dict) -> str:
    """Extract text from an A2A message.

    The text lives in message parts. Falls back to "content" so the example
    also works against older bindu releases that flattened history to chat
    format.
    """
    text = " ".join(
        p.get("text", "") for p in message.get("parts", []) if p.get("kind") == "text"
    )
    return text or message.get("content", "")


def handler(messages: list[dict[str, str]]):
    """Analyze the meaning of a song based on the user's query.

    Args:
        messages: Standard A2A message list, e.g.
                  [{"role": "user", "content": "What does Bohemian Rhapsody mean?"}]

    Returns:
        Structured song meaning analysis with SUMMARY, MEANING, and EVIDENCE sections.
    """
    try:
        user_messages = [m for m in messages if m.get("role") == "user"]
        if not user_messages:
            return "No query received. Please ask about a song, e.g. 'What does Bohemian Rhapsody mean?'"

        query = _message_text(user_messages[-1]).strip()
        if not query:
            return "Empty query. Please name a song or paste lyrics you'd like analyzed."

        # Flatten the history to chat format for the agno agent.
        chat_messages = []
        for m in messages:
            text = _message_text(m)
            if not text:
                continue
            role = "user" if m.get("role") == "user" else "assistant"
            chat_messages.append({"role": role, "content": text})

        result = agent.run(input=chat_messages)
        return result

    except Exception as e:
        return f"Error analyzing song: {str(e)}"


# ---------------------------------------------------------------------------
# 4. Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("🎵 Song Meaning Analyzer running at http://localhost:3773")
    print("🎸 Example: {\"role\": \"user\", \"content\": \"What does Bohemian Rhapsody really mean?\"}")
    bindufy(config, handler)
