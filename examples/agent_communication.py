#!/usr/bin/env python
"""
Agent Communication Example

This example demonstrates how to set up direct communication between
different agent types using the pebble protocol adapters.

Replacement Guide:
1. Replace the example Agent implementations with your actual agent implementations
2. Adjust the adapter configuration to match your agent's API
3. Modify the message format and content to fit your use case
"""

import asyncio
import json
import os
from typing import Dict, Any, Optional, List, Union

# Import pebble components
from pebble import (
    Protocol, 
    Message,
    MessageType, 
    AgentType,
    SmolAdapter,
    AgnoAdapter, 
    CrewAdapter
)

#------------------------------------------------------------
# AGENT IMPLEMENTATIONS
# Replace these with your actual agent implementations
#------------------------------------------------------------

# For SmolAgent integration
# from smolagents import CodeAgent as SmolAgent
class SmolAgent:
    """
    Example SmolAgent implementation.
    Replace with actual SmolAgent import from your installed libraries.
    """
    def __init__(self, name: str, **kwargs):
        self.name = name 
        self.config = kwargs
        # Add your actual initialization code here
        
    async def chat(self, message: str) -> str:
        """Process a message and return a response."""
        # Replace with actual SmolAgent chat implementation
        print(f"[SmolAgent:{self.name}] Processing message: {message}")
        return f"SmolAgent {self.name} processed your message: '{message}'"
    
    async def execute_task(self, task: str, **context) -> Union[str, Dict[str, Any]]:
        """Execute a task with the given context."""
        # Replace with actual SmolAgent task execution
        print(f"[SmolAgent:{self.name}] Executing task: {task}")
        return f"Task '{task}' was executed successfully by {self.name}"


# For AgnoAgent integration
# from agno.agent import Agent as AgnoAgent
class AgnoAgent:
    """
    Example AgnoAgent implementation.
    Replace with actual AgnoAgent import from your installed libraries.
    """
    def __init__(self, name: str, **kwargs):
        self.name = name
        self.config = kwargs
        # Add your actual initialization code here
        
    async def generate(self, message: str) -> str:
        """Generate a response to the given message."""
        # Replace with actual AgnoAgent generate implementation
        print(f"[AgnoAgent:{self.name}] Generating response to: {message}")
        return f"Research findings by {self.name} on '{message}'"
    
    async def run_task(self, task: str, **params) -> Union[str, Dict[str, Any]]:
        """Run a task with the given parameters."""
        # Replace with actual AgnoAgent task execution
        print(f"[AgnoAgent:{self.name}] Running task: {task}")
        return {
            "status": "completed",
            "result": f"Task '{task}' completed by {self.name}",
            "metrics": {"time_taken": 2.5}
        }


# For CrewAgent integration
# from crewai import Agent as CrewAgent
class CrewAgent:
    """
    Example CrewAgent implementation.
    Replace with actual CrewAgent import from your installed libraries.
    """
    def __init__(self, name: str, **kwargs):
        self.name = name
        self.config = kwargs
        # Add your actual initialization code here
        
    async def execute(self, message: str) -> str:
        """Execute a message and return a response."""
        # Replace with actual CrewAgent execute implementation
        print(f"[CrewAgent:{self.name}] Executing: {message}")
        return f"CrewAgent {self.name} executed the task related to '{message}'"
    
    # Add any other methods required by your CrewAgent implementation


