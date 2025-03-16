#!/usr/bin/env python
"""
Simple Multi-Agent Workflow Example

This example demonstrates a simplified but practical multi-agent workflow
that developers can use as a starting point for their own applications.
"""

import asyncio
import json
from typing import Dict, Any, List, Optional

# Import pebble components
from pebble import (
    Protocol,
    Message,
    MessageType,
    AgentType,
    ProtocolCoordinator
)

# Simplified agent implementations - replace with your actual agents
class SimpleSmolAgent:
    def __init__(self, name: str, skill: str):
        self.name = name
        self.skill = skill
        
    async def chat(self, message: str) -> str:
        """Process a message and return a response."""
        return f"[{self.name}] ({self.skill}): Processed '{message}'"
    
    async def execute_task(self, task: str, **context) -> Dict[str, Any]:
        """Execute a task with the given context."""
        return {
            "result": f"Task '{task}' executed by {self.name}",
            "skill_applied": self.skill,
            "context_received": context
        }


class SimpleAgnoAgent:
    def __init__(self, name: str, expertise: str):
        self.name = name
        self.expertise = expertise
        
    async def generate(self, message: str) -> str:
        """Generate a response to the given message."""
        return f"[{self.name}] Analysis ({self.expertise}): {message}"
    
    async def run_task(self, task: str, **params) -> Dict[str, Any]:
        """Run a task with the given parameters."""
        return {
            "analysis": f"Analysis of '{task}' complete",
            "expertise_applied": self.expertise,
            "params_used": params
        }


class SimpleWorkflow:
    """
    A simple workflow that coordinates multiple agents to complete a task.
    """
    
    def __init__(self):
        self.coordinator = ProtocolCoordinator()
        self.agent_ids = {}
        self.results = {}
        
    def setup_agents(self):
        """Set up the agents needed for the workflow."""
        # Create agents with different roles
        agents = [
            SimpleSmolAgent("Coder", "Python"),
            SimpleSmolAgent("Documenter", "Technical Writing"),
            SimpleAgnoAgent("Analyzer", "Code Quality"),
            SimpleAgnoAgent("Tester", "Unit Testing")
        ]
        
        # Register agents with the coordinator
        for agent in agents:
            agent_id = self.coordinator.register_agent(agent)
            self.agent_ids[agent.name] = agent_id
            print(f"Registered agent '{agent.name}' with ID: {agent_id}")
            
    async def run_workflow(self, project_spec: str):
        """Run the workflow with the given project specification."""
        print(f"\n=== Starting Simple Workflow for: {project_spec} ===\n")
        
        # Step 1: Analyzer agent analyzes the project specification
        print("Step 1: Analyzing project specification")
        analysis_response = await self.coordinator.send_message(
            sender_id="workflow",
            receiver_id=self.agent_ids["Analyzer"],
            content=f"Analyze requirements: {project_spec}",
            message_type=MessageType.TEXT
        )
        
        self.results["analysis"] = analysis_response.content
        print(f"Analysis result: {analysis_response.content}")
        print()
        
        # Step 2: Coder agent implements the code
        print("Step 2: Implementing code")
        implementation_response = await self.coordinator.send_message(
            sender_id=self.agent_ids["Analyzer"],
            receiver_id=self.agent_ids["Coder"],
            content={
                "command": "execute_task",
                "args": {
                    "task": "Implement solution",
                    "requirements": project_spec,
                    "analysis": self.results["analysis"]
                }
            },
            message_type=MessageType.COMMAND
        )
        
        self.results["implementation"] = implementation_response.content
        print(f"Implementation result: {implementation_response.content}")
        print()
        
        # Step 3: Tester agent tests the implementation
        print("Step 3: Testing implementation")
        testing_response = await self.coordinator.send_message(
            sender_id=self.agent_ids["Coder"],
            receiver_id=self.agent_ids["Tester"],
            content={
                "command": "run_task",
                "args": {
                    "task": "Test implementation",
                    "implementation": self.results["implementation"]
                }
            },
            message_type=MessageType.COMMAND
        )
        
        self.results["testing"] = testing_response.content
        print(f"Testing result: {testing_response.content}")
        print()
        
        # Step 4: Documenter creates documentation
        print("Step 4: Creating documentation")
        documentation_response = await self.coordinator.send_message(
            sender_id="workflow",
            receiver_id=self.agent_ids["Documenter"],
            content={
                "command": "execute_task",
                "args": {
                    "task": "Create documentation",
                    "requirements": project_spec,
                    "implementation": self.results["implementation"],
                    "test_results": self.results["testing"]
                }
            },
            message_type=MessageType.COMMAND
        )
        
        self.results["documentation"] = documentation_response.content
        print(f"Documentation result: {documentation_response.content}")
        print()
        
        # Step 5: Final report
        print("=== Workflow Summary ===")
        for step, result in self.results.items():
            print(f"- {step.capitalize()}: Completed successfully")
            
        return self.results


async def main():
    """Run the simple workflow example."""
    # Create and set up the workflow
    workflow = SimpleWorkflow()
    workflow.setup_agents()
    
    # Define a simple project
    project_spec = "Create a function to calculate fibonacci numbers recursively"
    
    # Run the workflow
    results = await workflow.run_workflow(project_spec)
    
    print("\n=== Workflow Complete ===")
    print(f"Project: {project_spec}")
    print("All steps completed successfully")


if __name__ == "__main__":
    asyncio.run(main())
