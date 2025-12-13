from bindu.penguin.bindufy import bindufy

def handler(messages):
    # Simple agent that responds with its identity and echoes the message
    response = f"I am a simple Bindu agent. You said: {messages[-1]['content']}"
    return [{"role": "assistant", "content": response}]

config = {
    "author": "your.email@example.com",
    "name": "identity_agent",
    "description": "A simple agent that identifies itself and echoes messages.",
    "deployment": {"url": "http://localhost:3775", "expose": True},
    "skills": []
}

bindufy(config, handler)