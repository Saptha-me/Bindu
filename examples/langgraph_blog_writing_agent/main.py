from bindu.penguin.bindufy import bindufy
from graph import build_graph
from schemas import AgentResponse

graph = build_graph()

def handler(messages):
    try:
        # Handle possible dict wrapper
        if isinstance(messages, dict) and "messages" in messages:
            messages = messages["messages"]

        if not messages:
            raise ValueError("No messages received")

        last_message = messages[-1]

        # Support all formats:
        # 1) A2A messages: [{"role": "user", "parts": [{"kind": "text", ...}]}]
        # 2) chat format (older bindu releases): [{"role": "user", "content": "..."}]
        # 3) ["plain string"]
        if isinstance(last_message, dict):
            text = " ".join(
                p.get("text", "")
                for p in last_message.get("parts", [])
                if p.get("kind") == "text"
            )
            query = text or last_message.get("content", "")
        else:
            query = str(last_message)

        result = graph.invoke({
            "topic": query,
            "plan": None,
            "sections": [],
            "final": None
        })

        return result["final"]

    except Exception as e:
        return AgentResponse(
            answer="Agent execution failed.",)

config = {
    "author": "amritanshu9973@gmail.com",
    "name": "langgraph_blog_writing_agent",
    "deployment": {
        "url": "http://localhost:3773",
        "expose": True,
        "cors_origins": ["*"],
    },
    "skills": ["skills/Blog_writing_agent"],
}

bindufy(config, handler)
