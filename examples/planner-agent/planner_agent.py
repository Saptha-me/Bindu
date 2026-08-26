"""Planner Agent - Multi-Agent Task Orchestrator for Bindu

A Bindu-native agent that orchestrates task execution across multiple
specialized agents. Demonstrates the "Internet of Agents" vision where
agents collaborate based on capabilities.

Architecture:
    User Goal → Planner → Task Decomposer → Agent Registry
              → Worker Agents → Aggregator → Final Result

Features:
    - Rule-based task decomposition
    - Capability-based agent discovery
    - HTTP/JSON-RPC agent communication
    - Intelligent result aggregation

Usage:
    python planner_agent.py

Environment:
    WORKER_AGENTS - Comma-separated list of worker agent URLs
"""

import os
from bindu.penguin.bindufy import bindufy
from core.task_decomposer import TaskDecomposer
from core.agent_registry import AgentRegistry
from core.aggregator import Aggregator
from core.executor import execute_on_agent


# Load worker agent URLs from environment
WORKER_AGENTS = os.getenv(
    "WORKER_AGENTS",
    "http://localhost:3775,http://localhost:3776"
).split(",")


def handler(messages):
    """
    Main orchestration handler.
    
    1. Decomposes user goal into sub-tasks
    2. Discovers agents by capability
    3. Executes tasks on matched agents
    4. Aggregates results into coherent response
    
    Args:
        messages: List of message dicts from conversation history
    
    Returns:
        List with single assistant message containing orchestration results
    """
    user_goal = messages[-1]["content"]
    
    print(f"\n🎯 Planner received goal: {user_goal}")
    
    # Step 1: Decompose goal into sub-tasks
    decomposer = TaskDecomposer()
    sub_tasks = decomposer.decompose(user_goal)
    
    print(f"📋 Decomposed into {len(sub_tasks)} sub-tasks:")
    for task in sub_tasks:
        print(f"   Step {task['step']}: {task['description']}")
    
    # Step 2: Discover agents from registry
    registry = AgentRegistry(WORKER_AGENTS)
    execution_plan = []
    
    for task in sub_tasks:
        agent = registry.find_agent_for_capabilities(
            task["required_capabilities"]
        )
        
        if agent:
            execution_plan.append({
                "task": task,
                "agent_url": agent["url"]
            })
            print(f"🤖 Step {task['step']} → {agent.get('name', 'Unknown')} ({agent['url']})")
        else:
            print(f"⚠️  No agent found for step {task['step']}")
    
    # Step 3: Execute tasks on worker agents
    results = []
    print(f"\n⚡ Executing {len(execution_plan)} tasks...")
    
    for plan_item in execution_plan:
        task = plan_item["task"]
        agent_url = plan_item["agent_url"]
        
        print(f"   Executing step {task['step']} on {agent_url}...")
        
        result = execute_on_agent(
            agent_url,
            task["description"]
        )
        
        results.append({
            "step": task["step"],
            "description": task["description"],
            "result": result
        })
        
        if result.get("success"):
            print(f"   ✅ Step {task['step']} completed")
        else:
            print(f"   ❌ Step {task['step']} failed: {result.get('error')}")
    
    # Step 4: Aggregate results
    aggregator = Aggregator()
    final_output = aggregator.merge(results, user_goal)
    
    print(f"\n✨ Orchestration complete!\n")
    
    return [{
        "role": "assistant",
        "content": final_output
    }]


# Agent configuration
config = {
    "author": "prachetdevsingh@gmail.com",
    "name": "planner_agent",
    "description": "Orchestrates complex tasks across multiple specialized Bindu agents using capability-based discovery and task decomposition",
    "version": "1.0.0",
    "skills": ["skills/orchestration"],
    "deployment": {
        "url": "http://localhost:3774",
        "expose": True,
        "cors_origins": ["http://localhost:5173"]
    },
}

# Start the Bindu agent
bindufy(config, handler)
