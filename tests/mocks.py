"""Mock objects for testing."""

import json
from typing import Any, Callable, Dict, Optional
from uuid import UUID


class MockAgent:
    """Mock agent for testing different response types."""

    def __init__(self, response: str = "Test response", response_type: str = "normal"):
        """Initialize mock agent.

        Note: This is an __init__ method for a mock test object.

        Args:
            response: The response text to return
            response_type: Type of response - "normal", "input-required", "auth-required", "error"
        """
        self.response = response
        self.response_type = response_type
        self.call_count = 0
        self.last_input = None

    def __call__(self, message: str) -> str:
        """Execute the mock agent."""
        self.call_count += 1
        self.last_input = message

        if self.response_type == "error":
            raise ValueError(self.response)
        elif self.response_type == "input-required":
            return json.dumps({"state": "input-required", "prompt": self.response})
        elif self.response_type == "auth-required":
            return json.dumps(
                {
                    "state": "auth-required",
                    "prompt": self.response,
                    "auth_type": "api_key",
                    "service": "test_service",
                }
            )
        else:
            return self.response


class MockManifest:
    """Mock AgentManifest for testing."""

    def __init__(
        self,
        agent_fn: Optional[Callable] = None,
        name: str = "Test Agent",
        description: str = "A test agent",
        version: str = "1.0.0",
        capabilities: Optional[Dict[str, Any]] = None,
    ):
        """Initialize mock manifest.

        Note: This is an __init__ method for a mock test object.
        """
        self.id = UUID("550e8400-e29b-41d4-a716-446655440000")
        self.name = name
        self.description = description
        self.version = version
        self.kind = "agent"
        self.skills = []
        self.capabilities = capabilities or {}
        self.num_history_sessions = 10
        self.extra_data = {}
        self.debug_mode = False
        self.debug_level = 1
        self.monitoring = False
        self.telemetry = False
        self.agent_trust = {
            "identity_provider": "custom",
            "inherited_roles": [],
            "creator_id": "test",
            "creation_timestamp": 0,
            "trust_verification_required": False,
            "allowed_operations": {},
        }
        self.agent_fn = agent_fn or MockAgent()
        self.did_extension = None

        # Manifest configuration attributes
        self.enable_system_message = True
        self.enable_context_based_history = False

    def run(self, message_history: list):
        """Run the agent synchronously.

        Returns a generator that yields the agent result.
        This matches the sync generator pattern from the real manifest.
        """
        # Extract the last user message from history
        if message_history:
            last_msg = message_history[-1]
            if isinstance(last_msg, dict):
                content = last_msg.get("content", "")
            else:
                content = str(last_msg)
        else:
            content = ""

        # Call agent function (now sync)
        # Note: Exceptions will propagate to the caller (ManifestWorker)
        if callable(self.agent_fn):
            result = self.agent_fn(content)
            yield result
        else:
            yield "Mock response"


class MockDIDExtension:
    """Mock DID extension for testing."""

    def __init__(
        self,
        did: str = "did:bindu:test_user:test_agent:550e8400e29b41d4a716446655440000",
        public_key: str = "test_public_key",
    ):
        """Initialize mock DID extension.

        Note: This is an __init__ method for a mock test object.
        """
        self.did = did
        self.public_key = public_key
        self.created = "2025-01-01T00:00:00Z"

    def get_did_document(self) -> Dict[str, Any]:
        """Get mock DID document."""
        return {
            "@context": ["https://www.w3.org/ns/did/v1", "https://bindu.ai/ns/v1"],
            "id": self.did,
            "created": self.created,
            "authentication": [
                {
                    "id": f"{self.did}#key-1",
                    "type": "Ed25519VerificationKey2020",
                    "controller": self.did,
                    "publicKeyBase58": self.public_key,
                }
            ],
            "bindu": {
                "agentName": "test_agent",
                "userId": "test_user",
                "skills": [],
                "capabilities": {},
                "description": "Test agent",
                "version": "1.0.0",
            },
            "service": [
                {
                    "id": f"{self.did}#agent-service",
                    "type": "binduAgentService",
                    "serviceEndpoint": "http://localhost:8030",
                }
            ],
        }

    def get_agent_info(self) -> Dict[str, Any]:
        """Get simplified agent info."""
        return {
            "did": self.did,
            "agentName": "test_agent",
            "userId": "test_user",
            "publicKey": self.public_key,
            "created": self.created,
            "skills": [],
            "capabilities": {},
            "description": "Test agent",
            "version": "1.0.0",
            "url": "http://localhost:8030",
        }


class MockNotificationService:
    """Mock notification service for testing."""

    def __init__(self):
        """Initialize mock notification service.

        Note: This is an __init__ method for a mock test object.
        """
        self.notifications = []
        self.delivery_failures = []

    def validate_config(self, config: Dict[str, Any]) -> None:
        """Validate push notification config."""
        if "url" not in config:
            raise ValueError("Missing 'url' in push notification config")

    async def send_notification(
        self,
        url: str,
        event: Dict[str, Any],
        token: Optional[str] = None,
        authentication: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Mock send notification."""
        self.notifications.append(
            {
                "url": url,
                "event": event,
                "token": token,
                "authentication": authentication,
            }
        )
        return True

    def mark_delivery_failure(self, task_id: UUID, error: str) -> None:
        """Mark a delivery failure."""
        self.delivery_failures.append(
            {
                "task_id": task_id,
                "error": error,
            }
        )
