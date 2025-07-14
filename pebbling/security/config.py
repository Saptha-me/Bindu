"""
Configuration constants for Pebbling security features.

This module defines constants and default values used across the security
subsystem, including both DID-based authentication and mTLS.
"""

import os
from datetime import timedelta

# DID-related configuration
DEFAULT_KEY_PATH = "pebble_private_key.json"
DEFAULT_CHALLENGE_TIMEOUT_SECONDS = 60

# mTLS-related configuration
DEFAULT_CERT_DIRECTORY = os.path.join(os.path.expanduser("~"), ".pebble", "certs")
DEFAULT_TOKEN_VALIDITY = timedelta(hours=24)
DEFAULT_CERTIFICATE_VALIDITY = timedelta(days=30)

# Verification endpoints
DEFAULT_SHELDON_CA_URL = "https://sheldon-ca.example.com"  # Replace with actual URL in production

# Security protocol configuration
DEFAULT_TLS_VERSION = "TLSv1.3"
DEFAULT_CIPHER_SUITES = [
    "TLS_AES_256_GCM_SHA384",
    "TLS_CHACHA20_POLY1305_SHA256",
    "TLS_AES_128_GCM_SHA256",
]

# Security endpoints
SECURITY_ENDPOINTS = {
    "exchange_did": "/security/exchange_did",
    "verify_connection": "/security/verify_connection",
    "challenge": "/security/challenge",
    "challenge_response": "/security/challenge_response",
    "certificate_status": "/security/certificate_status",
}

# Sheldon CA API endpoints
SHELDON_CA_ENDPOINTS = {
    "issue_certificate": "/issue_certificate",
    "verify_certificate": "/verify_certificate",
    "public_certificate": "/public_certificate",
}
