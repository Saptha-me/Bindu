"""Mock Research Agent for testing the Planner Agent.

Simulates a research/web search agent that can gather information.
"""

from bindu.penguin.bindufy import bindufy


def handler(messages):
    """
    Handle research requests.
    
    Returns mock research results to test orchestration flow.
    """
    user_query = messages[-1]["content"]
    
    # Mock research results
    response = f"""**Research Results:**

Based on your request: "{user_query}"

I found the following key information:

1. **Trend 1:** Large Language Models continue to scale with improved reasoning capabilities
2. **Trend 2:** Multimodal AI combining vision, text, and audio is becoming mainstream
3. **Trend 3:** Agent-based systems and autonomous AI are emerging rapidly

**Sources:**
- Recent papers from arXiv, OpenAI, Anthropic
- Industry reports from 2024

*Note: This is mock data from Research Agent*
"""
    
    return [{
        "role": "assistant",
        "content": response
    }]


config = {
    "author": "prachetdevsingh@gmail.com",
    "name": "research_agent",
    "description": "Performs web research and information gathering",
    "skills": ["skills/research"],
    "deployment": {
        "url": "http://localhost:3775",
        "expose": True,
        "cors_origins": ["http://localhost:5173"]
    }
}

bindufy(config, handler)
