#!/usr/bin/env python
"""
Protocol Coordinator Example

This example demonstrates how to use the ProtocolCoordinator to 
manage multiple agents and route messages between them.

Replacement Guide:
1. Replace the Agent implementations with your actual agent implementations
2. Modify the send_message and broadcast_message calls to fit your use case
3. Adapt the response handling to match your agent output formats
"""

import asyncio
import os
import json
from typing import Dict, List, Any, Optional

# Import pebble components
from pebble import (
    Protocol, 
    Message,
    MessageType, 
    AgentType,
    ProtocolCoordinator
)

# -----------------------------------------------------
# AGENT IMPLEMENTATIONS
# Replace these with your actual agent implementations
# -----------------------------------------------------

# For SmolAgent integration:
# from smolagents import Agent as SmolAgent
class SmolAgent:
    """Example SmolAgent implementation.
    Replace with actual SmolAgent import: from smolagents import Agent
    """
    def __init__(self, name, **kwargs):
        self.name = name
        self.config = kwargs
        # Your actual initialization here
    
    async def chat(self, message):
        # Replace with actual SmolAgent chat implementation
        print(f"[SmolAgent:{self.name}] Received message: {message}")
        return f"Response from {self.name} to: {message}"
    
    async def execute_task(self, task, **context):
        # Replace with actual SmolAgent task execution
        print(f"[SmolAgent:{self.name}] Executing task: {task} with context: {context}")
        return {"result": f"Task executed by {self.name}", "status": "success"}


# For AgnoAgent integration:
# from agno.agent import Agent as AgnoAgent
class AgnoAgent:
    """Example AgnoAgent implementation.
    Replace with actual AgnoAgent import: from agno.agent import Agent
    """
    def __init__(self, name, **kwargs):
        self.name = name
        self.config = kwargs
        # Your actual initialization here
    
    async def generate(self, message):
        # Replace with actual AgnoAgent generate implementation
        print(f"[AgnoAgent:{self.name}] Generating for message: {message}")
        return f"Generated content from {self.name}"
    
    async def run_task(self, task, **params):
        # Replace with actual AgnoAgent task execution
        print(f"[AgnoAgent:{self.name}] Running task: {task} with params: {params}")
        return {"output": f"Task result from {self.name}", "completed": True}


# For CrewAgent integration:
# from crewai import Agent as CrewAgent
class CrewAgent:
    """Example CrewAgent implementation.
    Replace with actual CrewAgent import: from crewai import Agent
    """
    def __init__(self, name, **kwargs):
        self.name = name
        self.config = kwargs
        # Your actual initialization here
    
    async def execute(self, message):
        # Replace with actual CrewAgent execute implementation
        print(f"[CrewAgent:{self.name}] Executing message: {message}")
        return f"Execution result from {self.name}"


