"""
Constants module - Re-exports settings as constants for backward compatibility.

All constants have been moved to the settings module for better configuration management.
This module provides backward-compatible access to those settings.
"""

from bindu.settings import app_settings

# =============================================================================
# 🔐 SECURITY CONSTANTS (DID Settings)
# =============================================================================

# DID Configuration
DID_CONFIG_FILENAME = app_settings.did.config_filename
DID_METHOD = app_settings.did.method
DID_AGENT_EXTENSION_METADATA = app_settings.did.agent_extension_metadata

# DID File Names
DID_PRIVATE_KEY_FILENAME = app_settings.did.private_key_filename
DID_PUBLIC_KEY_FILENAME = app_settings.did.public_key_filename

# DID Document Constants
DID_W3C_CONTEXT = app_settings.did.w3c_context
DID_BINDU_CONTEXT = app_settings.did.bindu_context
DID_VERIFICATION_KEY_TYPE = app_settings.did.verification_key_type
DID_KEY_FRAGMENT = app_settings.did.key_fragment
DID_SERVICE_FRAGMENT = app_settings.did.service_fragment
DID_SERVICE_TYPE = app_settings.did.service_type

# DID Method Prefixes
DID_METHOD_BINDU = app_settings.did.method_bindu
DID_METHOD_KEY = app_settings.did.method_key
DID_MULTIBASE_PREFIX = app_settings.did.multibase_prefix

# DID Extension
DID_EXTENSION_URI = app_settings.did.extension_uri
DID_EXTENSION_DESCRIPTION = app_settings.did.extension_description
DID_RESOLVER_ENDPOINT = app_settings.did.resolver_endpoint
DID_INFO_ENDPOINT = app_settings.did.info_endpoint

# DID Key Directory
PKI_DIR = app_settings.did.pki_dir

# DID Validation
DID_PREFIX = app_settings.did.prefix
DID_MIN_PARTS = app_settings.did.min_parts
DID_BINDU_PARTS = app_settings.did.bindu_parts

# Text Encoding
TEXT_ENCODING = app_settings.did.text_encoding
BASE58_ENCODING = app_settings.did.base58_encoding


# =============================================================================
# 🌐 NETWORKING CONSTANTS (Network Settings)
# =============================================================================

# Default Host and URL
DEFAULT_HOST = app_settings.network.default_host
DEFAULT_PORT = app_settings.network.default_port
DEFAULT_URL = app_settings.network.default_url

# Timeouts (seconds)
DEFAULT_REQUEST_TIMEOUT = app_settings.network.request_timeout
DEFAULT_CONNECTION_TIMEOUT = app_settings.network.connection_timeout

# Media Types for Static Files
MEDIA_TYPES = app_settings.network.media_types

# =============================================================================
# 🚀 DEPLOYMENT CONSTANTS (Deployment Settings)
# =============================================================================

# Server Types
SERVER_TYPE_AGENT = app_settings.deployment.server_type_agent
SERVER_TYPE_MCP = app_settings.deployment.server_type_mcp

# Endpoint Types
ENDPOINT_TYPE_JSON_RPC = app_settings.deployment.endpoint_type_json_rpc
ENDPOINT_TYPE_HTTP = app_settings.deployment.endpoint_type_http
ENDPOINT_TYPE_SSE = app_settings.deployment.endpoint_type_sse

# Docker Configuration
DEFAULT_DOCKER_PORT = app_settings.deployment.docker_port
DOCKER_HEALTHCHECK_PATH = app_settings.deployment.docker_healthcheck_path

# =============================================================================
# 📊 OBSERVABILITY CONSTANTS (Observability Settings)
# =============================================================================

# OpenInference Instrumentor Mapping
OPENINFERENCE_INSTRUMENTOR_MAP = app_settings.observability.instrumentor_map

# OpenTelemetry Base Packages
OPENTELEMETRY_BASE_PACKAGES = app_settings.observability.base_packages
