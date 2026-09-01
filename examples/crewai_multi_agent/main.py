from bindu.penguin.bindufy import bindufy

def research_agent(query):
    return f"📊 Research Data:\n'{query}' involves autonomous systems that use reasoning, memory, and tools to complete tasks."

def summary_agent(research_text):
    return f"📝 Summary:\nThis topic explains how AI agents work step-by-step to solve problems efficiently."

def handler(messages):
    user_input = messages[-1]["content"]
    research_output = research_agent(user_input)
    final_output = summary_agent(research_output)

    return [{
        "role": "assistant",
        "content": f"{research_output}\n\n{final_output}"
    }]

config = {
    "author": "your_email@example.com",
    "name": "crewai_multi_agent",
    "description": "Multi-agent system using Bindu (Research + Summary agents)",
    "deployment": {
        "url": "http://localhost:3773",
        "expose": True,
    },
    "skills": []
}


bindufy(config, handler)