"""
Smart Research Assistant Agent for Bindu

A production-ready Bindu agent that researches topics from the internet,
synthesizes information, and returns structured responses with key insights
and source references.

This agent demonstrates:
- Official Bindu integration with bindufy decorator
- Agno agent framework with DuckDuckGo tools
- Robust LLM support (OpenAI and OpenRouter)
- Skills system for capability advertisement
- Error resilience with graceful degradation

Bindu provides the identity, communication & payments layer for AI agents.
This agent only needs to focus on its research capability.
"""

import os
import logging
from typing import Any
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ============================================================================
# Imports
# ============================================================================

# Official Bindu framework import
from bindu.penguin.bindufy import bindufy

# Agno agent framework imports
from agno.agent import Agent
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.models.openai import OpenAIChat
from agno.models.openrouter import OpenRouterChat

# ============================================================================
# Configuration (Bindu Standard Format)
# ============================================================================

# Official Bindu agent configuration
CONFIG = {
    "author": "ughademayur67@gmail.com",  
    "name": "smart_research_agent",
    "description": "An intelligent research assistant that searches the internet and synthesizes information into structured responses with key insights and sources.",
    "deployment": {
        "url": "http://localhost:3773",
        "expose": False  # Set to True to expose via tunnel
    },
    "skills": [
        "skills/question-answering",
        "skills/web-research",
        "skills/information-synthesis"
    ]
}

# ============================================================================
# Environment Configuration
# ============================================================================

# Official Bindu env vars for LLM
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")  # Accessible by default

# Search configuration
SEARCH_MAX_RESULTS = int(os.getenv("SEARCH_MAX_RESULTS", "10"))
SEARCH_TIMEOUT = int(os.getenv("SEARCH_TIMEOUT", "30"))


# ============================================================================
# Utility Functions
# ============================================================================

def get_llm_model() -> Any:
    """
    Initialize LLM model with Agno framework.
    Tries OpenAI first, falls back to OpenRouter.
    
    Returns:
        Agno model instance (OpenAIChat or OpenRouterChat)
        
    Raises:
        ValueError: If no API key is configured
    """
    if OPENAI_API_KEY:
        logger.info(f"Initializing OpenAI model: {LLM_MODEL}")
        return OpenAIChat(id=LLM_MODEL, api_key=OPENAI_API_KEY)
    
    elif OPENROUTER_API_KEY:
        logger.info(f"Initializing OpenRouter model: {LLM_MODEL}")
        return OpenRouterChat(id=LLM_MODEL, api_key=OPENROUTER_API_KEY)
    
    else:
        raise ValueError(
            "No LLM API key configured. "
            "Set OPENAI_API_KEY or OPENROUTER_API_KEY environment variable."
        )


def parse_research_response(response: str) -> dict:
    """
    Parse agent response into structured components.
    
    Args:
        response: The raw response from the Agno agent
        
    Returns:
        Dictionary with summary, key_points, and sources
    """
    result = {
        "summary": "",
        "key_points": [],
        "sources": []
    }
    
    if not response:
        return result
    
    # Try to parse structured sections from response
    sections = response.split("##")
    
    for section in sections:
        section = section.strip()
        if section.startswith("Summary"):
            content = section.replace("Summary", "", 1).strip()
            result["summary"] = content.split("\n")[0][:500]
            
        elif section.startswith("Key Points") or section.startswith("Key Insights"):
            content = section.replace("Key Points", "", 1).replace("Key Insights", "", 1).strip()
            lines = [l.strip() for l in content.split("\n") if l.strip().startswith(("-", "•", "*", "1", "2", "3"))]
            result["key_points"] = [l.lstrip("-•*0123456789. ").strip() for l in lines][:6]
            
        elif section.startswith("Sources"):
            content = section.replace("Sources", "", 1).strip()
            sources = [s.strip() for s in content.split("\n") if s.strip() and len(s.strip()) > 5]
            result["sources"] = sources[:10]
    
    # Fallback: if no structured sections, use first few lines as summary
    if not result["summary"] and response:
        result["summary"] = response.split("\n")[0][:500]
    
    return result


