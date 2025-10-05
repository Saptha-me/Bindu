#
# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/bindu-ai/pebble/issues/new/choose |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🐧

"""🔧 Global Constants: The Foundation Stones

Central repository for all constants, configuration values, and type definitions
used throughout the bindu framework. Like carefully selected pebbles,
each constant serves a specific purpose in the greater architecture.

🏗️ Categories:
   • Security: Cryptographic keys, file names, algorithms
   • Networking: Ports, timeouts, protocols
   • Registry: Default URLs, authentication
   • Deployment: Docker, Fly.io configurations
"""

from typing import Literal, Union

from cryptography.hazmat.primitives.asymmetric import ed25519, rsa

# =============================================================================
# 🔐 SECURITY CONSTANTS
# =============================================================================

# DID Configuration
DID_CONFIG_FILENAME = "did.json"
DID_METHOD = "key"
DID_AGENT_EXTENSION_METADATA = "did.message.signature"

# DID File Names
DID_PRIVATE_KEY_FILENAME = "private.pem"
DID_PUBLIC_KEY_FILENAME = "public.pem"

# DID Document Constants
DID_W3C_CONTEXT = "https://www.w3.org/ns/did/v1"
DID_BINDU_CONTEXT = "https://bindu.ai/ns/v1"
DID_VERIFICATION_KEY_TYPE = "Ed25519VerificationKey2020"
DID_KEY_FRAGMENT = "key-1"
DID_SERVICE_FRAGMENT = "agent-service"
DID_SERVICE_TYPE = "binduAgentService"

# DID Method Prefixes
DID_METHOD_BINDU = "bindu"
DID_METHOD_KEY = "key"
DID_MULTIBASE_PREFIX = "z"  # Base58btc prefix for ed25519

# DID Extension
DID_EXTENSION_URI = "https://github.com/Saptha-me/saptha_me"
DID_EXTENSION_DESCRIPTION = "DID-based identity management for bindu agents"
DID_RESOLVER_ENDPOINT = "/did/resolve"
DID_INFO_ENDPOINT = "/agent/info"

# DID Validation
DID_PREFIX = "did:"
DID_MIN_PARTS = 3
DID_BINDU_PARTS = 4

# Text Encoding
TEXT_ENCODING = "utf-8"
BASE58_ENCODING = "ascii"


# =============================================================================
# 🌐 NETWORKING CONSTANTS
# =============================================================================

# Default Ports
DEFAULT_AGENT_PORT = 3773
DEFAULT_MCP_PORT = 8080
DEFAULT_REGISTRY_PORT = 19191

# Timeouts (seconds)
DEFAULT_REQUEST_TIMEOUT = 30
DEFAULT_CONNECTION_TIMEOUT = 10

# =============================================================================
# 🚀 DEPLOYMENT CONSTANTS
# =============================================================================

# Server Types
SERVER_TYPE_AGENT = "agent"
SERVER_TYPE_MCP = "mcp"

# Endpoint Types
ENDPOINT_TYPE_JSON_RPC = "json-rpc"
ENDPOINT_TYPE_HTTP = "http"
ENDPOINT_TYPE_SSE = "sse"

# Docker Configuration
DEFAULT_DOCKER_PORT = 8080
DOCKER_HEALTHCHECK_PATH = "/healthz"
