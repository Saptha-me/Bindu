"""
Example M2M client for authenticating with Bindu agents using Auth0.

This client demonstrates how to:
1. Request an access token from Auth0
2. Cache the token for reuse
3. Make authenticated requests to Bindu agents
4. Handle token expiration and refresh

Setup:
1. Set environment variables:
   export AUTH0_DOMAIN="your-tenant.auth0.com"
   export AUTH0_CLIENT_ID="your-client-id"
   export AUTH0_CLIENT_SECRET="your-client-secret"
   export AUTH0_AUDIENCE="https://api.bindu.ai"
   export BINDU_AGENT_URL="http://localhost:8030"

2. Run the client:
   python m2m_client_example.py
"""

import os
import sys
import time
from typing import Optional

import requests


class BinduM2MClient:
    """M2M client for Auth0-authenticated Bindu agents."""

    def __init__(
        self,
        auth0_domain: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        audience: Optional[str] = None,
        agent_url: Optional[str] = None,
    ):
        """Initialize M2M client with Auth0 credentials.
        
        Args:
            auth0_domain: Auth0 tenant domain (e.g., 'your-tenant.auth0.com')
            client_id: M2M application client ID
            client_secret: M2M application client secret
            audience: API audience/identifier
            agent_url: Bindu agent URL
        """
        self.auth0_domain = auth0_domain or os.getenv("AUTH0_DOMAIN")
        self.client_id = client_id or os.getenv("AUTH0_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("AUTH0_CLIENT_SECRET")
        self.audience = audience or os.getenv("AUTH0_AUDIENCE")
        self.agent_url = agent_url or os.getenv("BINDU_AGENT_URL", "http://localhost:8030")
        
        # Token cache
        self._token: Optional[str] = None
        self._token_expires_at: float = 0
        
        # Validate configuration
        self._validate_config()
    
    def _validate_config(self) -> None:
        """Validate that all required configuration is present."""
        missing = []
        if not self.auth0_domain:
            missing.append("AUTH0_DOMAIN")
        if not self.client_id:
            missing.append("AUTH0_CLIENT_ID")
        if not self.client_secret:
            missing.append("AUTH0_CLIENT_SECRET")
        if not self.audience:
            missing.append("AUTH0_AUDIENCE")
        
        if missing:
            raise ValueError(
                f"Missing required configuration: {', '.join(missing)}. "
                f"Set environment variables or pass to constructor."
            )
    
    def _get_token(self) -> str:
        """Get valid access token, refreshing if needed.
        
        Returns:
            Valid JWT access token
            
        Raises:
            requests.HTTPError: If token request fails
        """
        current_time = time.time()
        
        # Return cached token if still valid (5 min buffer)
        if self._token and self._token_expires_at > (current_time + 300):
            print(f"Using cached token (expires in {int(self._token_expires_at - current_time)}s)")
            return self._token
        
        # Request new token from Auth0
        print(f"Requesting new token from Auth0...")
        token_url = f"https://{self.auth0_domain}/oauth/token"
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "audience": self.audience,
            "grant_type": "client_credentials"
        }
        
        try:
            response = requests.post(token_url, json=payload, timeout=10)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to get token from Auth0: {e}")
            raise
        
        token_data = response.json()
        self._token = token_data["access_token"]
        self._token_expires_at = current_time + token_data["expires_in"]
        
        print(f"✅ Token acquired (expires in {token_data['expires_in']}s)")
        return self._token
    
    def send_message(self, message: str, context_id: Optional[str] = None) -> dict:
        """Send message to Bindu agent.
        
        Args:
            message: Message text to send
            context_id: Optional context ID for conversation continuity
            
        Returns:
            JSON-RPC response from agent
            
        Raises:
            requests.HTTPError: If request fails
        """
        token = self._get_token()
        
        payload = {
            "jsonrpc": "2.0",
            "method": "message/send",
            "params": {
                "message": {
                    "context_id": context_id,
                    "parts": [{"text": message}],
                    "role": "user"
                }
            },
            "id": f"req-{int(time.time() * 1000)}"
        }
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        print(f"\n📤 Sending message to agent...")
        print(f"   Message: {message}")
        if context_id:
            print(f"   Context: {context_id}")
        
        try:
            response = requests.post(self.agent_url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"   Response: {e.response.text}")
            raise
        
        result = response.json()
        print(f"✅ Response received")
        return result
    
    def get_task(self, task_id: str) -> dict:
        """Get task details.
        
        Args:
            task_id: Task UUID
            
        Returns:
            Task details
        """
        token = self._get_token()
        
        payload = {
            "jsonrpc": "2.0",
            "method": "tasks/get",
            "params": {"task_id": task_id},
            "id": f"req-{int(time.time() * 1000)}"
        }
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(self.agent_url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        
        return response.json()
    
    def list_tasks(self, length: Optional[int] = None) -> dict:
        """List all tasks.
        
        Args:
            length: Optional limit on number of tasks
            
        Returns:
            List of tasks
        """
        token = self._get_token()
        
        params = {}
        if length:
            params["length"] = length
        
        payload = {
            "jsonrpc": "2.0",
            "method": "tasks/list",
            "params": params,
            "id": f"req-{int(time.time() * 1000)}"
        }
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(self.agent_url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        
        return response.json()


def main():
    """Example usage of M2M client."""
    print("=" * 60)
    print("Bindu M2M Client Example")
    print("=" * 60)
    
    try:
        # Initialize client
        print("\n1. Initializing M2M client...")
        client = BinduM2MClient()
        print(f"   Agent URL: {client.agent_url}")
        print(f"   Auth0 Domain: {client.auth0_domain}")
        print(f"   Audience: {client.audience}")
        
        # Send first message
        print("\n2. Sending first message...")
        result1 = client.send_message("Hello! What can you help me with?")
        
        if "result" in result1:
            task = result1["result"]
            print(f"   Task ID: {task['task_id']}")
            print(f"   Status: {task['status']['state']}")
        elif "error" in result1:
            print(f"   ❌ Error: {result1['error']['message']}")
            return
        
        # Send follow-up message (same context)
        print("\n3. Sending follow-up message...")
        context_id = result1["result"]["context_id"]
        result2 = client.send_message("Tell me a joke!", context_id=context_id)
        
        if "result" in result2:
            task = result2["result"]
            print(f"   Task ID: {task['task_id']}")
            print(f"   Status: {task['status']['state']}")
        
        # List tasks
        print("\n4. Listing recent tasks...")
        tasks_result = client.list_tasks(length=5)
        
        if "result" in tasks_result:
            tasks = tasks_result["result"]
            print(f"   Found {len(tasks)} tasks")
            for task in tasks:
                print(f"   - {task['task_id']}: {task['status']['state']}")
        
        print("\n" + "=" * 60)
        print("✅ All operations completed successfully!")
        print("=" * 60)
        
    except ValueError as e:
        print(f"\n❌ Configuration error: {e}")
        print("\nPlease set the following environment variables:")
        print("  - AUTH0_DOMAIN")
        print("  - AUTH0_CLIENT_ID")
        print("  - AUTH0_CLIENT_SECRET")
        print("  - AUTH0_AUDIENCE")
        print("  - BINDU_AGENT_URL (optional, defaults to http://localhost:8030)")
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Request failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
