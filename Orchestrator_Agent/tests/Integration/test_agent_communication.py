import pytest
from utils.a2a_client import A2AClient


class TestAgentCommunication:
    """Test A2A protocol communication"""
    
    def test_create_a2a_message(self, orchestrator_did):
        """Test creating A2A message"""
        client = A2AClient(orchestrator_did)
        
        message = client.create_message(
            "did:bindu:agent:test",
            "test_action",
            {"key": "value"}
        )
        
        assert message.from_did == orchestrator_did
        assert message.to_did == "did:bindu:agent:test"
        assert message.action == "test_action"
    
    def test_send_task_request(self, orchestrator_did):
        """Test sending task request"""
        client = A2AClient(orchestrator_did)
        
        message = client.send_task_request(
            "did:bindu:agent:test",
            "subtask-001",
            "Test task",
            {"param": "value"}
        )
        
        assert message.action == "execute_task"
        assert message.payload["subtask_id"] == "subtask-001"
    
    def test_send_quote_request(self, orchestrator_did):
        """Test sending quote request"""
        client = A2AClient(orchestrator_did)
        
        message = client.send_quote_request(
            "did:bindu:agent:test",
            "task-001",
            "subtask-001",
            {"requirement": "value"}
        )
        
        assert message.action == "request_quote"
        assert message.payload["task_id"] == "task-001"
    
    def test_send_payment_notification(self, orchestrator_did):
        """Test sending payment notification"""
        client = A2AClient(orchestrator_did)
        
        message = client.send_payment_notification(
            "did:bindu:agent:test",
            "payment-001",
            50.0,
            "USD"
        )
        
        assert message.action == "payment_notification"
        assert message.payload["amount"] == 50.0
    
    def test_message_history(self, orchestrator_did):
        """Test message history tracking"""
        client = A2AClient(orchestrator_did)
        
        client.send_task_request("did:bindu:agent:test", "task-001", "Task", {})
        client.send_quote_request("did:bindu:agent:test2", "task-002", "subtask", {})
        
        history = client.get_message_history()
        assert len(history) >= 2
        
        # Get specific agent history
        agent_history = client.get_message_history("did:bindu:agent:test")
        assert len(agent_history) >= 1