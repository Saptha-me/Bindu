"""
Summarizer Agent

Handles summarization and explanation tasks.
"""

from agno.agent import Agent
from agno.models.openrouter import OpenRouter


class SummarizerAgent:

    def __init__(self):
        self.agent = Agent(
            model=OpenRouter(id="openai/gpt-oss-120b"),
            instructions=(
                "You are a helpful assistant. "
                "If the user asks to summarize, provide a concise summary. "
                "If the user asks to explain a topic, provide a clear explanation."
            ),
        )

    async def run(self, text: str):
        """
        Execute summarization or explanation task.
        """

        try:
            response = self.agent.run(text)

            if response and hasattr(response, "content"):
                return response.content

            return "No response generated."

        except Exception as e:
            return f"Summarizer agent error: {str(e)}"