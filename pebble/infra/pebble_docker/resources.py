"""
Pebble Docker Resources
"""
from typing import List, Optional

from pebble.infra.docker.resources import DockerResources
from pebble.infra.pebble_docker.pebble_app import PebbleServer


class PebbleDockerResources(DockerResources):
    """Docker resources for the Pebble server"""
    name: str = "pebble"
    network: str = "pebble-network"
    
    def __init__(self):
        """Initialize resources with the PebbleServer app"""
        super().__init__()
        
        # Configure the Pebble server app
        self.apps: List[PebbleServer] = [PebbleServer()]
