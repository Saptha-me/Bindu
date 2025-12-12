# Bindu Examples

This directory contains example agents demonstrating different Bindu features and use cases.

## 🎯 Available Examples

### 1. Simple Joke Agent (`simple_joke_agent.py`)

A minimal, beginner-friendly example showing the basics of creating a Bindu agent.

**What it does:** Tells programming jokes on request

**What it demonstrates:**
- Basic Bindu configuration structure
- Simple message handler function
- Local deployment setup
- Response formatting
- User input detection

**How to run:**
```bash
# Make sure your virtual environment is activated
python examples/simple_joke_agent.py
```

**How to test:**
1. Run the agent (command above)
2. Open browser: http://localhost:3774/docs
3. Use the Swagger UI to send messages
4. Try asking: "Tell me a joke"

**Perfect for:** 
- First-time Bindu users
- Understanding basic agent structure
- Learning the handler pattern

---

## 🚀 Creating Your Own Example

Want to add your own example agent? Here's the basic structure:
```python
from bindu.penguin.bindufy import bindufy

# 1. Define configuration
config = {
    "author": "your.email@example.com",
    "name": "your_agent_name",
    "description": "What your agent does",
    "version": "1.0.0",
    "deployment": {
        "url": "http://localhost:PORT",  # Use unique port (3775, 3776, etc.)
        "expose": True
    }
}

# 2. Define handler function
def handler(messages: list[dict[str, str]]) -> dict:
    """
    Process messages and return responses.
    
    Args:
        messages: List of message dicts with 'role' and 'content'
        
    Returns:
        dict: Response with 'content' key
    """
    # Your agent logic here
    return {"content": "Your response"}

# 3. Bindu-fy it!
if __name__ == "__main__":
    bindufy(config, handler)
```

## 💡 Tips for Creating Examples

- **Use unique ports** for each agent (3774, 3775, 3776, etc.)
- **Add clear docstrings** explaining what your agent does
- **Include usage examples** in the file header
- **Test thoroughly** before submitting
- **Keep it simple** - examples should be easy to understand
- **Add comments** for non-obvious logic

## 🤝 Contributing Examples

Have an idea for a new example? We'd love to see it! 

Examples we'd like to see:
- Weather information agent
- Calculator/math agent
- Translation agent
- News summary agent
- Code explanation agent

Check out our [Contributing Guide](../.github/contributing.md) to get started!

## 📚 Learning Path

Recommended order for exploring examples:

1. **Start here:** `simple_joke_agent.py` - Learn the basics
2. **Next:** (Add more examples as they're created)
3. **Advanced:** (Add advanced examples as they're created)

## 🆘 Need Help?

- Check the main [README](../README.md)
- Visit [Bindu Documentation](https://docs.getbindu.com)
- Join our [Discord](https://discord.gg/3w5zuYUuwt)
- Open an [Issue](https://github.com/getbindu/Bindu/issues)