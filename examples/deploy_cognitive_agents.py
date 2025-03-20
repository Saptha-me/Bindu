#!/usr/bin/env python
"""
Deploy Cognitive Agents Example

This example demonstrates how to deploy cognitive agents using the pebble framework with
protocol system integration. The agents will be deployed locally and accessible via 
cognitive API endpoints with token-based authentication.
"""

import sys
import pathlib
import uuid
from typing import Dict, Any, List

# Add parent directory to path to allow importing from utils
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
from utils.manage_secrets import ensure_env_file

# Import Agno agent components
from agno.agent import Agent as AgnoAgent
from agno.models.openai import OpenAIChat
from agno.tools.duckduckgo import DuckDuckGoTools

# Import pebble components
from pebble import deploy
from pebble.adapters.agno_cognitive_adapter import AgnoCognitiveAdapter
from pebble.api.auth import register_agent
from pebble.schemas.models import DeploymentConfig
from pebble.security.keys import get_secret_key, generate_api_key


def create_customer_agent():
    """Create a customer agent with a specific query."""
    
    agent = AgnoAgent(
        name="Customer",
        model=OpenAIChat(id="gpt-4o"),
        description="You are a customer looking to purchase a high-quality laptop for gaming and programming.",
        instructions=[
            "You are interested in performance, build quality, and value for money.",
            "You have a budget of around $1500-2000.",
            "You prefer laptops with good cooling systems and a nice screen.",
            "You want to ask questions to clarify your options.",
            "Be specific about your requirements and preferences."
        ],
        tools=[BasicTools(), DuckDuckGoTools()],
        show_tool_calls=True,
        markdown=True
    )
    
    # Wrap the Agno agent with our cognitive adapter
    return AgnoCognitiveAdapter(
        agent=agent,
        name="Customer Alex",
        metadata={
            "role": "customer",
            "personality": "detail-oriented, thoughtful, budget-conscious"
        }
    )


def create_sales_agent():
    """Create a sales agent to assist customers."""
    
    agent = AgnoAgent(
        name="Sales Representative",
        model=OpenAIChat(id="gpt-4o"),
        description="You are a knowledgeable sales representative for a computer store specializing in laptops.",
        instructions=[
            "Be helpful and informative about laptop specifications and features.",
            "Listen carefully to customer requirements and suggest appropriate options.",
            "Be honest about trade-offs between price and performance.",
            "Avoid overselling or pushing products that don't meet the customer's needs.",
            "Provide reasoning for your recommendations."
        ],
        tools=[BasicTools(), DuckDuckGoTools()],
        show_tool_calls=True,
        markdown=True
    )
    
    # Wrap the Agno agent with our cognitive adapter
    return AgnoCognitiveAdapter(
        agent=agent,
        name="Sales Rep Jordan",
        metadata={
            "role": "sales_representative",
            "personality": "helpful, knowledgeable, honest"
        }
    )


def main():
    """Run the cognitive agent deployment example."""
    
    # Ensure environment variables for API keys are set
    ensure_env_file()
    
    print("Creating cognitive Agno agents...")
    
    # Create our agents
    customer = create_customer_agent()
    sales_rep = create_sales_agent()
    
    # Generate API keys for each agent
    customer_api_key = generate_api_key()
    sales_rep_api_key = generate_api_key()
    
    # Register the agents with their API keys
    register_agent(customer_api_key, customer)
    register_agent(sales_rep_api_key, sales_rep)
    
    # Configure deployment settings
    config = DeploymentConfig(
        host="0.0.0.0",         # Host to bind to
        port=8000,              # Port to listen on
        cors_origins=["*"],     # CORS allowed origins
        enable_docs=True,       # Enable Swagger docs at /docs
        require_auth=True,      # Require authentication
        access_token_expire_minutes=30,  # Token expiration time
        api_key_expire_days=365  # API key expiration time
    )
    
    print("\nDeploying cognitive Agno agents with protocol-integrated pebblify...")
    
    # Deploy the server with our agents already registered
    deploy(
        host=config.host,
        port=config.port,
        cors_origins=config.cors_origins,
        enable_docs=config.enable_docs,
        require_auth=config.require_auth,
        include_cognitive_routes=True  # Enable cognitive routes
    )
    
    print("\nAPI Keys for accessing agents:")
    print(f"- Customer Agent: {customer_api_key}")
    print(f"- Sales Rep Agent: {sales_rep_api_key}")
    
    print("\nOnce the server is running, try these cognitive endpoints:")
    print("- POST /cognitive/act: Make an agent take action")
    print("- POST /cognitive/listen: Make an agent listen to verbal input")
    print("- POST /cognitive/see: Make an agent perceive visual input")
    print("- POST /cognitive/think: Make an agent think about a topic")
    print("- GET /cognitive/state: Get the current cognitive state of an agent")
    print("- GET /docs: Full API documentation")
    
    print("\nExample curl command to make the customer agent act:")
    print(f"""curl -X POST -H 'Content-Type: application/json' \\
    -H 'X-API-Key: {customer_api_key}' \\
    -d '{{
        "agent_id": "{customer.agent_id}",
        "session_id": "{uuid.uuid4()}",
        "content": "Approach the sales representative and ask about gaming laptops.",
        "stimulus_type": "action",
        "metadata": {{}}
    }}' \\
    http://localhost:8000/cognitive/act""")
    
    print("\nExample curl command to make the sales rep listen:")
    print(f"""curl -X POST -H 'Content-Type: application/json' \\
    -H 'X-API-Key: {sales_rep_api_key}' \\
    -d '{{
        "agent_id": "{sales_rep.agent_id}",
        "session_id": "{uuid.uuid4()}",
        "content": "I'm looking for a high-performance gaming laptop with good cooling.",
        "stimulus_type": "verbal",
        "metadata": {{"speaker": "Customer"}}
    }}' \\
    http://localhost:8000/cognitive/listen""")


if __name__ == "__main__":
    main()