async def direct_communication_example():
    """
    Example of direct communication between agent adapters.
    """
    print("=== Pebble Direct Agent Communication Example ===\n")
    
    #------------------------------------------------------------
    # STEP 1: Create your agent instances
    #------------------------------------------------------------
    # Replace with your actual agent instances
    
    # Create a SmolAgent (replace with your implementation)
    smol_agent = SmolAgent(
        name="CodeAssistant",
        model="gpt-4", 
        system_prompt="You are a coding assistant that helps with programming tasks."
    )
    
    # Create an AgnoAgent (replace with your implementation)
    agno_agent = AgnoAgent(
        name="Researcher",
        model="claude-3",
        tools=["web_search", "document_retrieval"]
    )
    
    # Create a CrewAgent (replace with your implementation)
    crew_agent = CrewAgent(
        name="Coordinator",
        role="Project manager that coordinates tasks",
        goal="Ensure tasks are completed efficiently",
        backstory="Experienced in managing complex projects"
    )
    
    #------------------------------------------------------------
    # STEP 2: Create adapters for each agent
    #------------------------------------------------------------
    # The adapters translate between the pebble protocol and agent-specific formats
    
    # Create adapters for each agent type
    try:
        smol_adapter = SmolAdapter(smol_agent)
        agno_adapter = AgnoAdapter(agno_agent)
        crew_adapter = CrewAdapter(crew_agent)
        
        print("Created agents with adapters:")
        print(f"- SmolAgent: {smol_agent.name} (ID: {smol_adapter.agent_id})")
        print(f"- AgnoAgent: {agno_agent.name} (ID: {agno_adapter.agent_id})")
        print(f"- CrewAgent: {crew_agent.name} (ID: {crew_adapter.agent_id})")
    except Exception as e:
        print(f"Error creating adapters: {str(e)}")
        return
    
    print()
    
    #------------------------------------------------------------
    # STEP 3: Create and send messages between agents
    #------------------------------------------------------------
    
    # Initialize the protocol for message creation
    protocol = Protocol()
    
    # Example: SmolAgent sending a message to AgnoAgent
    try:
        # Create a text message
        message = protocol.create_message(
            message_type=MessageType.TEXT,
            sender=smol_adapter.agent_id,
            content="What are the latest advancements in transformer architectures for code generation?",
            receiver=agno_adapter.agent_id,
            metadata={"priority": "high", "category": "research"}
        )
        
        print(f"Message created:")
        print(f"- From: {message.sender} (SmolAgent)")
        print(f"- To: {message.receiver} (AgnoAgent)")
        print(f"- Type: {message.type}")
        print(f"- Content: {message.content}")
        print(f"- Metadata: {message.metadata}")
        print()
        
        # Send message from SmolAgent to AgnoAgent
        print("Sending message to AgnoAgent...")
        response = await agno_adapter.send_message(message)
        
        # Process the response
        if response:
            print(f"Response received:")
            print(f"- From: {response.sender} (AgnoAgent)")
            print(f"- To: {response.receiver} (SmolAgent)")
            print(f"- Type: {response.type}")
            print(f"- Content: {response.content}")
            print(f"- Timestamp: {response.timestamp}")
        else:
            print("No response received")
    except Exception as e:
        print(f"Error in text message communication: {str(e)}")
    
    print()
    
    #------------------------------------------------------------
    # STEP 4: Sending structured commands between agents
    #------------------------------------------------------------
    
    # Example: CrewAgent sending a command to SmolAgent
    try:
        # Create a command message with structured data
        command_data = {
            "command": "execute_task",
            "args": {
                "task": "Write a sorting algorithm in Python",
                "requirements": {
                    "algorithm": "quicksort",
                    "comments": True,
                    "test_cases": True
                }
            }
        }
        
        command_message = protocol.create_message(
            message_type=MessageType.COMMAND,
            sender=crew_adapter.agent_id,
            content=command_data,
            receiver=smol_adapter.agent_id
        )
        
        print(f"Command message created:")
        print(f"- From: {command_message.sender} (CrewAgent)")
        print(f"- To: {command_message.receiver} (SmolAgent)")
        print(f"- Type: {command_message.type}")
        print(f"- Command: {json.dumps(command_message.content, indent=2)}")
        print()
        
        # Send command from CrewAgent to SmolAgent
        print("Sending command to SmolAgent...")
        command_response = await smol_adapter.send_message(command_message)
        
        # Process the command response
        if command_response:
            print(f"Command response received:")
            print(f"- From: {command_response.sender} (SmolAgent)")
            print(f"- Content: {command_response.content}")
        else:
            print("No response to command")
    except Exception as e:
        print(f"Error in command communication: {str(e)}")
    
    print()
    
    #------------------------------------------------------------
    # STEP 5: Advanced usage - Agent-specific format adaptation
    #------------------------------------------------------------
    
    print("=== Agent-Specific Format Adaptation ===\n")
    
    # Create a generic message
    generic_message = protocol.create_message(
        message_type=MessageType.TEXT,
        sender="system",
        content="Explain how transformer models work",
    )
    
    # Demonstrate adapting the message to different agent formats
    print("Adapting generic message to different agent formats:")
    
    # For SmolAgent format
    smol_format = protocol.adapt_for_agent_type(generic_message, AgentType.SMOL)
    print(f"\nSmolAgent format:")
    print(json.dumps(smol_format, indent=2))
    
    # For AgnoAgent format
    agno_format = protocol.adapt_for_agent_type(generic_message, AgentType.AGNO)
    print(f"\nAgnoAgent format:")
    print(json.dumps(agno_format, indent=2))
    
    # For CrewAgent format
    crew_format = protocol.adapt_for_agent_type(generic_message, AgentType.CREW)
    print(f"\nCrewAgent format:")
    print(json.dumps(crew_format, indent=2))


async def main():
    await direct_communication_example()


if __name__ == "__main__":
    asyncio.run(main())
