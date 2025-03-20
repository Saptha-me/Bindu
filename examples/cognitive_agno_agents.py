#!/usr/bin/env python
"""
Cognitive Agno Agents Communication Example

This example demonstrates how two Agno agents can communicate with each other using the
cognitive protocol extension. The agents will use various cognitive methods (act, listen, see, think)
to interact with each other and their environment.
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
from pebble.adapters.agno_cognitive_adapter import AgnoCognitiveAdapter
from pebble.schemas.cognitive_models import (
    CognitiveRequest,
    CognitiveResponse,
    StimulusType
)


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
        tools=[DuckDuckGoTools()],
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
        tools=[DuckDuckGoTools()],
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


def simulate_conversation(customer: AgnoCognitiveAdapter, sales_rep: AgnoCognitiveAdapter, 
                         store_environment: str):
    """Simulate a conversation between a customer and sales representative in a store.
    
    Args:
        customer: The customer agent
        sales_rep: The sales representative agent
        store_environment: Description of the store environment
    """
    # Create a unique session ID for this conversation
    session_id = uuid.uuid4()
    
    print("\n=== Starting Cognitive Agent Conversation ===\n")
    
    # Step 1: Both agents perceive the environment (see)
    print(f"🌎 Environment: {store_environment}")
    
    customer_perception = customer.see(CognitiveRequest(
        session_id=session_id,
        content=store_environment,
        stimulus_type=StimulusType.VISUAL,
        metadata={"location": "Computer Store"}
    ))
    
    sales_rep_perception = sales_rep.see(CognitiveRequest(
        session_id=session_id,
        content=store_environment,
        stimulus_type=StimulusType.VISUAL,
        metadata={"location": "Computer Store"}
    ))
    
    print(f"\n👤 {customer.name} (perceiving environment): {customer_perception.content[:150]}...\n")
    print(f"👨‍💼 {sales_rep.name} (perceiving environment): {sales_rep_perception.content[:150]}...\n")
    
    # Step 2: Sales rep thinks about approach
    sales_thinking = sales_rep.think(CognitiveRequest(
        session_id=session_id,
        content="How should I approach this customer? What questions should I ask to understand their needs?",
        stimulus_type=StimulusType.THOUGHT,
        metadata={"customer_appearance": "A person looking at gaming laptops"}
    ))
    
    print(f"🧠 {sales_rep.name} (thinking): {sales_thinking.content[:200]}...\n")
    
    # Step 3: Sales rep initiates conversation
    sales_greeting = sales_rep.act(CognitiveRequest(
        session_id=session_id,
        content="Approach the customer and introduce yourself, offering assistance.",
        stimulus_type=StimulusType.ACTION,
        metadata={}
    ))
    
    print(f"👨‍💼 {sales_rep.name}: {sales_greeting.content}\n")
    
    # Step 4: Customer listens and responds
    customer_response = customer.listen_and_act(CognitiveRequest(
        session_id=session_id,
        content=sales_greeting.content,
        stimulus_type=StimulusType.VERBAL,
        metadata={
            "speaker": sales_rep.name,
            "action_instruction": "Respond to the sales representative's greeting and explain what you're looking for."
        }
    ))
    
    print(f"👤 {customer.name}: {customer_response.content}\n")
    
    # Step 5: Sales rep listens and thinks
    sales_rep_listening = sales_rep.listen(CognitiveRequest(
        session_id=session_id,
        content=customer_response.content,
        stimulus_type=StimulusType.VERBAL,
        metadata={"speaker": customer.name}
    ))
    
    sales_rep_thinking = sales_rep.think(CognitiveRequest(
        session_id=session_id,
        content=f"What laptop options would best meet this customer's needs? Consider: {customer_response.content}",
        stimulus_type=StimulusType.THOUGHT,
        metadata={}
    ))
    
    print(f"🧠 {sales_rep.name} (thinking): {sales_rep_thinking.content[:200]}...\n")
    
    # Step 6: Sales rep responds with recommendations
    sales_rep_recommendation = sales_rep.act(CognitiveRequest(
        session_id=session_id,
        content="Provide laptop recommendations based on the customer's requirements.",
        stimulus_type=StimulusType.ACTION,
        metadata={}
    ))
    
    print(f"👨‍💼 {sales_rep.name}: {sales_rep_recommendation.content}\n")
    
    # Step 7: Customer thinks about the recommendations
    customer_thinking = customer.think(CognitiveRequest(
        session_id=session_id,
        content=f"Are these recommendations aligning with my needs? What specific questions should I ask? Considering: {sales_rep_recommendation.content}",
        stimulus_type=StimulusType.THOUGHT,
        metadata={}
    ))
    
    print(f"🧠 {customer.name} (thinking): {customer_thinking.content[:200]}...\n")
    
    # Step 8: Customer asks follow-up questions
    customer_followup = customer.act(CognitiveRequest(
        session_id=session_id,
        content="Ask specific follow-up questions about the recommended laptops.",
        stimulus_type=StimulusType.ACTION,
        metadata={}
    ))
    
    print(f"👤 {customer.name}: {customer_followup.content}\n")
    
    # Step 9: Sales rep responds to follow-up
    sales_rep_response = sales_rep.listen_and_act(CognitiveRequest(
        session_id=session_id,
        content=customer_followup.content,
        stimulus_type=StimulusType.VERBAL,
        metadata={
            "speaker": customer.name,
            "action_instruction": "Respond to the customer's follow-up questions with detailed information."
        }
    ))
    
    print(f"👨‍💼 {sales_rep.name}: {sales_rep_response.content}\n")
    
    # Step 10: Customer makes a decision
    customer_decision = customer.listen_and_act(CognitiveRequest(
        session_id=session_id,
        content=sales_rep_response.content,
        stimulus_type=StimulusType.VERBAL,
        metadata={
            "speaker": sales_rep.name,
            "action_instruction": "Make a decision about which laptop you want to purchase, if any."
        }
    ))
    
    print(f"👤 {customer.name}: {customer_decision.content}\n")
    
    # Step 11: Sales rep concludes the interaction
    sales_rep_conclusion = sales_rep.listen_and_act(CognitiveRequest(
        session_id=session_id,
        content=customer_decision.content,
        stimulus_type=StimulusType.VERBAL,
        metadata={
            "speaker": customer.name,
            "action_instruction": "Conclude the interaction based on the customer's decision."
        }
    ))
    
    print(f"👨‍💼 {sales_rep.name}: {sales_rep_conclusion.content}\n")
    
    print("\n=== Conversation Complete ===\n")
    
    # Return the full conversation for analysis
    return {
        "session_id": session_id,
        "customer_cognitive_state": customer.cognitive_state,
        "sales_rep_cognitive_state": sales_rep.cognitive_state
    }


def main():
    """Run the cognitive agent communication example."""
    
    # Ensure environment variables for API keys are set
    ensure_env_file()
    
    print("Creating Agno agents with cognitive capabilities...")
    
    # Create our agents
    customer = create_customer_agent()
    sales_rep = create_sales_agent()
    
    # Define the store environment
    store_environment = """
    A modern computer store with a wide selection of laptops arranged on display tables. 
    The gaming section features high-performance laptops with RGB lighting and large screens.
    The professional section showcases sleek ultrabooks and powerful workstations.
    Price tags and specification sheets are visible next to each laptop.
    The store has a testing area where customers can try out the laptops.
    """
    
    # Run the conversation simulation
    result = simulate_conversation(customer, sales_rep, store_environment)
    
    # Display cognitive state summary
    print("\n=== Cognitive State Summary ===\n")
    print(f"Customer Agent ({customer.name}):")
    print(f"- Episodic Memory Events: {len(customer.cognitive_state['episodic_memory'])}")
    print(f"- Final Attention: {customer.cognitive_state['attention']}")
    
    print(f"\nSales Rep Agent ({sales_rep.name}):")
    print(f"- Episodic Memory Events: {len(sales_rep.cognitive_state['episodic_memory'])}")
    print(f"- Final Attention: {sales_rep.cognitive_state['attention']}")


if __name__ == "__main__":
    main()
