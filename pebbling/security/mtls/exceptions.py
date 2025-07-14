"""
Custom exceptions for mTLS operations in the Pebbling security system.

These exceptions provide specific error types for various mTLS-related failures,
allowing for more precise error handling and debugging.
"""


class MTLSError(Exception):
    """Base exception class for all mTLS-related errors."""
    pass


class CertificateError(MTLSError):
    """Exception raised for errors related to certificate operations."""
    pass


class CertificateRequestError(CertificateError):
    """Exception raised when requesting a certificate from the CA fails."""
    pass


class CertificateVerificationError(CertificateError):
    """Exception raised when certificate verification fails."""
    pass


class TokenError(MTLSError):
    """Exception raised for errors related to verification tokens."""
    pass


class TokenExpiredError(TokenError):
    """Exception raised when a verification token has expired."""
    pass


class SheldonCAError(MTLSError):
    """Exception raised for errors when communicating with the Sheldon CA service."""
    pass


class SSLContextError(MTLSError):
    """Exception raised for errors when creating or using SSL contexts."""
    pass
