"""Example Bindu agent with Notion OAuth integration.

This example demonstrates how to create an agent that requires Notion
credentials and uses them to search the user's workspace.
"""

import asyncio
import os
from typing import Any

from bindu.penguin.bindufy import bindufy


# Agent configuration with credential requirements
config = {
    "author": os.getenv("USER_EMAIL", "user@example.com"),
    "name": "notion_search_agent",
    "description": "Search your Notion workspace for information",
    "deployment": {
        "url": "http://localhost:3773",
        "expose": True,
    },
    # NEW: Credential requirements
    "credential_requirements": {
        "notion": {
            "type": "oauth2",
            "provider": "notion",
            "scopes": ["read_content", "search"],
            "required": True,
            "description": "Access your Notion workspace to search for documents and pages"
        }
    },
}


async def handler(context: dict[str, Any]) -> dict[str, Any]:
    """Agent handler with Notion credential access.
    
    Args:
        context: Agent context including:
            - messages: User messages
            - credentials: OAuth credentials (if authorized)
            - user: User information
    
    Returns:
        Agent response
    """
    messages = context.get("messages", [])
    credentials = context.get("credentials", {})
    user = context.get("user", {})
    
    # Get the last user message
    if not messages:
        return {
            "role": "assistant",
            "parts": [{"kind": "text", "text": "Please send a message to search Notion."}]
        }
    
    last_message = messages[-1]
    user_query = ""
    for part in last_message.get("parts", []):
        if part.get("kind") == "text":
            user_query = part.get("text", "")
            break
    
    # Check if we have Notion credentials
    if "notion" not in credentials:
        return {
            "role": "assistant",
            "parts": [{
                "kind": "text",
                "text": "❌ Notion credentials not found. Please authorize Notion access first."
            }],
            "error": "authorization_required",
            "missing_providers": ["notion"]
        }
    
    # Get Notion access token
    notion_token = credentials["notion"]["access_token"]
    workspace_name = credentials["notion"].get("workspace_name", "your workspace")
    
    # Simulate Notion search (replace with actual Notion API call)
    # In production, you would use the Notion SDK or API
    try:
        # Example: Search Notion using the token
        # from notion_client import Client
        # notion = Client(auth=notion_token)
        # results = notion.search(query=user_query).get("results", [])
        
        # For this example, we'll return a mock response
        response_text = f"""
🔍 **Searching Notion workspace: {workspace_name}**

Query: "{user_query}"

📄 **Mock Results:**
1. **Project Planning** - Updated 2 days ago
   - Contains information about project timelines and milestones
   
2. **Meeting Notes** - Updated 1 week ago
   - Team sync notes mentioning related topics

3. **Documentation** - Updated 3 weeks ago
   - Technical documentation for the project

💡 **Note:** This is a mock response. In production, this would search your actual Notion workspace using the Notion API.

**Credentials verified:**
- ✅ Notion access token: {notion_token[:20]}...
- ✅ Workspace: {workspace_name}
- ✅ User: {user.get('email', 'Unknown')}
"""
        
        return {
            "role": "assistant",
            "parts": [{"kind": "text", "text": response_text}]
        }
        
    except Exception as e:
        return {
            "role": "assistant",
            "parts": [{
                "kind": "text",
                "text": f"❌ Error searching Notion: {str(e)}"
            }]
        }


if __name__ == "__main__":
    print("🌻 Starting Notion Search Agent...")
    print("=" * 50)
    print()
    print("This agent requires Notion OAuth authorization.")
    print("If you haven't authorized yet, you'll receive an authorization URL.")
    print()
    print("Configuration:")
    print(f"  - Agent: {config['name']}")
    print(f"  - URL: {config['deployment']['url']}")
    print(f"  - Required: Notion OAuth")
    print()
    print("=" * 50)
    print()
    
    # Bindufy the agent
    bindufy(config, handler)
