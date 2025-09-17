#
# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/Pebbling-ai/pebble/issues/new/choose |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🐧

"""🔧 Global Constants: The Foundation Stones

Central repository for all constants, configuration values, and type definitions
used throughout the Pebbling framework. Like carefully selected pebbles,
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

# Cryptographic Key Configuration
PKI_DIR = "pki"
CERTIFICATE_DIR = "certs"
PRIVATE_KEY_FILENAME = "private_key.pem"
PUBLIC_KEY_FILENAME = "public_key.pem"
CSR_FILENAME = "agent.csr"
CERTIFICATE_FILENAME = "agent.cert"
ROOT_CERTIFICATE_FILENAME = "root.cert"
CERTIFICATE_AUTHORITY = "sheldon"


RSA_KEY_SIZE = 4096
RSA_PUBLIC_EXPONENT = 65537
CHALLENGE_EXPIRATION_SECONDS = 300

# Key Types
KeyType = Literal["rsa", "ed25519"]
PrivateKeyTypes = Union[rsa.RSAPrivateKey, ed25519.Ed25519PrivateKey]
PublicKeyTypes = Union[rsa.RSAPublicKey, ed25519.Ed25519PublicKey]

# JWT Configuration
DEFAULT_JWT_EXPIRY_HOURS = 24
JWT_ALGORITHM = "HS256"

# DID Configuration
DID_CONFIG_FILENAME = "did.json"
DID_METHOD = "key"

# Security-related constants and type definitions from keys.py
KEY_TYPES = ["rsa", "ed25519"]
KEY_SIZES = {"rsa": 4096, "ed25519": 256}
KEY_ALGORITHMS = {"rsa": "RS256", "ed25519": "EdDSA"}
DEFAULT_KEY_ALGORITHM = KEY_ALGORITHMS["ed25519"]

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

# File Extensions
CERT_FILE_EXTENSION = ".cert"
CSR_FILE_EXTENSION = ".csr"
KEY_FILE_EXTENSION = ".pem"
