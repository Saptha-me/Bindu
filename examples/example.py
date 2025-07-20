from pebbling.agent import pebblify, run_agent
from pebbling.protocol.types import RunMode

from agno.agent import Agent
from agno.models.openai import OpenAIChat

@pebblify(expose=True)
def news_reporter():
    agent = Agent(
        model=OpenAIChat(id="gpt-4o"),
        instructions="You are a news reporter with a flair for storytelling.",
        markdown=True
    )
    return agent



# @pebble_agent(expose=True)
# def editor():
#     return Agent(
#         model=OpenAIChat(id="gpt-4o"),
#         instructions="You are an editor who reviews and improves news stories.",
#         markdown=True
#     )

# User code is now simpler - communication is handled internally
async def main():
    reporter = news_reporter()
    story = await run_agent(
        reporter.pebble_did, 
        "Write a short story about AI"
    )
    # editor_agent = editor()
    
    # Simple message passing with automatic secure channels
    # story = await reporter.run("Write a short story about AI")
    # edited_story = await editor_agent.run("Improve the story: " + story)
    
    print(f"Original story: {story}")
    # print(f"Edited story: {edited_story}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())