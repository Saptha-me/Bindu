<div align="center" id="top">
  <a href="https://docs.pebbling.ai">
    <picture>
      <img src="sample_data/image/image.png" alt="Pebble" width="100">
    </picture>
  </a>
</div>
<div align="center">
  <a href="https://docs.pebbling.ai">📚 Documentation</a> &nbsp;|&nbsp;
  <a href="examples">💡 Examples</a> &nbsp;|&nbsp;
  <a href="https://github.com/Pebbling-ai/pebble/stargazers">🌟 Star Us</a>
</div>

<div align="center" id="top">
  <h1><strong>Pebble 🐧</strong></h1>
</div>




<div align="center">
  <h3> A Protocol to Connect Them All: Seamless AI Agent Communication </h3>
</div>

Millions Agents from mutiple frameworks - but how they will communicate? 
We are making the Esperanto of AI Agent Communication to solve the problem.
Enabling effortless collaboration across [Smolagent](https://github.com/huggingface/smolagents), [AgnoAI](https://github.com/agno-agi/agno), [CrewAI](https://github.com/crewai/crewai) and more. 
One protocol to unite them all , simple, powerful, and ready to transform how your agents communicate.


## 🏎️ Our Vision

**Building the Open Standard for Agent-to-Agent Communication in a World of Billions of AI Agents.**

As autonomous agents proliferate, secure and efficient communication becomes critical. Our protocol enables decentralized agent communication with:  

- **Security First**: Built on mutual TLS (mTLS) for enterprise-grade security
- **Framework-Agnostic Adapters**: Adapter system translates between different frameworks' internal representations.
- **Persistent State Management**: Maintain context and cognitive state across interactions
- **High Performance**: Lightweight protocol optimized for distributed systems
- **Future-Ready**: Designed for the coming era of autonomous, agent-driven applications

Without a standardized protocol, creating multi-agent systems becomes exponentially more complex, requiring custom adapters for each pair of frameworks.


## 🚀 Getting Started

```bash
# Install Pebble
pip install pebble

# Or with uv for faster installation
uv pip install pebble
```

Check out the [examples](examples/) directory to see how to use Pebble with different agent frameworks.


## 🏁 Quick Start

### Basic Agent Communication

```python
# Import Agno agent components
from agno.agent import Agent as AgnoAgent
from agno.models.openai import OpenAIChat
from agno.models.google import Gemini
from agno.tools.duckduckgo import DuckDuckGoTools

# Import pebble components
from pebble import deploy
from pebble.schemas.models import DeploymentConfig
from pebble.security.keys import get_secret_key, rotate_secret_key

# Initialize a simple Agno agent
basic_agent = AgnoAgent(
    name="Customer Support Assistant",
    model=OpenAIChat(id="gpt-4o"),
    description="You are a helpful customer support assistant for a software company.",
    instructions=[
        "Be concise and professional.",
        "If you don't know an answer, acknowledge it.",
        "Make use of your tools when appropriate.",
        "Focus on providing actionable solutions."
    ],
    tools=[DuckDuckGoTools()],
    show_tool_calls=True,
    markdown=True
)

audio_agent = AgnoAgent(
    name="Audio Assistant",
    model=Gemini(id="gemini-2.0-flash-thinking-exp"),
    description="You are an assistant that can process audio and generate responses.",
    instructions=[
        "Be concise and professional.",
        "If you don't know an answer, acknowledge it.",
        "Make use of your tools when appropriate.",
        "Focus on providing actionable solutions."
    ],
    markdown=True
)

image_agent = AgnoAgent(
    name="Image Assistant",
    model=OpenAIChat(id="gpt-4o"),
    markdown=True,
)

video_agent = AgnoAgent(
    name="Video Assistant",
    description="Process videos and generate engaging shorts.",
    model=Gemini(id="gemini-2.0-flash-exp"),
    markdown=True,
    debug_mode=True,
    instructions=[
    "Analyze the provided video directly—do NOT reference or analyze any external sources or YouTube videos."
    ]
)

config = DeploymentConfig(
    host="0.0.0.0",         # Host to bind to
    port=8000,              # Port to listen on
    cors_origins=["*"],     # CORS allowed origins
    enable_docs=True,       # Enable Swagger docs at /docs
    require_auth=True,      # Require authentication
    access_token_expire_minutes=30,  # Token expiration time
    api_key_expire_days=365  # API key expiration time
)

deploy(
    agent=[audio_agent, image_agent, video_agent],  # Pass a list of agents
    name=["Audio Processing Agent", "Image Processing Agent", "Video Processing Agent"],
    host=config.host,
    port=config.port,
    cors_origins=config.cors_origins,
    enable_docs=config.enable_docs,
    require_auth=config.require_auth
)

```

## 📚 Learn More

Visit our [documentation](https://docs.pebbling.ai) for comprehensive guides and API references.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
