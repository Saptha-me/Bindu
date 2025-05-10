"""
Pebble Server Docker Application
"""
from typing import Dict, List, Optional, Union

from pebble.infra.fastapi.fastapi import FastApi
from pebble.infra.docker.app.base import ContainerContext


class PebbleServer(FastApi):
    # -*- App Name
    name: str = "pebble-server"

    # -*- Image Configuration - using the same base image as FastApi
    image_name: str = "agnohq/fastapi"
    image_tag: str = "0.104"
    command: Optional[Union[str, List[str]]] = "python -m pebble.server.main"

    # -*- App Ports for Pebble
    open_port: bool = True
    # Default ports for Pebble server
    port_number: int = 3773  # JSON-RPC server port
    rest_port: int = 3774    # REST API server port

    # -*- Workspace Configuration
    workspace_dir_container_path: str = "/app"
    # Mount the workspace directory to enable local development
    mount_workspace: bool = True

    # -*- Uvicorn Configuration
    uvicorn_host: str = "0.0.0.0"
    uvicorn_reload: Optional[bool] = True
    uvicorn_log_level: Optional[str] = "info"

    def get_container_env(self, container_context: ContainerContext) -> Dict[str, str]:
        """Add Pebble-specific environment variables to the container"""
        container_env: Dict[str, str] = super().get_container_env(container_context=container_context)
        
        # Add Pebble-specific environment variables
        container_env["PEBBLE_PORT"] = str(self.port_number)
        container_env["USER_PORT"] = str(self.rest_port)
        container_env["HOST"] = self.uvicorn_host
        container_env["HOSTING_METHOD"] = "docker"
        
        return container_env
