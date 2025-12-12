import logging
from typing import Dict, Any
from utils.logger import get_logger


class A2AHandler:
  
    
    def __init__(self, orchestrator_did: str):
        self.logger = get_logger(__name__)
        self.orchestrator_did = orchestrator_did
        self.message_log = []
    
    def handle_agent_message(self, message: Dict[str, Any]) -> Dict[str, Any]:

        self.logger.info(f"Received A2A message from {message.get('from_did')}")
        self.message_log.append(message)
        
        action = message.get("action")
        
        if action == "quote_response":
            return self.handle_quote_response(message)
        elif action == "task_result":
            return self.handle_task_result(message)
        elif action == "task_error":
            return self.handle_task_error(message)
        elif action == "heartbeat":
            return self.handle_heartbeat(message)
        else:
            self.logger.warning(f"Unknown action: {action}")
            return {"status": "error", "message": f"Unknown action: {action}"}
    
    def handle_quote_response(self, message: Dict[str, Any]) -> Dict[str, Any]:

        payload = message.get("payload", {})
        self.logger.info(f"Quote response: ${payload.get('price')}")
        return {"status": "received", "action": "quote_response"}
    
    def handle_task_result(self, message: Dict[str, Any]) -> Dict[str, Any]:

        payload = message.get("payload", {})
        self.logger.info(f"Task result received for {payload.get('subtask_id')}")
        return {"status": "received", "action": "task_result"}
    
    def handle_task_error(self, message: Dict[str, Any]) -> Dict[str, Any]:

        payload = message.get("payload", {})
        self.logger.error(f"Agent error: {payload.get('error_message')}")
        return {"status": "received", "action": "task_error"}
    
    def handle_heartbeat(self, message: Dict[str, Any]) -> Dict[str, Any]:

        agent_did = message.get("from_did")
        self.logger.debug(f"Heartbeat from {agent_did}")
        return {"status": "ok", "action": "heartbeat_ack"}
    
    def send_task_execution_request(self, agent_did: str, subtask_id: str, 
                                   task_description: str) -> Dict[str, Any]:

        message = {
            "from_did": self.orchestrator_did,
            "to_did": agent_did,
            "action": "execute_task",
            "payload": {
                "subtask_id": subtask_id,
                "description": task_description,
                "timestamp": self._get_timestamp()
            }
        }
        
        self.logger.info(f"Sending execution request to {agent_did}")
        return message
    
    def send_quote_request(self, agent_did: str, capability: str, 
                          budget: float) -> Dict[str, Any]:
        message = {
            "from_did": self.orchestrator_did,
            "to_did": agent_did,
            "action": "request_quote",
            "payload": {
                "capability": capability,
                "budget": budget,
                "timestamp": self._get_timestamp()
            }
        }
        
        self.logger.info(f"Sending quote request to {agent_did}")
        return message
    
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.utcnow().isoformat()
    
    def get_message_log(self) -> list:
        """Get message log"""
        return self.message_log