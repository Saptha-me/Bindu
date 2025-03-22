<div align="center">
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

<br/>

<div align="center">
  <h1><strong>Pebble 🐧</strong></h1>
  <h3>One Protocol to Connect Them All: Seamless AI Agent Communication</h3>
</div>

---

> **Millions of AI agents. Different frameworks. No universal language.**  
> Pebble is the *Esperanto* for agent-to-agent communication — a simple, secure, and powerful protocol enabling collaboration across [Smolagent](https://github.com/huggingface/smolagents), [AgnoAI](https://github.com/agno-agi/agno), [CrewAI](https://github.com/crewai/crewai), and beyond.

---

## 🏎️ Our Vision

**Build the open standard for agent communication in a world with billions of AI agents.**

As autonomous agents scale, seamless and secure communication becomes non-negotiable. Pebble is designed to be the backbone of this agent ecosystem:

- 🔐 **Security First**: Built on mutual TLS (mTLS) for end-to-end trust  
- 🔌 **Framework-Agnostic**: Adapters bridge internal APIs across ecosystems  
- 🧠 **Stateful by Default**: Maintain agent memory and cognition across requests  
- ⚡ **Blazing Fast**: Lightweight protocol optimized for distributed deployments  
- 🔮 **Future-Proof**: Built for the coming wave of autonomous applications

> Without Pebble, building interoperable multi-agent systems is like writing custom APIs for every pair of agents. Yikes.

---

## 🚀 Installation

```bash
# Install Pebble
pip install pebble

# Or use uv for faster installs
uv pip install pebble
```

Check out the [examples](examples/) directory to see how to use Pebble with different agent frameworks.


## 🏁 Quickstart: Cross-Framework Agent Communication

```python
from agno.agent import Agent as AgnoAgent
from agno.models.openai import OpenAIChat
from agno.models.google import Gemini
from agno.tools.duckduckgo import DuckDuckGoTools

from pebble import deploy
from pebble.schemas.models import DeploymentConfig

# Define agents
support_agent = AgnoAgent(
    name="Customer Support",
    model=OpenAIChat(id="gpt-4o"),
    description="Handles user queries for a software company.",
    instructions=[
        "Be concise and professional.",
        "Acknowledge unknowns gracefully.",
        "Use tools when relevant.",
        "Focus on actionable advice."
    ],
    tools=[DuckDuckGoTools()],
    show_tool_calls=True,
    markdown=True
)

audio_agent = AgnoAgent(
    name="Audio Assistant",
    model=Gemini(id="gemini-2.0-flash-thinking-exp"),
    description="Processes audio and generates intelligent responses.",
    instructions=[
        "Be concise and professional.",
        "Use tools when relevant.",
        "Don’t fake answers."
    ],
    markdown=True
)

video_agent = AgnoAgent(
    name="Video Assistant",
    description="Processes videos to generate engaging shorts.",
    model=Gemini(id="gemini-2.0-flash-exp"),
    debug_mode=True,
    instructions=[
        "Analyze only the input video.",
        "Avoid referencing YouTube or external content."
    ],
    markdown=True
)

# Deployment config
config = DeploymentConfig(
    host="0.0.0.0",
    port=8000,
    cors_origins=["*"],
    enable_docs=True,
    require_auth=True,
    access_token_expire_minutes=30,
    api_key_expire_days=365
)

# Launch agents
deploy(
    agent=[support_agent, audio_agent, video_agent],
    name=["Customer Support", "Audio Agent", "Video Agent"],
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

We welcome contributions of all kinds:

1. Fork the repo
2. Create your feature branch: `git checkout -b feat/amazing-idea`
3. Commit your changes: `git commit -m "feat: added amazing idea"`
4. Push to your branch: `git push origin feat/amazing-idea`
5. Submit a Pull Request ❤️

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
