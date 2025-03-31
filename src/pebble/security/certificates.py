# src/pebble/security/certificates.py
"""Certificate management for secure agent communication."""

import os
import datetime
from pathlib import Path
from typing import Optional, Tuple
import logging
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa

logger = logging.getLogger("pebble.security")

def generate_key_pair() -> rsa.RSAPrivateKey:
    """Generate a new RSA key pair."""
    return rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

def generate_self_signed_cert(
    private_key: rsa.RSAPrivateKey,
    agent_id: str,
    days_valid: int = 365,
) -> x509.Certificate:
    """Generate a self-signed certificate for an agent."""
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, f"pebble-agent-{agent_id}")
    ])
    
    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        private_key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.datetime.utcnow()
    ).not_valid_after(
        datetime.datetime.utcnow() + datetime.timedelta(days=days_valid)
    ).add_extension(
        x509.SubjectAlternativeName([x509.DNSName(f"agent-{agent_id}")]),
        critical=False,
    ).sign(private_key, hashes.SHA256())
    
    return cert

def save_certificate(
    cert: x509.Certificate,
    private_key: rsa.RSAPrivateKey,
    agent_id: str,
    certs_dir: Optional[Path] = None,
) -> Tuple[Path, Path]:
    """Save certificate and private key to disk."""
    if certs_dir is None:
        certs_dir = Path.home() / ".pebble" / "certs"
    
    certs_dir.mkdir(parents=True, exist_ok=True)
    
    cert_path = certs_dir / f"{agent_id}.crt"
    key_path = certs_dir / f"{agent_id}.key"
    
    # Write certificate
    with open(cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    
    # Write private key
    with open(key_path, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))
    
    logger.info(f"Generated certificate and key for agent {agent_id}")
    return cert_path, key_path

def generate_agent_certificate(
    agent_id: str, 
    certs_dir: Optional[Path] = None
) -> Tuple[Path, Path]:
    """Generate and save a self-signed certificate for an agent."""
    private_key = generate_key_pair()
    cert = generate_self_signed_cert(private_key, agent_id)
    return save_certificate(cert, private_key, agent_id, certs_dir)