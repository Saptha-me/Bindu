# Copyright 2025 BeeAI a Series of LF Projects, LLC
# SPDX-License-Identifier: Apache-2.0

import abc
import inspect
from collections.abc import AsyncGenerator, Coroutine, Generator
from typing import Any, Callable


class AgentManifest(abc.ABC):
    @property
    def name(self) -> str:
        return self.__class__.__name__

    @property
    def description(self) -> str:
        return ""

    @property
    def input_content_types(self) -> list[str]:
        return []

    @property
    def output_content_types(self) -> list[str]:
        return []

    @property
    def metadata(self) -> dict[str, Any]:
        return {}
        
    @property
    def capabilities(self) -> dict[str, Any]:
        """Agent capabilities like streaming, state history, etc."""
        return {}
        
    @property
    def skills(self) -> list[dict[str, Any]]:
        """List of skills the agent supports."""
        return []

    #@abc.abstractmethod
    # def run(
    #     self, input: list[Message], context: dict[str, Any]
    # ) -> (
    #     AsyncGenerator[RunYield, RunYieldResume] | Generator[RunYield, RunYieldResume] | Coroutine[RunYield] | RunYield
    # ):
    #     pass


Agent = AgentManifest


def agent(
    name: str | None = None,
    description: str | None = None,
    *,
    metadata: dict[str, Any] | None = None,
    input_content_types: list[str] | None = None,
    output_content_types: list[str] | None = None,
) -> Callable[[Callable], AgentManifest]:
    """Decorator to create an agent."""

    def decorator(fn: Callable) -> AgentManifest:
        signature = inspect.signature(fn)
        parameters = list(signature.parameters.values())

        if len(parameters) == 0:
            raise TypeError("The agent function must have at least 'input' argument")
        if len(parameters) > 2:
            raise TypeError("The agent function must have only 'input' and 'context' arguments")
        if len(parameters) == 2 and parameters[1].name != "context":
            raise TypeError("The second argument of the agent function must be 'context'")

        has_context_param = len(parameters) == 2

        class DecoratorAgentBase(AgentManifest):
            @property
            def name(self) -> str:
                return name or fn.__name__

            @property
            def description(self) -> str:
                return description or inspect.getdoc(fn) or ""

            @property
            def metadata(self) -> dict[str, Any]:
                return metadata or {}

            @property
            def input_content_types(self) -> list[str]:
                return input_content_types or ["*/*"]

            @property
            def output_content_types(self) -> list[str]:
                return output_content_types or ["*/*"]

        agent: AgentManifest
        if inspect.isasyncgenfunction(fn):

            class AsyncGenDecoratorAgent(DecoratorAgentBase):
                async def run(self, input: list[Message], context: Context) -> AsyncGenerator[RunYield, RunYieldResume]:
                    try:
                        gen: AsyncGenerator[RunYield, RunYieldResume] = (
                            fn(input, context) if has_context_param else fn(input)
                        )
                        value = None
                        while True:
                            value = yield await gen.asend(value)
                    except StopAsyncIteration:
                        pass

            agent = AsyncGenDecoratorAgent()
        elif inspect.iscoroutinefunction(fn):

            class CoroDecoratorAgent(DecoratorAgentBase):
                async def run(self, input: list[Message], context: Context) -> Coroutine[RunYield]:
                    return await (fn(input, context) if has_context_param else fn(input))

            agent = CoroDecoratorAgent()
        elif inspect.isgeneratorfunction(fn):

            class GenDecoratorAgent(DecoratorAgentBase):
                def run(self, input: list[Message], context: Context) -> Generator[RunYield, RunYieldResume]:
                    yield from (fn(input, context) if has_context_param else fn(input))

            agent = GenDecoratorAgent()
        else:

            class FuncDecoratorAgent(DecoratorAgentBase):
                def run(self, input: list[Message], context: Context) -> RunYield:
                    return fn(input, context) if has_context_param else fn(input)

            agent = FuncDecoratorAgent()

        return agent

    return decorator
