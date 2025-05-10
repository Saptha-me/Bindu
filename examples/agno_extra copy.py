from pydantic import BaseModel, Field
import re
from abc import ABC, abstractmethod
from enum import Enum

import litellm

MODEL = "openai/gpt-4o-mini"
MAX_TOKENS = 500


class AgentName(Enum):
    PROPONENT = "proponent"
    OPPONENT = "opponent"
    NEUTRAL = "neutral"

# System prompts for the agents (Same as the 1st example)
PRO_AGENT_INSTRUCTIONS = (
    "You are an agent debating with other agents about a proposition that you agree with: {proposition}."
    "Start your response with 'Proponent:'. Limit your response to 1-2 sentences mimicking a real person."
    "After you respond, you can transition to the next agent by saying either 'Transition to opponent' or 'Transition to neutral'."
)

CON_AGENT_INSTRUCTIONS = (
    "You are an agent debating with other agents about a proposition that you disagree with: {proposition}."
    "Start your response with 'Opponent:'. Limit your response to 1-2 sentences mimicking a real person."
    "After you respond, you can transition to the next agent by saying either 'Transition to proponent' or 'Transition to neutral'."
)

NEUTRAL_AGENT_INSTRUCTIONS = (
    "You are an agent debating with other agents about a proposition that you feel neutral about: {proposition}."
    "Start your response with 'Neutral:'. Limit your response to 1-2 sentences mimicking a real person."
    "After you respond, you can transition to the next agent by saying either 'Transition to proponent' or 'Transition to opponent'."
)


class DebateContext:
    def __init__(
        self,
        proposition: str,
        curr_agent: AgentName,
        agents_registry: dict[AgentName, any],
    ) -> None:
        self.proposition = proposition

        self.agents_registry = agents_registry
        for agent in self.agents_registry.values():
            agent.context = self

        self.curr_agent = self.agents_registry[curr_agent.value]
        self.messages = []

    def run(self):
        self.curr_agent.debate()

class AgentInterface(ABC):
    def __init__(self, name: str, instructions: str) -> None:
        super().__init__()
        self.name = name
        self.instructions = instructions
        self._context = None

    @property
    def messages(self) -> list[dict]:
        """
        The messages history is the system prompt plus the messages from the previous debates.
        The system prompt defines the agent's role and its proposition.
        """
        return [
            {"role": "system", "content": self.instructions}
        ] + self.context.messages

    @property
    def context(self) -> DebateContext:
        return self._context

    @context.setter
    def context(self, context: DebateContext) -> None:
        self._context = context

    @abstractmethod
    def debate(self) -> str:
        pass


class DebateResponse(BaseModel):
    response: str = Field(
        description="The debate response based on the previous debate history."
    )
    next_agent_name: AgentName = Field(
        description="The next agent name to transition to. Always transition to a different agent."
    )


class Agent(AgentInterface):
    def __init__(self, name: str, instructions: str) -> None:
        super().__init__(name, instructions)

    def debate(self) -> str:
        response = litellm.completion(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            messages=self.messages,
            response_format=DebateResponse,
        )

        # State transition using structured output
        parsed_response = DebateResponse.model_validate_json(
            response.choices[0].message.content
        )
        content = parsed_response.response
        next_agent_name = parsed_response.next_agent_name.value

        print(f"{content}")
        print("-" * 100)

        # Update the messages history and transition to the next agent
        self.context.messages.append({"role": "assistant", "content": f"{content}"})
        self.context.curr_agent = self.context.agents_registry[next_agent_name]

        return content


def run_debate(
    agents_registry: dict[AgentName, Agent],
    proposition: str,
    max_turns: int = 10,
) -> None:
    context = DebateContext(
        proposition, curr_agent=AgentName.PROPONENT, agents_registry=agents_registry
    )

    print(f"\nStarting debate on proposition: {proposition}\n")
    print("=" * 100)
    while len(context.messages) < max_turns:
        context.run()
if __name__ == "__main__":
    proposition = (
        "Artificial intelligence should be allowed to make moral decisions in"
        "situations where humans fail to agree."
    )
    agents_registry = {
        AgentName.PROPONENT.value: Agent(
            name="Proponent",
            instructions=PRO_AGENT_INSTRUCTIONS.format(proposition=proposition),
        ),
        AgentName.OPPONENT.value: Agent(
            name="Opponent",
            instructions=CON_AGENT_INSTRUCTIONS.format(proposition=proposition),
        ),
        AgentName.NEUTRAL.value: Agent(
            name="Neutral",
            instructions=NEUTRAL_AGENT_INSTRUCTIONS.format(proposition=proposition),
        ),
    }

    run_debate(agents_registry, proposition, max_turns=10)