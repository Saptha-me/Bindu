#!/usr/bin/env python
"""
Pebble Client Example

This example demonstrates how to interact with an agent deployed using the Pebble framework.
It shows how to make API calls to get the agent status and send messages to the agent.
"""

import argparse
import json
import sys
import uuid
from typing import Dict, Any, Optional
import requests


class PebbleClient:
    """Client for interacting with agents deployed with the Pebble framework."""
    
    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: Optional[str] = None
    ):
        """Initialize the client.
        
        Args:
            base_url: Base URL of the Pebble API server
            api_key: API key for authentication (if required)
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.session_id = str(uuid.uuid4())
        self.agent_id = None
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests.
        
        Returns:
            Dict[str, str]: Headers for API requests
        """
        headers = {
            "Content-Type": "application/json"
        }
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers
    
    def get_agent_status(self) -> Dict[str, Any]:
        """Get the status of the agent.
        
        Returns:
            Dict[str, Any]: Agent status information
        
        Raises:
            Exception: If the API request fails
        """
        url = f"{self.base_url}/agent/status"
        response = requests.get(url, headers=self._get_headers())
        
        if response.status_code != 200:
            raise Exception(f"Error getting agent status: {response.text}")
        
        status_data = response.json()
        self.agent_id = status_data.get("agent_id")
        return status_data
    
    def send_message(
        self,
        message: str,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        stream: bool = False
    ) -> Dict[str, Any]:
        """Send a message to the agent.
        
        Args:
            message: Message content to send
            session_id: Session ID for conversation continuity (uses self.session_id if not provided)
            metadata: Additional metadata for the request
            stream: Whether to stream the response
            
        Returns:
            Dict[str, Any]: Agent response
            
        Raises:
            Exception: If the agent_id is not set or the API request fails
        """
        if not self.agent_id:
            # Try to get the agent_id from status
            self.get_agent_status()
            if not self.agent_id:
                raise Exception("Agent ID not set. Call get_agent_status() first")
        
        url = f"{self.base_url}/agent/action"
        data = {
            "agent_id": self.agent_id,
            "session_id": session_id or self.session_id,
            "message": message,
            "stream": stream
        }
        
        if metadata:
            data["metadata"] = metadata
        
        response = requests.post(url, json=data, headers=self._get_headers())
        
        if response.status_code != 200:
            raise Exception(f"Error sending message: {response.text}")
        
        return response.json()


def main():
    """Run the example client."""
    parser = argparse.ArgumentParser(description="Pebble Client Example")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL of the Pebble API server")
    parser.add_argument("--api-key", help="API key for authentication")
    args = parser.parse_args()
    
    client = PebbleClient(base_url=args.url, api_key=args.api_key)
    
    try:
        # Get agent status
        print("Getting agent status...")
        status = client.get_agent_status()
        print(f"Connected to agent: {status['name']} (ID: {status['agent_id']})")
        print(f"Framework: {status['framework']}")
        print(f"Capabilities: {', '.join(status['capabilities'])}")
        print(f"Status: {status['status']}")
        print()
        
        # Start conversation
        print("Starting conversation with the agent...")
        print("Type 'exit' to quit, 'new' to start a new session.")
        print()
        
        while True:
            message = input("You: ")
            if message.lower() == "exit":
                break
            elif message.lower() == "new":
                client.session_id = str(uuid.uuid4())
                print(f"Started new session with ID: {client.session_id}")
                continue
            
            # Send message to agent
            try:
                response = client.send_message(message)
                print(f"\nAgent: {response['message']}")
                
                # Display tool calls if any
                if response.get("tool_calls"):
                    print("\nTool calls:")
                    for i, tool_call in enumerate(response["tool_calls"]):
                        print(f"  {i+1}. {tool_call.get('name', 'Unknown tool')}")
                        print(f"     Arguments: {json.dumps(tool_call.get('arguments', {}))}")
                        print(f"     Result: {tool_call.get('result', 'N/A')}")
                
                print()
            except Exception as e:
                print(f"Error: {str(e)}")
    
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
