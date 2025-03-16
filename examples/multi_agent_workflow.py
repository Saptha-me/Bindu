#!/usr/bin/env python
"""
Multi-Agent Workflow Example

This example demonstrates a practical use case of the pebble protocol
for orchestrating a workflow across multiple agent types with different roles.

The workflow simulates a project where:
1. A CrewAgent acts as the project manager
2. AgnoAgents perform research and fact-checking
3. SmolAgents handle code implementation and data analysis
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

# Import mock agents (using the same mock classes as in other examples)
class MockSmolAgent:
    """Mock implementation of SmolAgent for example purposes."""
    def __init__(self, name, role):
        self.name = name
        self.id = f"smol-{name}"
        self.role = role
        self.memory = {}
        
    async def chat(self, message):
        if self.role == "coder":
            return f"SmolAgent {self.name} writes code in response to: '{message}'"
        elif self.role == "data_analyst":
            return f"SmolAgent {self.name} analyzes data for query: '{message}'"
        else:
            return f"SmolAgent {self.name} responds to: '{message}'"
    
    async def execute_task(self, task, **context):
        if "remember" in task.lower():
            key = context.get("key", "default")
            value = context.get("value", "")
            self.memory[key] = value
            return f"SmolAgent {self.name} stored '{value}' with key '{key}'"
        
        if "recall" in task.lower() and context.get("key") in self.memory:
            return f"SmolAgent {self.name} recalls: {self.memory[context.get('key')]}"
            
        return f"SmolAgent {self.name} ({self.role}) executed task: {task}"


class MockAgnoAgent:
    """Mock implementation of AgnoAgent for example purposes."""
    def __init__(self, name, role):
        self.name = name
        self.id = f"agno-{name}"
        self.role = role
        
    async def generate(self, message):
        if self.role == "researcher":
            return f"AgnoAgent {self.name} researched: '{message}' and found relevant information"
        elif self.role == "fact_checker":
            return f"AgnoAgent {self.name} verified the facts in: '{message}' and they are accurate"
        else:
            return f"AgnoAgent {self.name} generated a response to: '{message}'"
    
    async def run_task(self, task, **params):
        return f"AgnoAgent {self.name} ({self.role}) ran task: {task}"


class MockCrewAgent:
    """Mock implementation of CrewAgent for example purposes."""
    def __init__(self, name, role):
        self.name = name
        self.id = f"crew-{name}"
        self.role = role
        self.plan = []
        
    async def execute(self, message):
        if self.role == "project_manager":
            return f"CrewAgent {self.name} coordinated the team regarding: '{message}'"
        elif self.role == "reviewer":
            return f"CrewAgent {self.name} reviewed and provided feedback on: '{message}'"
        else:
            return f"CrewAgent {self.name} executed message: '{message}'"
    
    async def execute_task(self, task, **context):
        if "create_plan" in task.lower() and context.get("steps"):
            self.plan = context.get("steps", [])
            return f"CrewAgent {self.name} created a plan with {len(self.plan)} steps"
        
        if "get_plan" in task.lower():
            return {"plan": self.plan}
            
        return f"CrewAgent {self.name} ({self.role}) executed task: {task} with context: {context}"


class ProjectWorkflow:
    """
    Orchestrates a multi-agent workflow for a project using the pebble protocol.
    """
    
    def __init__(self):
        self.coordinator = ProtocolCoordinator()
        self.agent_ids = {}
        self.project_data = {}
        
    def setup_agents(self):
        """Create and register all agents needed for the workflow."""
        agents = [
            # Project management
            MockCrewAgent("ProjectManager", "project_manager"),
            MockCrewAgent("QualityReviewer", "reviewer"),
            
            # Research team
            MockAgnoAgent("PrimaryResearcher", "researcher"),
            MockAgnoAgent("FactChecker", "fact_checker"),
            
            # Implementation team
            MockSmolAgent("LeadDeveloper", "coder"),
            MockSmolAgent("DataScientist", "data_analyst")
        ]
        
        # Register all agents with coordinator
        for agent in agents:
            agent_id = self.coordinator.register_agent(agent)
            self.agent_ids[agent.name] = agent_id
            print(f"Registered {agent.role.capitalize()} '{agent.name}' with ID: {agent_id}")
    
    async def run_project(self, project_brief: str):
        """
        Execute the entire project workflow based on a project brief.
        
        Args:
            project_brief: Description of the project requirements
        """
        print(f"\n===== STARTING PROJECT: {project_brief} =====\n")
        
        # Step 1: Project Manager creates a plan
        print("STEP 1: Project planning")
        plan_steps = [
            "Research requirements and gather information",
            "Analyze data and identify patterns",
            "Implement solution based on research",
            "Review and quality check",
            "Finalize deliverables"
        ]
        
        plan_response = await self.coordinator.send_message(
            sender_id="workflow-system",
            receiver_id=self.agent_ids["ProjectManager"],
            content={
                "command": "execute_task",
                "args": {
                    "task": "create_plan",
                    "context": {"steps": plan_steps, "project": project_brief}
                }
            },
            message_type=MessageType.COMMAND
        )
        
        print(f"Project Manager: {plan_response.content}")
        print()
        
        # Step 2: Research phase
        print("STEP 2: Research phase")
        research_response = await self.coordinator.send_message(
            sender_id=self.agent_ids["ProjectManager"],
            receiver_id=self.agent_ids["PrimaryResearcher"],
            content=f"Research everything about: {project_brief}",
            message_type=MessageType.TEXT
        )
        
        print(f"Researcher: {research_response.content}")
        
        # Fact check the research
        fact_check_response = await self.coordinator.send_message(
            sender_id=self.agent_ids["ProjectManager"],
            receiver_id=self.agent_ids["FactChecker"],
            content=f"Verify this research: {research_response.content}",
            message_type=MessageType.TEXT
        )
        
        print(f"Fact Checker: {fact_check_response.content}")
        print()
        
        # Store the research results
        self.project_data["research"] = {
            "findings": research_response.content,
            "verification": fact_check_response.content
        }
        
        # Step 3: Analysis phase
        print("STEP 3: Analysis phase")
        analysis_response = await self.coordinator.send_message(
            sender_id=self.agent_ids["ProjectManager"],
            receiver_id=self.agent_ids["DataScientist"],
            content=f"Analyze the following research data: {research_response.content}",
            message_type=MessageType.TEXT
        )
        
        print(f"Data Scientist: {analysis_response.content}")
        print()
        
        self.project_data["analysis"] = analysis_response.content
        
        # Step 4: Implementation phase
        print("STEP 4: Implementation phase")
        implementation_response = await self.coordinator.send_message(
            sender_id=self.agent_ids["ProjectManager"],
            receiver_id=self.agent_ids["LeadDeveloper"],
            content={
                "command": "execute_task",
                "args": {
                    "task": "implement_solution",
                    "context": {
                        "research": self.project_data["research"],
                        "analysis": self.project_data["analysis"],
                        "requirements": project_brief
                    }
                }
            },
            message_type=MessageType.COMMAND
        )
        
        print(f"Lead Developer: {implementation_response.content}")
        print()
        
        self.project_data["implementation"] = implementation_response.content
        
        # Step 5: Review phase
        print("STEP 5: Review phase")
        review_response = await self.coordinator.send_message(
            sender_id=self.agent_ids["ProjectManager"],
            receiver_id=self.agent_ids["QualityReviewer"],
            content=f"Review the project implementation: {implementation_response.content}",
            message_type=MessageType.TEXT
        )
        
        print(f"Quality Reviewer: {review_response.content}")
        print()
        
        # Step 6: Finalize project - broadcast to all
        print("STEP 6: Project finalization")
        final_responses = await self.coordinator.broadcast_message(
            sender_id=self.agent_ids["ProjectManager"],
            content=f"Project completed! Thanks for your contributions to: {project_brief}",
            message_type=MessageType.TEXT,
            metadata={"project_status": "completed"}
        )
        
        print("Final team responses:")
        for agent_id, response in final_responses.items():
            if response:
                # Find agent name by ID
                agent_name = next((name for name, id in self.agent_ids.items() if id == agent_id), "Unknown")
                print(f"- {agent_name}: Acknowledged")
        
        print(f"\n===== PROJECT COMPLETED =====")
        
        return self.project_data


async def main():
    print("=== Pebble Multi-Agent Workflow Example ===\n")
    
    # Create and set up the project workflow
    workflow = ProjectWorkflow()
    workflow.setup_agents()
    
    # Run a sample project
    project_brief = "Build a machine learning model to predict customer churn"
    project_results = await workflow.run_project(project_brief)
    
    print("\n=== Project Summary ===")
    print(f"Project: {project_brief}")
    print("Phases completed:")
    for phase, data in project_results.items():
        print(f"- {phase.capitalize()}")


if __name__ == "__main__":
    asyncio.run(main())
