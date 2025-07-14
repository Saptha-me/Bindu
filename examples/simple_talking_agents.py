#!/usr/bin/env python3
"""Example demonstrating two Pebbling agents talking to each other using HTTP."""

import asyncio
import json
from textwrap import dedent

from agno.agent import Agent
from agno.models.openai import OpenAIChat

from pebbling.core.protocol import CoreProtocolMethod
from pebbling.server.pebbling_server import pebblify
from pebbling.security import with_did
from loguru import logger

# Define constants
LOCALHOST = "127.0.0.1"
TEACHER_PORT = 3773
STUDENT_PORT = 3775


@with_did(key_path="keys/teacher_key.json", endpoint=f"http://{LOCALHOST}:{TEACHER_PORT}/pebble")
def create_teacher_agent():
    """Create a teacher agent with a helpful personality."""
    return Agent(
        model=OpenAIChat(id="gpt-4o"),
        instructions=dedent(
            """\
            You are a knowledgeable and patient teacher.
            You explain complex topics in a clear, concise manner.
            You use analogies and examples to make concepts easier to understand.
            You are encouraging and supportive of learning.
            """
        ),
        markdown=True,
    )


@with_did(key_path="keys/student_key.json", endpoint=f"http://{LOCALHOST}:{STUDENT_PORT}/pebble")
def create_student_agent():
    """Create a student agent with a curious personality."""
    return Agent(
        model=OpenAIChat(id="gpt-4o"),
        instructions=dedent(
            """\
            You are a curious student eager to learn.
            You ask thoughtful questions to deepen your understanding.
            You try to connect new concepts with things you already know.
            You summarize what you've learned to check your understanding.
            """
        ),
        markdown=True,
    )


async def send_jsonrpc_request(url, method, params):
    """Send a JSON-RPC request using aiohttp.
    
    Args:
        url: Target URL
        method: JSON-RPC method to call
        params: Parameters for the method
        
    Returns:
        Response data
    """
    import aiohttp
    
    logger.info(f"Sending request to {url}: method={method}")
    
    try:
        async with aiohttp.ClientSession() as session:
            # Prepare JSON-RPC request
            payload = {
                "jsonrpc": "2.0",
                "method": method,
                "params": params,
                "id": 1
            }
            
            # Send request
            async with session.post(url, json=payload) as response:
                # Parse response
                result = await response.json()
                return result
                
    except Exception as e:
        logger.error(f"Error sending request: {e}")
        return {"error": {"message": str(e)}}


async def setup_teacher_agent():
    """Set up and start the teacher agent server."""
    # Create the agent
    agent = create_teacher_agent()
    
    logger.info(f"Teacher Agent DID: {agent.pebble_did}")
    
    # Supported methods
    supported_methods = [
        CoreProtocolMethod.CONTEXT,
        CoreProtocolMethod.LISTEN,
        CoreProtocolMethod.ACT,
    ]
    
    # Start the server - using create_task to avoid blocking
    asyncio.create_task(pebblify(
        agent=agent,
        supported_methods=supported_methods,
        pebbling_port=TEACHER_PORT,
        user_port=TEACHER_PORT+1,
        host=LOCALHOST,
        # Security configuration - DISABLED for simplicity
        enable_security=False,
        enable_mtls=False,
        # Agent metadata
        agent_name="teacher-agent",
        agent_description="A knowledgeable and patient teacher agent",
    ))
    
    return agent


async def setup_student_agent():
    """Set up and start the student agent server."""
    # Create the agent
    agent = create_student_agent()
    
    logger.info(f"Student Agent DID: {agent.pebble_did}")
    
    # Supported methods
    supported_methods = [
        CoreProtocolMethod.CONTEXT,
        CoreProtocolMethod.LISTEN,
        CoreProtocolMethod.ACT,
    ]
    
    # Start the server - using create_task to avoid blocking
    asyncio.create_task(pebblify(
        agent=agent,
        supported_methods=supported_methods,
        pebbling_port=STUDENT_PORT,
        user_port=STUDENT_PORT+1,
        host=LOCALHOST,
        # Security configuration - DISABLED for simplicity
        enable_security=False,
        enable_mtls=False,
        # Agent metadata
        agent_name="student-agent",
        agent_description="A curious student agent eager to learn",
    ))
    
    return agent


async def demo_conversation():
    """Demonstrate a conversation between teacher and student agents."""
    logger.info("Starting agent conversation demo")
    
    # Start both agents
    teacher = await setup_teacher_agent()
    student = await setup_student_agent()
    
    # Allow time for servers to start - longer wait to ensure they're ready
    logger.info("Waiting for servers to start...")
    await asyncio.sleep(5)
    
    # JSON-RPC endpoints - using HTTP instead of HTTPS
    teacher_rpc_url = f"http://{LOCALHOST}:{TEACHER_PORT}/jsonrpc"
    student_rpc_url = f"http://{LOCALHOST}:{STUDENT_PORT}/jsonrpc"
    
    # Student asks a question about neural networks
    question = "Can you explain the concept of neural networks in a simple way?"
    logger.info(f"Student asks: {question}")
    
    response = await send_jsonrpc_request(
        url=teacher_rpc_url,
        method="act",
        params={"messages": [{"role": "user", "content": question}]}
    )
    
    teacher_response = response.get("result", {}).get("response", "No response")
    logger.info(f"Teacher explains: {teacher_response}")
    
    # Student asks a follow-up question
    follow_up = "Thanks! How do neural networks actually learn from data?"
    logger.info(f"Student asks follow-up: {follow_up}")
    
    response = await send_jsonrpc_request(
        url=teacher_rpc_url,
        method="act",
        params={"messages": [{"role": "user", "content": follow_up}]}
    )
    
    teacher_response2 = response.get("result", {}).get("response", "No response")
    logger.info(f"Teacher explains further: {teacher_response2}")
    
    # Teacher asks student to summarize
    prompt = "Can you summarize what you've learned about neural networks?"
    logger.info(f"Teacher asks: {prompt}")
    
    response = await send_jsonrpc_request(
        url=student_rpc_url,
        method="act",
        params={"messages": [{"role": "user", "content": prompt}]}
    )
    
    student_summary = response.get("result", {}).get("response", "No response")
    logger.info(f"Student summarizes: {student_summary}")
    
    logger.info("Conversation demo completed")


async def main():
    """Main function to run the example."""
    # Configure logging
    logger.remove()
    logger.add(lambda msg: print(msg, end=""), colorize=True, level="INFO")
    
    # Create directories if they don't exist
    import os
    os.makedirs("keys", exist_ok=True)
    
    # Run the demo
    await demo_conversation()


if __name__ == "__main__":
    asyncio.run(main())
