#!/usr/bin/env python3
"""Example demonstrating two Pebbling agents talking to each other."""

import asyncio
import json
from typing import Dict, Any
from textwrap import dedent

from agno.agent import Agent
from agno.models.openai import OpenAIChat

from pebbling.core.protocol import CoreProtocolMethod
from pebbling.server.pebbling_server import pebblify
from pebbling.security import with_did
from pebbling.server.server_utils import create_secure_client_session, send_secure_request
from loguru import logger
import ssl


@with_did(key_path="keys/teacher_key.json", endpoint="https://teacher-agent.example.com/pebble")
def teacher_agent():
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


@with_did(key_path="keys/student_key.json", endpoint="https://student-agent.example.com/pebble")
def student_agent():
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


async def run_agent(agent_factory, agent_name, port, host="localhost"):
    """Run an agent with pebbling server.
    
    Args:
        agent_factory: Function that creates the agent
        agent_name: Name for the agent
        port: Port for the agent server
        host: Host for the agent server
        
    Returns:
        The agent instance with server running
    """
    # Create the agent
    agent = agent_factory()
    
    logger.info(f"Starting {agent_name} agent on port {port}")
    
    # List of supported methods
    supported_methods = [
        CoreProtocolMethod.CONTEXT,
        CoreProtocolMethod.LISTEN,
        CoreProtocolMethod.ACT,
    ]
    
    # Start the server with security enabled
    # Instead of awaiting directly, which would block, we create a task
    asyncio.create_task(pebblify(
        agent=agent,
        supported_methods=supported_methods,
        pebbling_port=port,
        user_port=port+1,
        host=host,
        did_manager=agent.pebble_did_manager,
        enable_security=True,
        enable_mtls=True,
        cert_path="keys/",
        register_with_hibiscus=True,
        agent_name=agent_name,
        agent_description=f"Example {agent_name} agent for demonstration",
    ))
    
    # Return the agent immediately
    return agent


async def send_message(source_agent, target_url, message_content):
    """Send a message from one agent to another.
    
    Args:
        source_agent: The agent sending the message
        target_url: URL of the target agent
        message_content: Message content to send
        
    Returns:
        Response from the target agent
    """
    logger.info(f"Sending message to {target_url}: {message_content}")
    
    try:
        # Get the agent's DID for security
        did = source_agent.pebble_did
        
        # Get proper SSL context for mTLS
        if hasattr(source_agent, 'pebble_cert_manager'):
            ssl_context = source_agent.pebble_cert_manager.get_client_ssl_context()
        else:
            # Fallback - create a default SSL context that accepts self-signed certs
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
        
        # Create a secure session - note that we need to await this!
        session = await create_secure_client_session(ssl_context)
        
        # Use the session
        try:
            # Prepare the message payload
            data = {
                "jsonrpc": "2.0",
                "method": "listen",
                "params": {
                    "messages": [{"role": "user", "content": message_content}]
                },
                "id": 1
            }
            
            # Send the request
            response = await send_secure_request(
                session=session,
                url=f"{target_url}/jsonrpc",
                json_data=data
            )
            
            return response
        finally:
            # Make sure to close the session when done
            await session.close()
            
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        return {"status": "error", "message": str(e)}


async def conversation_demo():
    """Demonstrate a conversation between two agents."""
    logger.info("Starting agent conversation demo")
    
    # Start teacher agent on port 3773
    teacher = await run_agent(
        agent_factory=teacher_agent,
        agent_name="Teacher",
        port=3773
    )
    
    # Start student agent on port 3775
    student = await run_agent(
        agent_factory=student_agent,
        agent_name="Student",
        port=3775
    )
    
    # Allow time for servers to start
    await asyncio.sleep(2)
    
    # Start the conversation with student asking a question
    logger.info("Beginning conversation")
    
    # Student asks a question
    question = "Can you explain the concept of neural networks in a simple way?"
    response = await send_message(
        source_agent=student,
        target_url="https://localhost:3773",
        message_content=question
    )
    
    # Extract teacher's explanation
    teacher_explanation = response.get("result", {}).get("response", "No response")
    logger.info(f"Teacher explains: {teacher_explanation}")
    
    # Student follows up with another question
    follow_up = f"Thanks! Based on that explanation, how do neural networks learn from data?"
    response = await send_message(
        source_agent=student,
        target_url="https://localhost:3773",
        message_content=follow_up
    )
    
    # Extract teacher's follow-up explanation
    teacher_follow_up = response.get("result", {}).get("response", "No response")
    logger.info(f"Teacher explains further: {teacher_follow_up}")
    
    # Student summarizes what they learned
    summary = f"Let me summarize what I've learned about neural networks."
    response = await send_message(
        source_agent=teacher,
        target_url="https://localhost:3775",
        message_content=summary
    )
    
    # Extract student's summary
    student_summary = response.get("result", {}).get("response", "No response")
    logger.info(f"Student summarizes: {student_summary}")
    
    logger.info("Conversation demo completed")


if __name__ == "__main__":
    # Configure logging
    logger.remove()
    logger.add(lambda msg: print(msg, end=""), colorize=True, level="INFO")
    
    # Run the demo
    asyncio.run(conversation_demo())
