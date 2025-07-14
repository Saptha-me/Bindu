"""Security components for the Pebbling server."""

# Re-export key components for easier imports
from pebbling.server.security.middleware_setup import (
    setup_security_methods,
    setup_security_middleware,
    setup_mtls_middleware,
    extract_did_manager
)
from pebbling.server.security.hibiscus_registry import register_with_hibiscus_registry
from pebbling.server.security.sheldon_service import setup_sheldon_certificates
