from pebble import pebblify
from pebble.schemas.models import DeploymentConfig, SecurityConfig
from pebble.registry import AgentRegistry
from pathlib import Path

# Create security configuration
security_config = SecurityConfig(
    use_mtls=True,
    certs_dir=str(Path.home() / ".pebble" / "certs"),
    require_client_cert=True
)

# Create deployment configuration
config = DeploymentConfig(
    host="0.0.0.0",
    port=8000,
    security=security_config,
    # Other configuration options...
)

# Deploy agent with mTLS
pebblify(agent, config=config)

# Create a registry with mTLS enabled
registry = AgentRegistry(
    use_mtls=True,
    certs_dir=Path.home() / ".pebble" / "certs"
)

# Register agents and communicate securely
registry.register("agent1", adapter1)
registry.register("agent2", adapter2)
response = registry.send_message("agent1", "agent2", "Secure message")