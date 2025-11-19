# Streamlit UI Guide for Bindu

## Overview

Bindu now supports Streamlit as an alternative to Gradio for the chat interface. Streamlit provides a clean, modern UI with built-in session state management.

## Quick Start

### Option 1: Using bindufy (Recommended)

1. **Update your config** to use Streamlit:

```python
from bindu.penguin.bindufy import bindufy

config = {
    "author": "your.email@example.com",
    "name": "my_agent",
    "description": "My agent description",
    "deployment": {"url": "http://localhost:3773"},
}

bindufy(config, handler, ui="streamlit")
```

2. **Run your agent**:
```bash
python examples/agno_example_streamlit.py
```

3. **In a separate terminal, run Streamlit**:
```bash
streamlit run bindu/ui/streamlit_ui.py
```

### Option 2: Direct Launch

```python
from bindu.ui import launch_streamlit_ui

launch_streamlit_ui(
    base_url="http://localhost:3773",
    title="My Agent",
    description="Chat with my agent"
)
```

Then run:
```bash
streamlit run your_script.py
```

## Features

### 1. **Reply to Messages**

Unlike Gradio's like button approach, Streamlit uses explicit Reply buttons:

- Each agent message has a **"↩️ Reply"** button
- Click it to select that message for reply
- A blue info box appears showing which task you're replying to
- Type your message and it will include `referenceTaskIds`

### 2. **Task Details**

Each agent response includes an expandable "📋 Task Details" section showing:
- Full Task ID
- Task State (completed, input-required, etc.)

### 3. **Sidebar Agent Info**

The sidebar displays:
- Agent name and description
- Available skills
- Message count
- Context ID

### 4. **Session State**

Streamlit maintains conversation history across page reloads using session state.

## UI Layout

```
┌─────────────────────────────────────────────────────────────┐
│  Sidebar                │  Main Chat Area                   │
│  ┌──────────────────┐   │  ┌─────────────────────────────┐ │
│  │ 🤖 Agent Info    │   │  │ My Agent                    │ │
│  │                  │   │  │ Chat with my agent          │ │
│  │ Name: my_agent   │   │  ├─────────────────────────────┤ │
│  │ Description: ... │   │  │                             │ │
│  │                  │   │  │ User: hi                    │ │
│  │ Skills:          │   │  │                             │ │
│  │ - skill1         │   │  │ Agent: Hello!               │ │
│  │                  │   │  │ 📋 Task Details             │ │
│  ├──────────────────┤   │  │ [↩️ Reply]                  │ │
│  │ 📋 Tasks         │   │  │                             │ │
│  │ Messages: 2      │   │  │ ℹ️ Replying to: abc123...  │ │
│  │ Context: abc...  │   │  │ [✖️ Clear]                  │ │
│  └──────────────────┘   │  │                             │ │
│                         │  │ Type your message here...   │ │
│                         │  └─────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Reply Feature in Detail

### How It Works

1. **Click "↩️ Reply"** on any agent message
2. **Reply indicator appears** (blue info box):
   ```
   💬 Replying to task: abc12345...  [✖️ Clear]
   ```
3. **Type your message** in the chat input
4. **Message is sent** with `referenceTaskIds: ["full-task-uuid"]`
5. **Indicator clears** automatically after sending

### Visual Example

```
┌─────────────────────────────────────────────────────────┐
│ Agent: Here's a long poem about AI...                  │
│ 📋 Task Details                                         │
│   Task ID: 2a35ae09-67a1-4fc1-b0bb-3a4c4850B78F       │
│   State: completed                                      │
│ [↩️ Reply]                                              │  ← Click here
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ ℹ️ Replying to task: 2a35ae09...  [✖️ Clear]           │  ← Appears here
└─────────────────────────────────────────────────────────┘

Type your message here...  ← Type "make it shorter"
```

## Advantages of Streamlit

### vs Gradio:

1. **Clearer Reply UX**: Explicit Reply buttons vs like buttons
2. **Better State Management**: Built-in session state
3. **Simpler Deployment**: Standard Python script
4. **More Customizable**: Easy to modify layout and styling
5. **Native Python**: No JavaScript/CSS needed

## Configuration

### Custom Styling

Streamlit uses its own theming system. Create `.streamlit/config.toml`:

```toml
[theme]
primaryColor = "#0366d6"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f6f8fa"
textColor = "#24292e"
font = "sans serif"
```

### Page Config

Modify in `streamlit_ui.py`:

```python
st.set_page_config(
    page_title="My Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)
```

## Deployment

### Local Development

```bash
# Terminal 1: Start agent server
python examples/agno_example_streamlit.py

# Terminal 2: Start Streamlit UI
streamlit run bindu/ui/streamlit_ui.py
```

### Production

Use Streamlit Cloud or deploy with Docker:

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY . .

RUN pip install -r requirements.txt

# Start both server and UI
CMD ["sh", "-c", "python examples/agno_example_streamlit.py & streamlit run bindu/ui/streamlit_ui.py --server.port 8501"]
```

## Troubleshooting

### Issue: "Connection refused"

**Solution**: Make sure the agent server is running on the correct port:
```bash
# Check if server is running
curl http://localhost:3773/agent/info
```

### Issue: Reply indicator doesn't clear

**Solution**: Streamlit reruns the entire script on interaction. The indicator clears automatically after sending a message.

### Issue: Messages disappear on refresh

**Solution**: This is expected. Streamlit session state is per-session. To persist messages, integrate with a database.

## API Reference

### launch_streamlit_ui()

```python
def launch_streamlit_ui(
    base_url: str = "http://localhost:3773",
    auth_token: str | None = None,
    title: str = "Bindu Agent Chat",
    description: str | None = None,
)
```

**Parameters:**
- `base_url`: Agent server URL
- `auth_token`: Optional JWT token for authentication
- `title`: Page title
- `description`: Optional description text

## Examples

### Basic Usage

```python
from bindu.ui import launch_streamlit_ui

if __name__ == "__main__":
    launch_streamlit_ui(
        base_url="http://localhost:3773",
        title="Research Assistant",
        description="Ask me anything!"
    )
```

### With Authentication

```python
launch_streamlit_ui(
    base_url="http://localhost:3773",
    auth_token="your-jwt-token",
    title="Secure Agent"
)
```

## Comparison: Gradio vs Streamlit

| Feature | Gradio | Streamlit |
|---------|--------|-----------|
| Reply Button | Like button (👍) | Explicit Reply button (↩️) |
| State Management | Manual | Built-in session state |
| Customization | CSS/JS | Python config |
| Deployment | Built-in server | Separate command |
| Learning Curve | Low | Low |
| UI Updates | Event-based | Rerun-based |

## Next Steps

1. Try the Streamlit UI with your agent
2. Customize the layout and styling
3. Add custom features using Streamlit components
4. Deploy to Streamlit Cloud for public access

For more information, see:
- [Streamlit Documentation](https://docs.streamlit.io/)
- [Bindu Documentation](https://github.com/Saptha-me/Bindu)