async def coordinator_example():
    """
    Example of using the ProtocolCoordinator with different agent types.
    """
    print("=== Pebble Protocol Coordinator Example ===\n")
    
    # -------------------------------------------------
    # STEP 1: Set up your agents with appropriate configs
    # -------------------------------------------------
    
    # SmolAgent examples (replace with your configurations)
    code_assistant = SmolAgent(
        name="CodeAssistant",
        model="gpt-4",
        system_prompt="You are a programming assistant that helps write code."
    )
    
    data_analyst = SmolAgent(
        name="DataAnalyst",
        model="gpt-4",
        system_prompt="You analyze data and provide insights."
    )
    
    # AgnoAgent examples (replace with your configurations)
    researcher = AgnoAgent(
        name="Researcher",
        model="anthropic/claude-3",
        tools=["search", "calculator"]
    )
    
    fact_checker = AgnoAgent(
        name="FactChecker",
        model="anthropic/claude-3",
        tools=["search", "knowledge_base"]
    )
    
    # CrewAgent examples (replace with your configurations)
    project_manager = CrewAgent(
        name="ProjectManager",
        role="Manage project and coordinate team efforts",
        goal="Ensure project is completed on time and with high quality"
    )
    
    coordinator = CrewAgent(
        name="Coordinator",
        role="Coordinate the work between agents",
        goal="Ensure smooth communication and task handoffs"
    )
    
    # -------------------------------------------------
    # STEP 2: Create and configure the coordinator
    # -------------------------------------------------
    
    # Create the protocol coordinator
    protocol_coordinator = ProtocolCoordinator()
    print("Created Protocol Coordinator")
    
    # -------------------------------------------------
    # STEP 3: Register all agents with the coordinator
    # -------------------------------------------------
    
    # List of all agents to register
    all_agents = [
        code_assistant,
        data_analyst,
        researcher,
        fact_checker,
        project_manager,
        coordinator
    ]
    
    # Register each agent and store their IDs
    agent_ids = {}
    for agent in all_agents:
        agent_id = protocol_coordinator.register_agent(agent)
        agent_ids[agent.name] = agent_id
        print(f"Registered agent '{agent.name}' with ID: {agent_id}")
    
    print(f"\nTotal registered agents: {len(protocol_coordinator.get_registered_agents())}")
    print()
    
    # -------------------------------------------------
    # STEP 4: Send direct messages between agents
    # -------------------------------------------------
    
    print("=== Direct Message Communication ===")
    sender_name = "CodeAssistant"
    receiver_name = "Researcher"
    
    print(f"Sending message from {sender_name} to {receiver_name}...")
    try:
        response = await protocol_coordinator.send_message(
            sender_id=agent_ids[sender_name],
            receiver_id=agent_ids[receiver_name],
            content="I need information about the latest reinforcement learning algorithms",
            message_type=MessageType.TEXT,
            metadata={"priority": "high", "category": "research"}
        )
        
        if response:
            print(f"Response received from {receiver_name}:")
            print(f"- Content: {response.content}")
            print(f"- Timestamp: {response.timestamp}")
            
            # If you need to process the response further
            # Do your custom processing here
        else:
            print(f"No response received from {receiver_name}")
    except Exception as e:
        print(f"Error sending message: {str(e)}")
    
    print()
    
    # -------------------------------------------------
    # STEP 5: Broadcast messages to multiple agents
    # -------------------------------------------------
    
    print("=== Broadcast Message Communication ===")
    broadcaster_name = "ProjectManager"
    
    print(f"Broadcasting message from {broadcaster_name} to all other agents...")
    try:
        # You can exclude specific agents if needed with the exclude_ids parameter
        # exclude_ids=[agent_ids["FactChecker"]]
        responses = await protocol_coordinator.broadcast_message(
            sender_id=agent_ids[broadcaster_name],
            content="We're shifting priorities to focus on the new ML model deployment",
            message_type=MessageType.TEXT,
            metadata={"category": "announcement", "urgency": "high"}
        )
        
        print(f"Received {len(responses)} responses:")
        for agent_id, response in responses.items():
            if response:
                # Find agent name by ID
                agent_name = next((name for name, id in agent_ids.items() if id == agent_id), "Unknown")
                print(f"- {agent_name}: {response.content[:50]}..." if len(response.content) > 50 else f"- {agent_name}: {response.content}")
    except Exception as e:
        print(f"Error broadcasting message: {str(e)}")
    
    print()
    
    # -------------------------------------------------
    # STEP 6: Send commands to agents
    # -------------------------------------------------
    
    print("=== Command Message Communication ===")
    commander_name = "Coordinator"
    target_name = "DataAnalyst"
    
    # Example of a command with structured data
    command_data = {
        "command": "analyze_data",
        "args": {
            "dataset": "quarterly_performance",
            "metrics": ["revenue", "user_growth", "retention"],
            "filters": {"date_range": "last_quarter"},
            "output_format": "json"
        }
    }
    
    print(f"Sending command from {commander_name} to {target_name}...")
    try:
        command_response = await protocol_coordinator.send_message(
            sender_id=agent_ids[commander_name],
            receiver_id=agent_ids[target_name],
            content=command_data,
            message_type=MessageType.COMMAND
        )
        
        if command_response:
            print(f"Command response received:")
            if isinstance(command_response.content, dict):
                print(json.dumps(command_response.content, indent=2))
            else:
                print(command_response.content)
        else:
            print("No response to command")
    except Exception as e:
        print(f"Error sending command: {str(e)}")
    
    # -------------------------------------------------
    # STEP 7: Agent management (adding/removing agents)
    # -------------------------------------------------
    
    print("\n=== Agent Management ===")
    
    # Unregister an agent
    agent_to_remove = "FactChecker"
    try:
        success = protocol_coordinator.unregister_agent(agent_ids[agent_to_remove])
        print(f"Unregistered agent '{agent_to_remove}': {success}")
        print(f"Remaining registered agents: {len(protocol_coordinator.get_registered_agents())}")
    except Exception as e:
        print(f"Error unregistering agent: {str(e)}")
    
    # You can add new agents at runtime
    try:
        new_agent = SmolAgent(
            name="NewAgent",
            model="gpt-3.5-turbo",
            system_prompt="You are a helpful assistant."
        )
        
        new_id = protocol_coordinator.register_agent(new_agent)
        print(f"Registered new agent 'NewAgent' with ID: {new_id}")
        print(f"Total registered agents: {len(protocol_coordinator.get_registered_agents())}")
    except Exception as e:
        print(f"Error registering new agent: {str(e)}")


async def main():
    await coordinator_example()


if __name__ == "__main__":
    asyncio.run(main())
