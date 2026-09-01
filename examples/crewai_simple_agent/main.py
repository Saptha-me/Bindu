from bindu.penguin.bindufy import bindufy


def handler(messages):
    user_input = messages[-1]["content"]
    
    return [{
        "role": "assistant",
        "content": f"👋 Hello! You said: {user_input}\n\nThis is a simple CrewAI-style agent running on Bindu."
    }]


config = {
    "author": "your_email@example.com",
    "name": "crewai_simple_agent",
    "description": "Beginner-friendly simple agent using Bindu (no API key required)",
    "deployment": {
        "url": "http://localhost:3773",
        "expose": True,
    },
    "skills": []
}


bindufy(config, handler)