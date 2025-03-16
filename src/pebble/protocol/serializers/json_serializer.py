"""
JSON serializer for agent communication protocol.
"""
import json
from datetime import datetime
from typing import Any, Dict, Type

from pydantic import BaseModel

class JsonSerializer:
    """
    JSON serializer for agent communication messages.
    
    This class provides functionality to convert between Pydantic models
    and JSON for agent communication.
    """
    
    @staticmethod
    def _datetime_serializer(obj: Any) -> Any:
        """Custom serializer for datetime objects."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable")
    
    @classmethod
    def serialize(cls, model: BaseModel) -> bytes:
        """
        Serialize a Pydantic model to JSON bytes.
        
        Args:
            model: The model to serialize
            
        Returns:
            bytes: JSON encoded bytes
        """
        return json.dumps(
            model.dict(), 
            default=cls._datetime_serializer
        ).encode('utf-8')
    
    @classmethod
    def deserialize(cls, data: bytes, model_class: Type[BaseModel]) -> BaseModel:
        """
        Deserialize JSON bytes to a Pydantic model.
        
        Args:
            data: The JSON bytes to deserialize
            model_class: The target Pydantic model class
            
        Returns:
            BaseModel: An instance of the specified model class
        """
        json_data = json.loads(data.decode('utf-8'))
        return model_class.parse_obj(json_data)
