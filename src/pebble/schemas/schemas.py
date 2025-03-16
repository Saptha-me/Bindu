from typing import Any, Callable, Dict, List, Optional, Union

from fastapi import UploadFile
from pydantic import BaseModel


class AgentGetResponse(BaseModel):
    agent_id: Optional[str] = None
    name: Optional[str] = None
    model: Optional[AgentModel] = None
    add_context: Optional[bool] = None
    tools: Optional[List[Dict[str, Any]]] = None
    memory: Optional[Dict[str, Any]] = None
    storage: Optional[Dict[str, Any]] = None
    knowledge: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    instructions: Optional[Union[List[str], str, Callable]] = None