def create_research_agent() -> Agent:
    """
    Create and configure the research agent using Agno framework.
    
    Returns:
        Configured Agno Agent instance
        
    Raises:
        ValueError: If LLM is not properly configured
    """
    logger.info("Creating Smart Research Assistant Agent")
    
    # Get LLM model
    try:
        model = get_llm_model()
    except ValueError as e:
        logger.error(f"Failed to initialize LLM: {e}")
        raise
    
    # Create agent with research capabilities
    agent = Agent(
        name="ResearchAssistant",
        model=model,
        tools=[DuckDuckGoTools()],
        instructions="""
You are an expert research assistant. For each user question:

1. Search for relevant, current information using available tools
2. Synthesize findings into a clear, well-structured answer
3. Extract 4-6 key insights and important points
4. Provide accurate source attribution
5. Ensure information is recent and reliable

Always structure your response with:

## Summary
Provide a 2-3 sentence overview of the key findings.

## Key Points
List 4-6 important insights, each as a separate point.

## Sources
List the sources you found, with brief descriptions.
""",
        markdown=True,
        show_tool_calls=False,
    )
    
    logger.info("Agent created successfully")
    return agent


# ============================================================================
# Handler Function (Bindu Entry Point)
# ============================================================================

def handler(messages: list[dict[str, str]]) -> dict[str, Any]:
    """
    Main handler function for the Smart Research Assistant agent.
    
    Bindu entry point that receives messages and returns research results.
    Matches official Bindu handler signature and response format.
    
    Args:
        messages: List of message dictionaries with 'role' and 'content' keys.
                  Example: [{\"role\": \"user\", \"content\": \"What is AI?\"}]
    
    Returns:
        Dictionary with status, response data, and optional error message.
        Response includes summary, key_points, sources, and timestamp.
    """
    try:
        # Extract latest user message
        user_message = None
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_message = msg.get("content", "").strip()
                break
        
        if not user_message:
            return {
                "status": "error",
                "response": None,
                "error": "No user message found"
            }
        
        logger.info(f"Processing research query: {user_message[:80]}...")
        
        # Create research agent
        agent = create_research_agent()
        
        # Execute research
        logger.info("Executing research workflow")
        agent_response = agent.run(user_message)
        
        # Extract and parse response
        response_text = str(agent_response) if agent_response else ""
        parsed = parse_research_response(response_text)
        
        # Return structured result
        return {
            "status": "success",
            "response": {
                "summary": parsed["summary"] or "Research completed but summary unavailable.",
                "key_points": parsed["key_points"],
                "sources": parsed["sources"],
                "timestamp": datetime.utcnow().isoformat() + "Z"
            },
            "error": None
        }
        
    except Exception as e:
        logger.error(f"Handler error: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "response": None,
            "error": str(e)
        }


# ============================================================================
# Bindu Registration
# ============================================================================

# Register agent with Bindu framework
# This makes the agent discoverable and deployable
bindufy(config=CONFIG, handler_func=handler)


# ============================================================================
# Demo & Testing (for local development only)
# ============================================================================

if __name__ == "__main__":
    """
    Local demo mode for testing the agent without full Bindu deployment.
    
    Usage:
      python agent.py --demo
    """
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        print("\n" + "="*80)
        print("SMART RESEARCH ASSISTANT - DEMO MODE")
        print("="*80 + "\n")
        
        # Check API key
        if not (OPENAI_API_KEY or OPENROUTER_API_KEY):
            print("⚠️  ERROR: No LLM API key configured\n")
            print("Set one of:")
            print("  export OPENAI_API_KEY='sk-...'")
            print("  export OPENROUTER_API_KEY='sk-...'")
            print("\nThen rerun: python agent.py --demo\n")
            sys.exit(1)
        
        # Run demo query
        demo_query = "What are the latest developments in AI agents?"
        print(f"📝 Query: {demo_query}\n")
        print("-" * 80 + "\n")
        
        messages = [{"role": "user", "content": demo_query}]
        result = handler(messages)
        
        if result["status"] == "success":
            res = result["response"]
            print("✅ SUCCESS\n")
            print(f"Summary:\n{res['summary']}\n")
            
            if res['key_points']:
                print("Key Points:")
                for i, point in enumerate(res['key_points'], 1):
                    print(f"  {i}. {point}")
            
            if res['sources']:
                print("\nSources:")
                for source in res['sources'][:5]:
                    print(f"  • {source}")
        else:
            print(f"❌ ERROR\n{result['error']}")
        
        print("\n" + "="*80 + "\n")
    
    else:
        print("\n" + "="*80)
        print("Smart Research Assistant Agent (Bindu)")
        print("="*80)
        print(f"Name: {CONFIG['name']}")
        print(f"Author: {CONFIG['author']}")
        print(f"Skills: {', '.join(CONFIG['skills'])}")
        print(f"Status: Ready for deployment\n")
        print("Usage:")
        print("  python agent.py --demo          # Test locally")
        print("  uv run python agent.py          # Deploy with Bindu")
        print("\n" + "="*80 + "\n")
