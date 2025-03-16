"""
Protocol registry for managing communication protocols in Pebble.
"""
from typing import Dict, Type, Optional

from .base import BaseProtocol

class ProtocolRegistry:
    """
    Registry for managing and accessing different protocol implementations.
    
    This class serves as a central registry for all protocol implementations,
    allowing agents to discover and select the appropriate protocol for communication.
    """
    
    _protocols: Dict[str, Type[BaseProtocol]] = {}
    
    @classmethod
    def register(cls, protocol_name: str, protocol_class: Type[BaseProtocol]) -> None:
        """
        Register a protocol implementation with the registry.
        
        Args:
            protocol_name: Unique name for the protocol
            protocol_class: The protocol class to register
        """
        if protocol_name in cls._protocols:
            raise ValueError(f"Protocol '{protocol_name}' is already registered")
        
        cls._protocols[protocol_name] = protocol_class
    
    @classmethod
    def get_protocol(cls, protocol_name: str) -> Optional[Type[BaseProtocol]]:
        """
        Get a protocol implementation by name.
        
        Args:
            protocol_name: The name of the protocol to retrieve
            
        Returns:
            Optional[Type[BaseProtocol]]: The protocol class if found, None otherwise
        """
        return cls._protocols.get(protocol_name)
    
    @classmethod
    def create_protocol(cls, protocol_name: str, **kwargs) -> Optional[BaseProtocol]:
        """
        Create an instance of a protocol by name.
        
        Args:
            protocol_name: The name of the protocol to instantiate
            **kwargs: Arguments to pass to the protocol constructor
            
        Returns:
            Optional[BaseProtocol]: The protocol instance if found, None otherwise
        """
        protocol_class = cls.get_protocol(protocol_name)
        if protocol_class:
            return protocol_class(**kwargs)
        return None
    
    @classmethod
    def list_protocols(cls) -> Dict[str, Type[BaseProtocol]]:
        """
        List all registered protocols.
        
        Returns:
            Dict[str, Type[BaseProtocol]]: Dictionary mapping protocol names to protocol classes
        """
        return cls._protocols.copy()
