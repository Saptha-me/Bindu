"""
Orchestrator

Coordinates agent discovery and execution.
Routes user request to the correct agent.
"""

from router_agent import RouterAgent
from summarizer_agent import SummarizerAgent
from translator_agent import TranslatorAgent


class Orchestrator:

    def __init__(self):
        # Initialize router
        self.router = RouterAgent()

        # Initialize available agents
        self.agents = {
            "summarizer_agent": SummarizerAgent(),
            "translator_agent": TranslatorAgent(),
        }

    async def run(self, request: str):
        """
        Main execution function.
        Routes the request to the correct agent and returns the response.
        """

        try:
            # Step 1: Route request to correct agent
            agent_name = self.router.route(request)

            if not agent_name:
                return "No suitable agent found for this request."

            # Step 2: Get agent instance
            agent = self.agents.get(agent_name)

            if not agent:
                return "Selected agent not available."

            # Step 3: Execute agent task
            response = await agent.run(request)

            return response

        except Exception as e:
            return f"Orchestrator error: {str(e)}"