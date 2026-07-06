"""Medical Research Agent with Web Search.

Run:
    python medical_agent.py
"""

from pathlib import Path

from dotenv import load_dotenv

from agno.agent import Agent
from agno.models.openrouter import OpenRouter
from agno.tools.duckduckgo import DuckDuckGoTools
from bindu.penguin.bindufy import bindufy
from bindu.settings import app_settings

load_dotenv(Path(__file__).parent / ".env")

OPENROUTER_API_KEY = app_settings.OPENROUTER_API_KEY

if not OPENROUTER_API_KEY:
    raise RuntimeError(
        "OPENROUTER_API_KEY is missing. Create a .env file and add your OpenRouter API key."
    )

agent = Agent(
    name="Medical Research Agent",
    instructions="""
You are a medical research assistant.

Your job:
- Provide general health and wellness information.
- Explain symptoms in an educational way.
- Use web search when useful.
- Do not diagnose the user.
- Do not prescribe medication.
- Do not replace a doctor.

Safety rules:
- Always include a clear medical disclaimer.
- For serious symptoms like chest pain, breathing difficulty, severe bleeding,
  fainting, stroke symptoms, severe allergic reaction, or suicidal thoughts,
  advise the user to seek emergency medical help immediately.
- Recommend consulting a qualified healthcare professional for personal diagnosis or treatment.

Response style:
- Be clear and simple.
- Give practical general guidance.
- Mention when urgent care is needed.
- End with: "Disclaimer: This is general health information, not professional medical advice."
""",
    model=OpenRouter(
        id="google/gemini-2.0-flash-001",
        api_key=OPENROUTER_API_KEY,
    ),
    tools=[DuckDuckGoTools()],
    markdown=True,
)

config = {
    "author": "bindu.builder@getbindu.com",
    "name": "medical_agent",
    "description": (
        "A medical research agent that provides general health information, "
        "symptom education, and wellness guidance with safety disclaimers."
    ),
    "deployment": {
        "url": "http://localhost:3773",
        "expose": True,
        "cors_origins": ["http://localhost:5173"],
    },
    "skills": ["skills/medical-research-skill"],
}


def handler(messages: list[dict[str, str]]) -> str:
    """Handle incoming Bindu messages."""
    if not messages:
        return (
            "Please ask a health-related question. "
            "Disclaimer: This is general health information, not professional medical advice."
        )

    latest_message = messages[-1]

    if isinstance(latest_message, dict):
        user_message = latest_message.get("content", "")
    else:
        user_message = latest_message

    user_message = "" if user_message is None else str(user_message)

    if not user_message.strip():
        return (
            "Please provide a health-related question. "
            "Disclaimer: This is general health information, not professional medical advice."
        )

    result = agent.run(input=user_message)

    if hasattr(result, "content"):
        return str(result.content)

    if hasattr(result, "response"):
        return str(result.response)

    return str(result)


if __name__ == "__main__":
    bindufy(config, handler)
