"""Mock Summary Agent for testing the Planner Agent.

Simulates a text summarization agent that can condense information.
"""

from bindu.penguin.bindufy import bindufy


def handler(messages):
    """
    Handle summarization requests.
    
    Returns mock summaries to test orchestration flow.
    """
    user_query = messages[-1]["content"]
    
    # Mock summary response
    response = f"""**Summary:**

Based on: "{user_query}"

**Key Points:**
• AI models are getting larger and more capable
• Multimodal systems are becoming standard
• Autonomous agents are a major focus area

**Conclusion:**
The AI landscape in 2024 is characterized by rapid advancement in model capabilities, 
broader multimodal integration, and a shift toward agentic systems that can plan and execute 
complex tasks autonomously.

**Word Count:** ~50 words

*Note: This is mock data from Summary Agent*
"""
    
    return [{
        "role": "assistant",
        "content": response
    }]


config = {
    "author": "prachetdevsingh@gmail.com",
    "name": "summary_agent",
    "description": "Summarizes and condenses text content",
    "skills": ["skills/summarization"],
    "deployment": {
        "url": "http://localhost:3776",
        "expose": True,
        "cors_origins": ["http://localhost:5173"]
    }
}

bindufy(config, handler)
