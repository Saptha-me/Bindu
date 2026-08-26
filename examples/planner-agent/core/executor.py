"""Agent-to-Agent communication via HTTP/JSON-RPC protocol."""

import requests
from typing import Dict


def execute_on_agent(agent_url: str, task_description: str) -> Dict:
    """
    Execute a task on a remote Bindu agent using JSON-RPC protocol.
    
    Args:
        agent_url: Base URL of the agent (e.g., http://localhost:3775)
        task_description: The task to execute
    
    Returns:
        Dict with structure:
        {
            "success": bool,
            "content": str (if success),
            "error": str (if failure),
            "agent_url": str
        }
    """
    payload = {
        "jsonrpc": "2.0",
        "method": "message/send",
        "params": {
            "message": {
                "role": "user",
                "content": task_description
            }
        },
        "id": 1
    }
    
    try:
        response = requests.post(
            f"{agent_url}/",  # Bindu agents listen on root endpoint
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        response.raise_for_status()
        
        data = response.json()
        
        # Extract content from JSON-RPC response
        if "result" in data and "messages" in data["result"]:
            return {
                "success": True,
                "content": data["result"]["messages"][-1]["content"],
                "agent_url": agent_url
            }
        
        return {
            "success": False,
            "error": "Invalid response format",
            "agent_url": agent_url
        }
    
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "error": "Request timeout",
            "agent_url": agent_url
        }
    except requests.exceptions.ConnectionError:
        return {
            "success": False,
            "error": "Connection failed - agent may not be running",
            "agent_url": agent_url
        }
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": str(e),
            "agent_url": agent_url
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "agent_url": agent_url
        }
