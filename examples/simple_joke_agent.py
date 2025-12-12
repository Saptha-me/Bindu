"""
Simple Joke Agent - Bindu Example
==================================

A minimal example showing how to create a Bindu agent that tells programming jokes.

This demonstrates:
- Basic agent setup with Bindu
- Simple configuration
- Handler function pattern
- Local deployment

Perfect for first-time Bindu users!

Usage:
    python examples/simple_joke_agent.py

Then visit: http://localhost:3774/docs to interact with the agent

Author: Shaikh Aman <shaikhamanksf@gmail.com>
"""

from bindu.penguin.bindufy import bindufy
import random

# Collection of programming jokes
PROGRAMMING_JOKES = [
    "Why do programmers prefer dark mode? Because light attracts bugs!",
    "How many programmers does it take to change a light bulb? None, that's a hardware problem!",
    "Why do Java developers wear glasses? Because they don't C#!",
    "What's a programmer's favorite hangout place? Foo Bar!",
    "Why did the programmer quit his job? Because he didn't get arrays!",
    "How do you comfort a JavaScript bug? You console it!",
    "Why do programmers always mix up Halloween and Christmas? Because Oct 31 == Dec 25!",
    "What do you call a programmer from Finland? Nerdic!",
    "Why did the programmer go broke? Because he used up all his cache!",
    "What's a programmer's favorite snack? Microchips!"
]

# Agent configuration
config = {
    "author": "shaikhamanksf@gmail.com",  
    "name": "joke_agent",
    "description": "A friendly agent that tells programming jokes on demand",
    "version": "1.0.0",
    "deployment": {
        "url": "http://localhost:3774",  # Different port from test agent
        "expose": True
    }
}


def handler(messages: list[dict[str, str]]) -> dict:
    """
    Process incoming messages and return jokes.
    
    This handler checks if the user is asking for a joke and returns
    a random programming joke from the collection.
    
    Args:
        messages (list[dict]): List of message dictionaries containing:
            - role: 'user' or 'assistant'
            - content: The message text
            
    Returns:
        dict: Response containing the joke or a greeting
        
    Example:
        >>> handler([{"role": "user", "content": "Tell me a joke"}])
        {"content": "Why do programmers prefer dark mode? ..."}
    """
    # Handle empty messages
    if not messages:
        return {
            "content": "Hi! I'm the Joke Agent! 🎭\n\nAsk me for a programming joke!"
        }
    
    # Get the last message from the user
    last_message = messages[-1].get("content", "").lower()
    
    # Check if user is requesting a joke
    joke_keywords = ["joke", "funny", "laugh", "humor", "make me laugh"]
    
    if any(keyword in last_message for keyword in joke_keywords):
        # Return a random joke
        joke = random.choice(PROGRAMMING_JOKES)
        return {
            "content": f"🎭 Here's one for you:\n\n{joke}\n\n😄 Want another? Just ask for another joke!"
        }
    
    # Default response for other queries
    return {
        "content": "Hi! I specialize in programming jokes. 🎭\n\nTry asking me:\n- 'Tell me a joke'\n- 'Make me laugh'\n- 'I need something funny'"
    }


if __name__ == "__main__":
    print("\n" + "="*60)
    print("🎭 STARTING JOKE AGENT")
    print("="*60)
    print(f"\n✅ Agent will be available at: {config['deployment']['url']}")
    print(f"✅ Visit the docs: {config['deployment']['url']}/docs")
    print(f"✅ Test it in your browser!")
    print("\n" + "="*60)
    print("💡 TIP: Open http://localhost:3774/docs in your browser")
    print("="*60 + "\n")
    
    # Bindu-fy the agent!
    bindufy(config, handler)