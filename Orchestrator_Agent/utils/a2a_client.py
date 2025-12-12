import json
import uuid
from typing import Dict, Any, Optional
from datetime import datetime
from .logger import get_logger


class A2AMessage:
    """A2A Protocol Message"""
    
    def __init__(self, from_did: str, to_did: str, action: str, payload: Dict[str, Any]):
        self.id = str(uuid.uuid4())
        self.from_did = from_did
        self.to_did = to_did
        self.action = action
        self.payload = payload
        self.timestamp = datetime.utcnow().isoformat()
        self.status = "pending"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "from_did": self.from_did,
            "to_did": self.to_did,
            "action": self.action,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "status": self.status,
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict())


class A2AClient:
    """Client for A2A Protocol communication"""
    
    def __init__(self, orchestrator_did: str):
        self.logger = get_logger(__name__)
        self.orchestrator_did = orchestrator_did
        self.message_history = []
    
    def create_message(self, to_did: str, action: str, payload: Dict[str, Any]) -> A2AMessage:
        """Create an A2A message"""
        message = A2AMessage(
            from_did=self.orchestrator_did,
            to_did=to_did,
            action=action,
            payload=payload
        )
        self.message_history.append(message)
        return message
    
    def send_task_request(self, agent_did: str, subtask_id: str, 
                         task_description: str, params: Dict[str, Any]) -> A2AMessage:
        """Send a task execution request via A2A"""
        payload = {
            "subtask_id": subtask_id,
            "description": task_description,
            "parameters": params,
            "request_time": datetime.utcnow().isoformat()
        }
        
        message = self.create_message(agent_did, "execute_task", payload)
        self.logger.info(f"Sent task request to {agent_did}: {subtask_id}")
        return message
    
    def send_quote_request(self, agent_did: str, task_id: str, subtask_id: str,
                          requirements: Dict[str, Any]) -> A2AMessage:
        """Send a quote request via A2A"""
        payload = {
            "task_id": task_id,
            "subtask_id": subtask_id,
            "requirements": requirements,
            "request_time": datetime.utcnow().isoformat()
        }
        
        message = self.create_message(agent_did, "request_quote", payload)
        self.logger.info(f"Sent quote request to {agent_did}")
        return message
    
    def send_payment_notification(self, agent_did: str, payment_id: str,
                                 amount: float, currency: str = "USD") -> A2AMessage:
        """Send payment notification via A2A"""
        payload = {
            "payment_id": payment_id,
            "amount": amount,
            "currency": currency,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        message = self.create_message(agent_did, "payment_notification", payload)
        self.logger.info(f"Sent payment notification to {agent_did}: ${amount}")
        return message
    
    def get_message_history(self, agent_did: Optional[str] = None) -> list:
        """Get message history"""
        if agent_did:
            return [m for m in self.message_history if m.to_did == agent_did]
        return self.message_history