"""
Translator Agent
"""

from agno.agent import Agent
from agno.models.openrouter import OpenRouter


class TranslatorAgent:

    def __init__(self):
        self.agent = Agent(
            model=OpenRouter(id="openai/gpt-oss-120b"),
            instructions="Translate the given text to Spanish.",
        )

    async def run(self, text: str):
        """
        Execute translation task.
        """

        try:
            response = self.agent.run(text)

            if response and hasattr(response, "content"):
                return response.content

            return "No response generated."

        except Exception as e:
            return f"Translator agent error: {str(e)}"